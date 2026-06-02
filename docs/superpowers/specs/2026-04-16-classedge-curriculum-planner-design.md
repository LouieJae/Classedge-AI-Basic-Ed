# Sub-project 4b — Curriculum Planner

## Overview

The curriculum planner takes a parsed textbook (from 4a) and a school's session
schedule, calls an LLM to produce a week-by-week chapter mapping, and presents
it to the publisher for review and editing. The approved plan feeds into
Sub-project 4c for per-week content generation.

## Scope

**In scope:**
- School-side schedule API endpoint (session count + minutes from Subject schedule + Term)
- LLM configuration with multiple models for comparison
- `CurriculumPlan` model (JSONField for week-by-week mapping)
- Celery task for LLM-assisted plan generation
- Bulk-run option (generate plans for all textbooks in a subject)
- Inline plan editor with constraints (every chapter assigned exactly once)
- Plan approval workflow (draft → approved / rejected)

**Out of scope:**
- Per-week content generation (4c)
- Actual teaching schedule creation on the school side
- Question generation for activities

## School-side Schedule API

New endpoint: `GET /api/central/schedule/<int:subject_id>/`

Protected by `require_central_token` bearer auth (same as existing ingest endpoints).

Response:
```json
{
  "subject_id": 42,
  "subject_name": "Math 101",
  "term": {
    "name": "1st Semester 2026-2027",
    "start_date": "2026-08-15",
    "end_date": "2026-12-15"
  },
  "sessions": [
    {"date": "2026-08-16", "start_time": "08:00", "end_time": "09:30", "minutes": 90},
    {"date": "2026-08-18", "start_time": "08:00", "end_time": "09:30", "minutes": 90}
  ],
  "session_count": 48,
  "minutes_per_session": 90
}
```

The endpoint queries:
1. The Subject's related Term for semester start/end dates.
2. The Subject's preset session schedule for individual session dates and times.
3. `minutes_per_session` is the most common (mode) duration across sessions.

Located in `received_central_content/views/schedule.py`, registered in
`received_central_content/urls.py`.

Returns 404 if subject not found, 400 if no term assigned.

## LLM Configuration

Settings define multiple LLM providers for comparison:

```python
CURRICULUM_PLANNER_MODELS = {
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
CURRICULUM_PLANNER_DEFAULT_MODEL = "haiku"
```

A thin `central_content/llm.py` module handles the API call:
- Takes: chapter list (number, title, page range), session count, minutes per
  session, model key.
- Builds a structured prompt instructing the LLM to assign every chapter to
  exactly one week, keep chapters sequential, and return JSON.
- Calls the Anthropic API using the configured model and API key.
- Parses and returns the JSON response.

The prompt enforces constraints: every chapter assigned once, no gaps, ordered
sequentially. The response is validated before storing.

Future models (OpenAI, local LLMs) can be added by extending the provider
dispatch in `llm.py`.

## Data Model

### `CurriculumPlan`

| Field | Type | Notes |
|---|---|---|
| `textbook` | ForeignKey | FK to `ParsedTextbook`, CASCADE. Multiple plans per textbook. |
| `school_subject_id` | PositiveIntegerField | School-side Subject PK (from schedule fetch). |
| `session_count` | PositiveIntegerField | Number of sessions used for planning. |
| `minutes_per_session` | PositiveIntegerField | Duration per session. |
| `model_key` | CharField(50) | LLM model key (e.g., "haiku", "sonnet"). |
| `plan_data` | JSONField | Week-by-week mapping (see format below). |
| `status` | CharField | `draft` / `approved` / `rejected` |
| `generated_by` | ForeignKey | FK to `CentralStaff`, PROTECT. |
| `created_at` | DateTimeField | auto_now_add |
| `updated_at` | DateTimeField | auto_now |

`plan_data` format:
```json
[
  {
    "week": 1,
    "chapters": [1, 2],
    "title": "Foundations",
    "description": "Introduction to real numbers and basic operations"
  },
  {
    "week": 2,
    "chapters": [3],
    "title": "Expressions",
    "description": "Algebraic expressions and simplification"
  }
]
```

