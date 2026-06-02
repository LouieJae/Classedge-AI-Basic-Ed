# Prime — RAG Tutor

## Overview

A student-facing AI tutor on the subject detail page. Students ask questions
about their course material, the system retrieves relevant content chunks via
vector similarity search, and an LLM generates a grounded answer. When course
materials don't cover the topic, the tutor suggests the student ask their
teacher or search trusted external sites (Khan Academy).

## Scope

**In scope:**
- New Django app `rag_tutor/`
- pgvector extension on Neon Postgres
- `ContentChunk` model with vector embeddings (1536-dim, OpenAI text-embedding-3-small)
- Content indexing pipeline: chunk + embed Module/Activity/ParsedChapter text
- Celery tasks for async indexing
- `ChatMessage` model for question/answer logging
- Query endpoint: embed question → pgvector search → Claude Haiku answer
- Chat widget on subject detail page (vanilla JS + fetch)
- Hybrid fallback: suggest Khan Academy when no relevant chunks found
- Management command for bulk re-indexing
- Strict grounding guardrails in system prompt

**Out of scope:**
- Multi-turn conversation (stateless Q&A only, v2)
- Teacher-configurable external reference sites (v2)
- Streaming responses (full response returned, v2)
- Per-school feature flag / tier gating (future)
- Grading or assessment features

## Infrastructure

No new hardware or services. All API-based:

| Component | Service | Cost |
|-----------|---------|------|
| Vector storage | pgvector on existing Neon Postgres | Free (extension) |
| Embeddings | OpenAI `text-embedding-3-small` API | $0.02/M tokens |
| LLM answers | Anthropic Claude Haiku API | $0.25/M input tokens |
| Indexing | Existing Celery worker | Already running |

**One-time setup:** `CREATE EXTENSION vector;` on the Neon database.

## Data Model

### `ContentChunk`

| Field | Type | Notes |
|---|---|---|
| `subject` | ForeignKey | FK to `subject.Subject`, CASCADE. |
| `source_type` | CharField(20) | `module` / `activity` / `chapter` |
| `source_id` | PositiveIntegerField | PK of the source Module/Activity/ParsedChapter. |
| `source_title` | CharField(200) | Title of the source (for citations). |
| `chunk_index` | PositiveIntegerField | 0-based index within the source. |
| `text` | TextField | The chunk text (~500 tokens). |
| `embedding` | VectorField(1536) | OpenAI text-embedding-3-small vector. |
| `created_at` | DateTimeField | auto_now_add |

**Unique constraint:** `(source_type, source_id, chunk_index)` — allows upsert
on re-index without duplicates.

**Index:** pgvector ivfflat or HNSW index on the embedding column for fast
similarity search. At this scale (<100K chunks), exact search is also fine.

### `ChatMessage`

| Field | Type | Notes |
|---|---|---|
| `subject` | ForeignKey | FK to `subject.Subject`, CASCADE. |
| `student` | ForeignKey | FK to `accounts.CustomUser`, CASCADE. |
| `question` | TextField | Student's question. |
| `answer` | TextField | LLM-generated answer. |
| `sources` | JSONField | List of source references used. |
| `had_relevant_chunks` | BooleanField | Whether RAG found relevant material. |
| `created_at` | DateTimeField | auto_now_add |

`sources` format:
```json
[
  {"source_type": "module", "source_id": 42, "title": "Week 1: Algebra Basics", "chunk_index": 0},
  {"source_type": "activity", "source_id": 55, "title": "Week 1 Quiz", "chunk_index": 1}
]
```

## Content Indexing Pipeline

### Chunking

`rag_tutor/chunking.py` — `chunk_text(text, max_tokens=500, overlap_tokens=50) -> list[str]`

Splits text into chunks at sentence boundaries (split on `. `, `! `, `? `).
Each chunk is ~500 tokens (estimated as len(text) / 4). Consecutive chunks
overlap by ~50 tokens for context continuity.

### Embedding

`rag_tutor/embeddings.py` — `embed_texts(texts: list[str]) -> list[list[float]]`

Calls OpenAI `text-embedding-3-small` API. Takes a batch of texts, returns
a list of 1536-dimensional vectors. Uses the `openai` Python package.

Settings:
```python
RAG_TUTOR_EMBEDDING_MODEL = "text-embedding-3-small"
OPENAI_API_KEY = env("OPENAI_API_KEY")
```

### Indexing task

`rag_tutor/tasks.py` — `index_content(source_type, source_id)`

1. Load the source object (Module, Activity, or ParsedChapter).
2. Extract text: Module.description, Activity.activity_instruction,
   or ParsedChapter.parsed_data["text"].
3. Skip if text is empty or too short (<50 chars).
4. Chunk the text via `chunk_text()`.
5. Embed all chunks in one batch via `embed_texts()`.
6. Delete existing ContentChunk rows for this source (upsert pattern).
7. Bulk-create new ContentChunk rows.

### Indexing triggers

Django `post_save` signal on `module.Module` and `activity.Activity`.
Dispatches `index_content.delay("module", instance.pk)` when description/
instruction changes.

