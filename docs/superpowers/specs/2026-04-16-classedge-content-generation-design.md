# Sub-project 4c — Per-week Content Generation

## Overview

Takes an approved CurriculumPlan (from 4b) and generates CentralModule +
CentralActivity rows for each week. The LLM uses parsed chapter text (from
4a's ParsedChapter) to produce lesson descriptions and quiz content. All
generated rows are in draft state for publisher review.

## Scope

**In scope:**
- `ContentGenerationJob` model to track generation progress
- Celery task for per-week content generation (module + activity)
- LLM prompt for lesson outline + quiz generation
- Chapter text preparation (trigger parsing if needed)
- "Generate Content" button on plan detail page
- Generation status page with per-week progress
- Bulk generation with model selection

**Out of scope:**
- Question bank / individual question models (activities store questions as
  instruction text)
- File/media generation for modules
- Editing UI for generated content (existing module/activity edit views suffice)
- Auto-submission for review (publisher decides when to submit)

## Data Model

### `ContentGenerationJob`

| Field | Type | Notes |
|---|---|---|
| `curriculum_plan` | ForeignKey | FK to `CurriculumPlan`, CASCADE. |
| `model_key` | CharField(50) | LLM model key used. |
| `status` | CharField | `pending` / `running` / `complete` / `failed` |
| `total_weeks` | PositiveIntegerField | Number of weeks to generate. |
| `completed_weeks` | PositiveIntegerField | Weeks successfully generated. Default 0. |
| `failed_weeks` | PositiveIntegerField | Weeks that failed. Default 0. |
| `error_message` | TextField | Blank. Overall error if entire job fails. |
| `week_results` | JSONField | Per-week status details (see format below). |
| `triggered_by` | ForeignKey | FK to `CentralStaff`, PROTECT. |
| `created_at` | DateTimeField | auto_now_add |
| `updated_at` | DateTimeField | auto_now |

`week_results` format:
```json
[
  {
    "week": 1,
    "status": "done",
    "module_id": 42,
    "activity_id": 55
  },
  {
    "week": 2,
    "status": "failed",
    "error": "Chapter parsing failed for chapter 3"
  },
  {
    "week": 3,
    "status": "pending"
  }
]
```

## LLM Content Generation

### What gets generated per week

**CentralModule:**
- `file_name`: "Week {N}: {plan week title}"
- `description`: Multi-paragraph lesson outline — key concepts, learning
  objectives, teaching notes. Generated from parsed chapter text.
- `order`: Week number from the plan.
- `file`, `url`, `iframe_code`: Left empty (no file generation).
- `state`: DRAFT
- `central_subject`: Same as the plan's textbook's central_subject.
- `created_by`: The staff member who triggered generation.

**CentralActivity:**
- `activity_name`: "Week {N} Quiz: {plan week title}"
- `activity_instruction`: Formatted quiz — 5-10 questions (mix of multiple
  choice and short answer), generated from chapter text.
- `activity_type`: FK to ActivityType where name="Quiz".
- `max_score`: 100
- `time_duration`: 30 (minutes)
- `passing_score`: 75
- `passing_score_type`: "percentage"
- `max_retake`: 1
- `retake_method`: "highest"
- `shuffle_questions`: True
- `is_graded`: True
- `state`: DRAFT
- `central_subject`: Same as the plan's textbook's central_subject.
- `created_by`: The staff member who triggered generation.
- `related_modules`: M2M link to the generated module for this week.

### LLM module extension

Extend `central_content/llm.py` with a new function:

`call_content_generator(chapter_texts, week_title, week_description, session_count, minutes_per_session, model_key)`

Takes:
- `chapter_texts`: List of dicts with `{"number": int, "title": str, "text": str}`
  where `text` is from ParsedChapter.parsed_data (truncated to ~4000 chars per
  chapter to stay within context limits).
- `week_title`, `week_description`: From the plan_data entry.
- `session_count`, `minutes_per_session`: From the CurriculumPlan.
- `model_key`: Which LLM to use.

Returns:
```json
{
  "lesson_description": "Multi-paragraph lesson outline...",
  "quiz_questions": "Formatted quiz text with questions..."
}
```

The prompt instructs the LLM to:
1. Write a lesson outline covering the chapters' key concepts and learning
   objectives, suitable for the given number of sessions and minutes.
2. Write 5-10 quiz questions (numbered, mix of multiple choice with 4 options
   marked A-D, and short answer) covering the chapter content.

Response is validated: must contain both keys, both non-empty strings.

## Celery Tasks

### `generate_week_content`

Arguments: `job_id`, `week_index` (0-based index into plan_data)

1. Load `ContentGenerationJob` and its `CurriculumPlan`.
2. Get the week entry from `plan_data[week_index]`.
3. For each chapter number in the week's chapters:
   a. Load `ParsedChapter` from the textbook.
   b. If `parsed_data` is NULL and status is `pending`: dispatch
      `parse_single_chapter` synchronously (call `.apply()` not `.delay()`),
      then reload. If still NULL after parsing, mark week as failed, skip.
   c. Extract text from `parsed_data` (truncate to ~4000 chars).
4. Call `call_content_generator()` with chapter texts + week context.
5. Create CentralModule + CentralActivity in a transaction.
6. Link activity to module via `related_modules.add()`.
7. Update `week_results[week_index]` with module_id/activity_id and status.
8. Increment `completed_weeks` (or `failed_weeks` on error).
9. If all weeks processed, set job status to `complete` (or `failed` if all
   weeks failed).

### `run_content_generation`

Arguments: `job_id`

1. Load `ContentGenerationJob`, set status to `running`.
2. For each week index in range(total_weeks):
   call `generate_week_content(job_id, week_index)` synchronously (sequential,
   not parallel — avoids rate limits and keeps progress linear).
3. After all weeks: set job status based on results.

This is dispatched via `.delay()` from the view.

## Central Portal UI

### Plan detail page — "Generate Content" button

Added below the existing approve/reject buttons on approved plans only.
Publisher-only. Shows:
- Model selection dropdown (from `CURRICULUM_PLANNER_MODELS`)
- "Generate Content" button
- List of existing generation jobs for this plan (status, date, link)

### Content generation status page

URL: `/subjects/<id>/textbooks/<tid>/plans/<pid>/jobs/<jid>/`

Shows:
- Job metadata: model used, triggered by, created at
- Overall progress bar (completed_weeks / total_weeks)
- Per-week table:
  - Week number, title, status (pending/generating/done/failed)
  - For done weeks: links to the generated module and activity
  - For failed weeks: error message
- HTMX polling on the status badge (same pattern as textbook parsing status)

### No changes to existing module/activity views

Generated modules and activities appear in the subject detail page's existing
lists. Publishers edit them through the existing module/activity edit forms.

## Testing

### Model tests
- `ContentGenerationJob` creation with valid fields.
- Job cascade-deletes with CurriculumPlan.
- `week_results` JSON stores/retrieves correctly.

### LLM module tests
- Mock Anthropic API, verify prompt includes chapter text and week context.
- Valid response parsed into correct structure.
- Invalid response (missing keys) raises ValueError.

### Celery task tests
- `generate_week_content` success: mock LLM call, verify CentralModule +
  CentralActivity created with correct fields.
- `generate_week_content` with unparsed chapter: mock `parse_single_chapter`,
  verify it's called synchronously.
- `generate_week_content` chapter parse failure: verify week marked as failed.
- `run_content_generation` success: mock `generate_week_content`, verify all
  weeks processed and job status set to complete.
- `run_content_generation` partial failure: some weeks fail, job still
  completes with correct counts.

### View tests
- Generate content button visible on approved plans, hidden on draft/rejected.
- POST triggers Celery task and redirects.
- Publisher-only access (editor/reviewer cannot trigger).
- Job status page renders with correct week data.
- HTMX status endpoint returns updated progress.

## Configuration

No new settings needed. Reuses `CURRICULUM_PLANNER_MODELS` and
`ANTHROPIC_API_KEY` from Sub-project 4b.