### Validation rules (enforced on save)

1. Every chapter number from the textbook must appear in exactly one week.
2. No chapter numbers that don't exist in the textbook.
3. Weeks must be sequential starting from 1.
4. At least one chapter per week.

## Celery Tasks

### `generate_curriculum_plan`

Arguments: `textbook_id`, `school_subject_id`, `model_key`, `triggered_by_id`

1. Load `ParsedTextbook` and its `ParsedChapter` rows.
2. Fetch schedule from school API via the binding's school base_url
   (`GET /api/central/schedule/<school_subject_id>/`).
3. Call LLM via `central_content/llm.py` with chapter list + session data.
4. Validate response: every chapter assigned exactly once, weeks sequential.
5. If valid: create `CurriculumPlan` with status `draft`.
6. If invalid: retry LLM call once with a correction prompt appended. If still
   invalid, create plan with status `draft` and store validation warnings
   alongside the plan_data.
7. On failure (API error, timeout): no plan created, return error dict.

### `bulk_generate_plans`

Arguments: `central_subject_id`, `model_key`, `school_id`, `triggered_by_id`

Finds all textbooks with `toc_ready` status under the subject. For each,
dispatches `generate_curriculum_plan` as a separate Celery task.

## Central Portal UI

### Textbook detail page — "Generate Plan" button

Visible when textbook status is `toc_ready`. Leads to the plan generation page.
Also lists existing plans for this textbook: model used, status, date. Links
to each plan detail.

### Plan generation page

Publisher selects:
- Target school + subject (dropdown, fetches schedule to show session
  count/duration for confirmation)
- LLM model (dropdown from `CURRICULUM_PLANNER_MODELS` keys)
- "Generate" button dispatches the Celery task

After generation, redirects to the plan detail page.

### Plan detail page — inline editor

Shows the week-by-week mapping in an editable table:
- Each row: week number, assigned chapters (with titles from ParsedChapter),
  description text field.
- Publisher can move chapters between weeks (select + move up/down buttons).
- Inline validation: red warning if any chapter unassigned or duplicated.
- Actions: "Save Changes", "Approve", "Reject", "Regenerate with different
  model" (link back to generation page).
- Approved plans are locked (read-only, no more editing).

### Subject detail page — bulk run

"Generate Plans for All Textbooks" button visible to publishers. Opens a
confirmation dialog with model selection. Dispatches `bulk_generate_plans`.

## Testing

### School-side API tests
- Schedule endpoint returns correct session data for a Subject with Term +
  schedule.
- Subject with no term returns 400.
- Unknown subject returns 404.
- Bearer auth required (401 without token).

### LLM module tests
- Mock the Anthropic API call, verify prompt includes chapter list and session
  count.
- Valid response parsed into correct structure.
- Invalid response (missing chapters) detected by validation.

### Model tests
- `CurriculumPlan` creation with valid plan_data.
- Multiple plans per textbook allowed.
- Validation rejects plan with duplicate chapters.
- Validation rejects plan with missing chapters.
- Validation rejects non-sequential weeks.
- Status transitions (draft → approved, draft → rejected).

### Celery task tests
- `generate_curriculum_plan` success: mock schedule fetch + LLM call, verify
  plan created with draft status.
- `generate_curriculum_plan` LLM failure: mock API error, verify no plan
  created.
- `generate_curriculum_plan` invalid LLM response: verify retry with
  correction prompt.
- `bulk_generate_plans`: mock to verify it dispatches per-textbook tasks.

### View tests
- Plan generation page renders with model dropdown.
- POST triggers Celery task and redirects.
- Plan detail page shows weeks and chapters.
- Plan edit saves updated plan_data, validation rejects invalid edits.
- Approve locks the plan (further edits return error).
- Reject sets status.
- Bulk run triggers tasks for all toc_ready textbooks.

## Configuration

Settings additions (in gitignored `lms/settings.py`):
```python
CURRICULUM_PLANNER_MODELS = {
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
CURRICULUM_PLANNER_DEFAULT_MODEL = "haiku"
```

Environment variable: `ANTHROPIC_API_KEY` (required for LLM calls).
