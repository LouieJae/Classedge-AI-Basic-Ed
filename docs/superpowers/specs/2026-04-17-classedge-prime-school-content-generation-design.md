# Prime — Per-school Content Generation

## Overview

Teachers generate AI-powered modules and activities directly from their
subject's existing views. They provide a topic, learning objectives, and
content type, optionally uploading reference material (PDFs/notes). The LLM
generates draft content that appears inline alongside manually-created content.

This is the first Prime tier feature. It runs on the school side (not the
central content portal) and is independent of the Plus central content pipeline.

## Scope

**In scope:**
- New Django app `ai_content/` on the school side
- `GenerationRequest` model to track each request
- LLM integration for lesson outline + quiz generation
- Optional PDF reference file upload with text extraction
- Celery task for async generation
- "Generate with AI" button on subject detail page
- Generation form: topic, objectives, content type, file upload, model selector
- Generated Module/Activity rows in draft state
- Configuration for LLM models (settings-based)

**Out of scope:**
- RAG tutor (separate sub-project)
- At-risk dashboard (separate sub-project)
- Central content pipeline (Plus tier only)
- Question bank / structured question models
- Feature flag / tier gating (future work)

## Data Model

### `GenerationRequest`

| Field | Type | Notes |
|---|---|---|
| `subject` | ForeignKey | FK to `subject.Subject`, CASCADE. |
| `term` | ForeignKey | FK to `course.Term`, CASCADE. |
| `requested_by` | ForeignKey | FK to `accounts.CustomUser`, CASCADE. |
| `topic` | CharField(200) | Topic name provided by teacher. |
| `objectives` | TextField | Learning objectives text. |
| `content_type` | CharField | `module` / `quiz` / `both` |
| `reference_file` | FileField | Optional PDF upload, blank=True. |
| `reference_text` | TextField | Extracted text from PDF, blank=True. |
| `model_key` | CharField(50) | LLM model key used. |
| `status` | CharField | `pending` / `running` / `complete` / `failed` |
| `error_message` | TextField | Blank. Error details if failed. |
| `generated_module_id` | PositiveIntegerField | PK of created Module, null=True. |
| `generated_activity_id` | PositiveIntegerField | PK of created Activity, null=True. |
| `created_at` | DateTimeField | auto_now_add |
| `updated_at` | DateTimeField | auto_now |

## LLM Integration

### `ai_content/llm.py`

Function: `call_school_content_generator(topic, objectives, content_type, reference_text, model_key)`

Takes:
- `topic`: String — the topic name.
- `objectives`: String — learning objectives.
- `content_type`: "module", "quiz", or "both".
- `reference_text`: String — extracted PDF text (may be empty).
- `model_key`: Which LLM model to use.

Returns:
```json
{
  "lesson_description": "Multi-paragraph lesson outline...",
  "quiz_questions": "Numbered quiz questions..."
}
```

When `content_type` is "module", only `lesson_description` is required.
When `content_type` is "quiz", only `quiz_questions` is required.
When `content_type` is "both", both are required.

The prompt instructs the LLM to:
1. Write a lesson outline covering key concepts, learning objectives, and
   teaching notes (if module or both).
2. Write 5-10 quiz questions — mix of multiple choice (A-D) and short answer
   (if quiz or both).
3. If reference text is provided, ground the content in that material.
4. If no reference text, generate based on the topic and objectives alone.

Uses same Anthropic SDK pattern as `central_content/llm.py`. Config via
`AI_CONTENT_MODELS` setting (same structure as `CURRICULUM_PLANNER_MODELS`).

### Reference file text extraction

`ai_content/pdf_extract.py` — a single function:

`extract_text_from_pdf(file_field) -> str`

Uses PyMuPDF (`fitz`) to extract text from each page of the uploaded PDF.
Concatenates all pages. Truncates to 8000 characters to stay within LLM
context limits. Returns empty string if extraction fails.

PyMuPDF is already installed (MinerU dependency). No new package needed.

## Celery Task

### `generate_school_content`

In `ai_content/tasks.py`.

Arguments: `request_id`