Signal registered in `rag_tutor/apps.py` via `ready()`.

For ParsedChapter: indexed when `parsed_data` is set (status changes to
COMPLETE). Signal on ParsedChapter `post_save`.

### Management command

`python manage.py reindex_subject <subject_id>` — re-indexes all modules,
activities, and parsed chapters for a given subject. Useful for initial
setup or after bulk imports.

## Query Flow

### Endpoint

`POST /rag-tutor/ask/<int:subject_id>/`

Request body: `{"question": "What is a variable?"}`

Protected by `@login_required`. Student must be enrolled in the subject
(use `check_subject_access` with `require_student=False` — allows both
students and teachers to ask).

### Query pipeline

`rag_tutor/query.py` — `ask_question(subject_id, question, student) -> dict`

1. Embed the question via `embed_texts([question])`.
2. pgvector cosine similarity search: find top 5 ContentChunk rows
   where `subject_id` matches, ordered by `embedding <=> question_embedding`.
3. Check relevance: if the best chunk's cosine distance > 0.8 (low
   similarity), set `had_relevant_chunks = False`.
4. Build LLM prompt (see below).
5. Call Claude Haiku via Anthropic API.
6. Save ChatMessage with question, answer, sources, had_relevant_chunks.
7. Return `{"answer": "...", "sources": [...], "had_relevant_chunks": true}`.

### LLM prompt

```
System: You are a helpful tutor for a school course. Answer the student's
question using ONLY the provided course material excerpts. Be clear,
educational, and appropriate for a school setting.

If the provided excerpts contain relevant information, answer the question
and cite which source you used (e.g., "According to Module 3...").

If the provided excerpts do NOT contain information to answer the question,
respond with: "Your course materials don't cover this topic yet. You might
want to ask your teacher about it, or search for '[topic]' on Khan Academy
(khanacademy.org)."

Do not make up information. Do not answer questions unrelated to academics.

Course material excerpts:
---
[Source: Module 3 - Algebra Basics]
{chunk text}
---
[Source: Week 1 Quiz]
{chunk text}
---

Student's question: {question}
```

### Response format

```json
{
  "answer": "A variable is a symbol that represents an unknown value...\n\n(Source: Module 3 - Algebra Basics)",
  "sources": [
    {"source_type": "module", "source_id": 42, "title": "Module 3 - Algebra Basics", "chunk_index": 0}
  ],
  "had_relevant_chunks": true
}
```

## UI — Chat Widget

### Placement

Bottom-right corner of the subject detail page. Collapsed by default —
a floating button labeled "Ask AI Tutor". Clicking expands a chat panel.

### Implementation

`rag_tutor/templates/rag_tutor/chat_widget.html` — a Django template
included via `{% include %}` in the subject detail template. Contains:

- Floating button (fixed position, bottom-right)
- Expandable chat panel (card with header, scrollable message area, input)
- Vanilla JavaScript: fetch POST to `/rag-tutor/ask/<subject_id>/`,
  display answer, show sources as clickable links
- Loading spinner while waiting for response (~2s)
- No framework dependencies — just DOM manipulation + fetch API

### Styling

Bootstrap 5 classes (consistent with the school-side app). Fixed-position
card, z-index above other content. Responsive — collapses to full-width on
mobile.

### Integration

Add `{% include "rag_tutor/chat_widget.html" %}` to the subject detail
template (`course/templates/course/view_subject_dashboard.html`), inside
the content block, gated by `{% if is_student or is_teacher %}`.

## Configuration

Settings additions (in gitignored `lms/settings.py`):

```python
# RAG Tutor
RAG_TUTOR_EMBEDDING_MODEL = "text-embedding-3-small"
RAG_TUTOR_LLM_MODEL = "claude-haiku-4-5-20251001"
RAG_TUTOR_TOP_K = 5
RAG_TUTOR_RELEVANCE_THRESHOLD = 0.8
```

Environment variable: `OPENAI_API_KEY` (for embeddings).
`ANTHROPIC_API_KEY` already configured (for Haiku).

New pip package: `openai` (for embeddings API), `pgvector` (Django integration).

## Testing

### Chunking tests
- Chunk short text returns single chunk.
- Chunk long text splits at sentence boundaries.
- Overlap between consecutive chunks.
- Empty text returns empty list.

### Embedding tests (mocked)
- Mock OpenAI API, verify batch call with correct model.
- Returns correct number of vectors with correct dimensions.

### Indexing task tests
- Index a module: verify ContentChunk rows created with correct fields.
- Re-index same module: old chunks deleted, new ones created (no duplicates).
- Skip empty/short content.

### Query tests (mocked)
- Mock embedding + pgvector results + Haiku call, verify full pipeline.
- No relevant chunks: verify fallback message includes "Khan Academy".
- ChatMessage saved with correct fields.

### View tests
- Endpoint returns JSON answer for enrolled student.
- Unauthenticated returns 401/302.
- Student not enrolled in subject returns 403/302.

### Widget integration test
- Subject detail page includes chat widget HTML for students.
- Chat widget not shown for unauthenticated users.
