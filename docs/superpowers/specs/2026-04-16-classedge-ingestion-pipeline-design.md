# Sub-project 4a — PDF Ingestion Pipeline

## Overview

Central portal staff upload a textbook PDF for a CentralSubject. A Celery task
sends the PDF to a MinerU Docker microservice that extracts the table of
contents (chapter titles, page ranges, hierarchy). The result is stored in a
`ParsedTextbook` model with child `ParsedChapter` rows — one per chapter, all
in `pending` state. Full chapter-level parsing happens on-demand in Sub-project
4b when the curriculum planner needs specific chapter content.

## Scope

**In scope:**
- MinerU Docker microservice (FastAPI wrapper, two endpoints, file-based cache)
- `ParsedTextbook` and `ParsedChapter` models
- Celery task for TOC extraction
- Celery task for single-chapter parsing (infrastructure for 4b, not triggered by 4a)
- Central portal UI: upload form, textbook status, chapter list
- WebSocket notification on parse completion

**Out of scope:**
- Session count / schedule data (4b)
- Chapter-to-session mapping (4b)
- Content generation from parsed text (4c)
- School-side anything

## MinerU Microservice

A stateless Docker container running MinerU with a FastAPI wrapper. No database,
no authentication. Receives a PDF, returns JSON.

### Endpoints

**`POST /parse/toc`**

Accepts a PDF file (multipart), returns chapter/section structure.

Response:
```json
{
  "title": "Algebra Fundamentals",
  "total_pages": 420,
  "chapters": [
    {"number": 1, "title": "Real Numbers", "start_page": 1, "end_page": 24},
    {"number": 2, "title": "Expressions", "start_page": 25, "end_page": 51}
  ]
}
```

**`POST /parse/chapter`**

Accepts a PDF file (multipart) + `start_page` and `end_page` form fields.
Returns full structured JSON for that chapter.

Response:
```json
{
  "chapter_number": 1,
  "title": "Real Numbers",
  "sections": [
    {"heading": "1.1 Natural Numbers", "text": "...", "images": ["img_001.png"]},
    {"heading": "1.2 Integers", "text": "...", "images": []}
  ]
}
```

### Caching

File-based cache in a Docker volume (survives container restarts):

- **TOC cache key:** `{sha256_of_pdf}_toc.json`
- **Chapter cache key:** `{sha256_of_pdf}_ch{start_page}_{end_page}.json`
- On success: result written to cache before returning.
- On failure: no cache entry written. Retry re-parses from scratch for that
  unit only. Previously cached results (other chapters, TOC) are preserved.
- If the same PDF + same page range is requested again, cached result is
  returned immediately without re-parsing.

This means if parsing 10 chapters fails on chapter 7, chapters 1-6 are cached
and a retry only processes 7-10.

### Docker

- Base image with MinerU + dependencies pre-installed
- FastAPI app as entrypoint
- Exposed port (configurable, default 8765)
- Volume mount for cache directory
- Health check endpoint: `GET /health`

## Data Model

### `ParsedTextbook`

| Field | Type | Notes |
|---|---|---|
| `central_subject` | ForeignKey | FK to `CentralSubject`, CASCADE. Multiple textbooks per subject allowed. |
| `title` | CharField(200) | Extracted from PDF metadata or entered by staff. |
| `original_file` | FileField | The uploaded PDF. |
| `file_hash` | CharField(64) | SHA-256 hex digest. Used as MinerU cache key. |
| `toc_data` | JSONField | Chapter list from `/parse/toc`. Null until parsed. |
| `status` | CharField | `uploading` / `parsing_toc` / `toc_ready` / `failed` |
| `error_message` | TextField | Blank on success, populated on failure. |
| `uploaded_by` | ForeignKey | FK to `CentralStaff`, PROTECT. |
| `created_at` | DateTimeField | auto_now_add |
| `updated_at` | DateTimeField | auto_now |

### `ParsedChapter`