1. Load `GenerationRequest`, set status to `running`.
2. If `reference_file` is set and `reference_text` is empty: extract text
   via `extract_text_from_pdf()`, save to `reference_text`.
3. Call `call_school_content_generator()` with topic, objectives, content_type,
   reference_text, model_key.
4. Based on `content_type`, create:
   - Module (`module.Module`): `file_name` = topic, `description` = lesson
     text, `subject` = request.subject, `term` = request.term. No start_date
     (implies draft).
   - Activity (`activity.Activity`): `activity_name` = "{topic} Quiz",
     `activity_instruction` = quiz text, `activity_type` = "Quiz",
     `subject` = request.subject, `term` = request.term, standard defaults
     (max_score=100, time_duration=30, passing_score=75, passing_score_type=
     "percentage", max_retake=1, retake_method="highest", shuffle_questions=
     True, is_graded=True).
   - If "both": create both, link activity to module via `additional_modules`
     M2M.
5. Store generated IDs in `generated_module_id` / `generated_activity_id`.
6. Set status to `complete` (or `failed` on error).

## UI Integration

### Subject detail page — "Generate with AI" button

The existing school-side subject detail page shows modules and activities.
Add a "Generate with AI" link/button alongside the existing "+ New module"
and "+ New activity" links.

This is a school-side page (not central portal), so it uses the school's
template system and URL routing. The button links to the generation form.

### Generation form page

URL: `/ai-content/generate/<int:subject_id>/`

Shows:
- Subject name + current term (auto-selected, changeable dropdown)
- Topic (text input, required)
- Learning objectives (textarea, required)
- Content type (radio: Module only / Quiz only / Both)
- Reference material (file input, optional, PDF only, max 50MB)
- LLM model (dropdown from `AI_CONTENT_MODELS` keys)
- "Generate" button

POST dispatches Celery task, redirects to subject detail page. A success
message (Django messages framework) tells the teacher content is being
generated.

### Permissions

The view checks if the current user has access to the subject using the same
permission logic as the existing module/activity create views. No new
permission model needed.

### No separate status page

Generated content appears directly in the subject's module/activity lists.
The GenerationRequest status is tracked in the database for debugging but
there's no dedicated status page — the teacher sees the new draft content
on the subject page after generation completes.

## URL Configuration

New URL patterns in `ai_content/urls.py`:

```
ai-content/generate/<int:subject_id>/ → generation form (GET + POST)
```

Included in `lms/urls.py` as:
```python
path('ai-content/', include('ai_content.urls')),
```

## Testing

### Model tests
- GenerationRequest creation with valid fields.
- Cascade delete with Subject.
- Status transitions.

### PDF extraction tests
- Extract text from a valid PDF (create a simple test PDF with reportlab or
  use a minimal PDF bytes fixture).
- Return empty string for invalid/corrupt file.
- Truncation to 8000 chars.

### LLM module tests
- Mock Anthropic API, verify prompt includes topic + objectives.
- Verify prompt includes reference text when provided.
- Valid response parsed for "both" content_type.
- Valid response parsed for "module" only.
- Valid response parsed for "quiz" only.
- Invalid response raises ValueError.

### Celery task tests
- Success with "both": mock LLM, verify Module + Activity created.
- Success with "module" only: verify only Module created.
- Success with "quiz" only: verify only Activity created.
- With reference PDF: verify text extracted and passed to LLM.
- LLM failure: verify status set to failed.

### View tests
- Form page renders for authorized user.
- POST triggers Celery task and redirects.
- Unauthorized user cannot access.
- File upload validation (PDF only).

## Configuration

Settings additions (in gitignored `lms/settings.py`):

```python
AI_CONTENT_MODELS = {
    "haiku": {
        "provider": "anthropic",
        "model": "claude-haiku-4-5-20251001",
        "api_key_env": "ANTHROPIC_API_KEY",
    },
    "sonnet": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-6",
        "api_key_env": "ANTHROPIC_API_KEY",
    },
}
AI_CONTENT_DEFAULT_MODEL = "haiku"
```

Environment variable: `ANTHROPIC_API_KEY` (same as central content, already
configured for Plus tier schools that also run Prime).