| Field | Type | Notes |
|---|---|---|
| `textbook` | ForeignKey | FK to `ParsedTextbook`, CASCADE. |
| `chapter_number` | PositiveIntegerField | From TOC. |
| `title` | CharField(200) | Chapter title from TOC. |
| `start_page` | PositiveIntegerField | First page of chapter. |
| `end_page` | PositiveIntegerField | Last page of chapter. |
| `parsed_data` | JSONField | Null until parsed. Filled by `/parse/chapter`. |
| `status` | CharField | `pending` / `parsing` / `complete` / `failed` |
| `error_message` | TextField | Blank on success, populated on failure. |

`ParsedChapter` rows are created automatically from the TOC response. Chapter
parsing is triggered on-demand by 4b, not by 4a.

## Upload Flow

### Step 1: Upload form

Central portal Publisher or Editor navigates to a CentralSubject detail page.
A "Textbooks" section shows existing textbooks. An "Upload Textbook" button
opens a form with:
- File picker (PDF only)
- Optional title field (defaults to PDF filename without extension)

POST creates a `ParsedTextbook` row with status `uploading` and dispatches the
Celery task.

### Step 2: Celery task `parse_textbook_toc`

1. Compute SHA-256 of the uploaded file, save to `file_hash`.
2. Set status to `parsing_toc`.
3. POST the PDF to MinerU's `/parse/toc` endpoint.
4. On success:
   - Store TOC JSON in `toc_data`.
   - Create `ParsedChapter` rows (one per chapter, all status `pending`).
   - Set textbook status to `toc_ready`.
5. On failure:
   - Set status to `failed`, save error message.
6. Send WebSocket notification to the uploading user (success or failure).

### Step 3: Chapter parsing (infrastructure only)

Celery task `parse_single_chapter(parsed_chapter_id)`:

1. Load the `ParsedChapter` and its parent textbook.
2. Set chapter status to `parsing`.
3. POST the PDF + page range to MinerU's `/parse/chapter`.
4. On success: save `parsed_data`, set status to `complete`.
5. On failure: set status to `failed`, save error.

This task is defined in 4a but not triggered by any 4a code. Sub-project 4b
calls it when it needs a specific chapter's content.

## Central Portal UI

### Subject detail page — Textbooks section

Below the existing modules/activities sections, a new "Textbooks" card:
- Lists uploaded textbooks: title, page count, status badge, upload date.
- Status badges: "Processing..." (amber), "Ready" (green), "Failed" (red).
- "Upload Textbook" button (Publisher/Editor only).
- WebSocket updates the status badge without page refresh.

### Textbook detail page

Shows:
- Title, total pages, file hash, uploaded by, date.
- "Re-upload" action if status is `failed`.
- Chapter list table: number, title, page range, parse status.
- No chapter action buttons in 4a (those come in 4b).

### Permissions

- Publisher and Editor can upload and view textbooks.
- Reviewer can view only.

### Navigation

No new nav entries. Textbooks are accessed through the subject detail page.

## Testing

### MinerU service tests
- TOC extraction from a small test PDF (2-3 pages, 2 chapters).
- Chapter parsing for a specific page range.
- Cache hit: parse once, verify second call returns cached result without
  re-parsing.
- Error handling: corrupted PDF returns appropriate error response.
- Error handling: empty file returns appropriate error response.

### Django model tests
- `ParsedTextbook` creation with FK to CentralSubject.
- Multiple textbooks per subject.
- `ParsedChapter` creation from TOC data.
- Status transitions on both models.

### Celery task tests
- `parse_textbook_toc` success: mock MinerU HTTP call, verify TOC stored and
  `ParsedChapter` rows created with status `pending`.
- `parse_textbook_toc` failure: mock MinerU error, verify textbook status
  `failed` with error message.
- `parse_single_chapter` success: mock MinerU call, verify `parsed_data`
  stored and chapter status `complete`.
- `parse_single_chapter` failure: mock failure, verify chapter status `failed`.

### View tests
- Upload form renders for Publisher/Editor, forbidden for Reviewer.
- POST creates `ParsedTextbook` and triggers Celery task.
- Textbook detail page shows chapter list from TOC.
- Subject detail page shows textbook section.

## Configuration

Central portal `settings.py` additions:
- `MINERU_SERVICE_URL` — URL of the MinerU microservice (default
  `http://localhost:8765`).
- `MINERU_TIMEOUT` — request timeout in seconds (default 120 for TOC, 300 for
  chapter parsing).
