# Auto-Quest Generation from Lesson Content

**Status:** Draft
**Date:** 2026-05-12
**Owner:** teryopitikin@gmail.com

## Problem

The existing quest map (`templates/student/gamification/quest_map.html`) maps 1:1 to `Module` rows: each uploaded lesson is one node. Students "complete" a lesson by viewing the file. This is shallow — there is no per-lesson learning check, and gamification cannot reflect comprehension.

We want: when a teacher uploads a lesson, the system generates a preset number of AI-authored quests from that lesson's content. Teachers review and publish the drafts. Quest completion drives module completion and can optionally feed the gradebook with a teacher-set weight.

## Goals

- Teacher chooses per lesson how quests are authored: **AI-assisted** (generate from uploaded file), **manual entry** (type in UI), or **bulk upload** (CSV/JSON template).
- Preset quest count configured per Subject (default 5) — applies to AI mode; manual/upload modes have no count enforcement.
- Draft-then-publish workflow with full teacher edit/delete/reorder/add-manual control.
- Quest completion is the source of truth for module completion.
- Optional gradebook integration via a new `gradebook_category = 'quest_completion'` component with a teacher-set weight, plus a per-quest `counts_toward_grade` toggle.
- Pluggable AI provider (Anthropic, OpenAI) selectable by site admin.
- Uniform percentage unit (float, 0.00–100.00, 2 decimal places) at every boundary so the gradebook sees nothing unusual.

## Non-Goals

- Auto-grading of free-form essay answers (reading_check uses keyword match; richer grading is future work).
- Auto-publishing without teacher review.
- Real-time collaborative editing of quest drafts.
- Celery/Redis infrastructure (uses background thread + DB-backed job model).

## Decisions Summary

| Decision | Choice |
|---|---|
| Quest types | Mix per quest: `quiz`, `reading_check`, `task` (AI picks per chunk) |
| Source content | Lesson uploaded file (`Module.file`) |
| Preset quest count | Per Subject (`Subject.quest_count_per_lesson`, default 5) |
| Authoring mode | Teacher picks per lesson: `ai` (auto-generate), `manual` (type in UI), or `upload` (CSV/JSON file) — **only modes enabled by the organization admin are shown** |
| Org admin gating | Registrar can enable/disable each authoring mode independently via `OrganizationQuestSettings` |
| Generation trigger | AI mode: teacher clicks "Generate quests" button. Manual/upload: teacher creates or imports directly. |
| Review flow | All AI quests start as `draft`; teacher publishes |
| AI provider | Pluggable: Anthropic + OpenAI, selected by `SiteSetting.quest_ai_provider` |
| Module completion rule | Module is complete when all published quests are completed by the student |
| Gradebook integration | Opt-in via `GradeBookComponents` row with `gradebook_category='quest_completion'`; teacher sets weight |
| Per-quest grading inclusion | `Quest.counts_toward_grade` BooleanField |
| Output unit to gradebook | `float`, 0.00–100.00, `round(..., 2)` — identical to `compute_component_subtotal` return shape |

## Data Model

### New models (in `gamification/`)

```python
class Quest(models.Model):
    KIND_CHOICES = [('quiz', 'Quiz'), ('reading_check', 'Reading Check'), ('task', 'Task')]
    STATUS_CHOICES = [('draft', 'Draft'), ('published', 'Published')]

    module = models.ForeignKey('module.Module', on_delete=models.CASCADE, related_name='quests')
    order = models.PositiveIntegerField(default=1)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    title = models.CharField(max_length=200)
    body = models.TextField()
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    counts_toward_grade = models.BooleanField(default=True)
    ai_provider = models.CharField(max_length=20, blank=True)   # 'anthropic'|'openai'|'manual'|'upload'
    source_chunk = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['module', 'order']

class QuestAttempt(models.Model):
    quest = models.ForeignKey(Quest, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    submitted_answer = models.JSONField(default=dict)
    is_correct = models.BooleanField(default=False)
    score = models.FloatField(default=0.0)        # 0.0..1.0 internal; only exposed as *100 outside this module
    completed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('quest', 'student')

class QuestGenerationJob(models.Model):
    STATUS_CHOICES = [('queued','Queued'),('running','Running'),('complete','Complete'),('failed','Failed')]
    module = models.ForeignKey('module.Module', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='queued')
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
```

DB-level guard: partial unique index on `QuestGenerationJob (module)` where `status IN ('queued','running')` — only one live job per module.

### Field additions on existing models

```python
# subject/models.py — Subject
quest_count_per_lesson = models.PositiveIntegerField(default=5)   # min 1, max 20 enforced in form
```

### Organization-level settings

Singleton model `OrganizationQuestSettings` (one row per deployment, enforced by `pk=1` get-or-create pattern used elsewhere in the project):

```python
class OrganizationQuestSettings(models.Model):
    ai_mode_enabled     = models.BooleanField(default=True)    # gate "Generate with AI"
    manual_mode_enabled = models.BooleanField(default=True)    # gate "Create manually"
    upload_mode_enabled = models.BooleanField(default=True)    # gate "Upload from file"
    ai_provider         = models.CharField(max_length=20, choices=[('anthropic','Anthropic'),('openai','OpenAI')], default='anthropic')
    updated_at          = models.DateTimeField(auto_now=True)
    updated_by          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
```

**Helper:** `OrganizationQuestSettings.load()` returns the singleton row, creating it with defaults if absent. All teacher views call this and pass the enabled flags into the template.

**Permission:** Edited only by users with the **registrar** role (the org-level admin in Classedge). Page lives at `/accounts/registrar/quest-settings/` under the existing registrar section.

**Enforcement rule:** Server-side check on every entry endpoint — generate, manual-create, upload — re-reads `load()` and returns 403 if that mode is disabled, regardless of what the UI showed. UI hiding is convenience; the server is the gate.

**Edge case:** If the admin disables **all three** modes, the registrar page shows a warning and the save is blocked. At least one mode must remain enabled at all times so teachers aren't locked out.

## Gradebook Integration

### Contract

The gradebook expects each component's subtotal as **`float` in [0.0, 100.0], rounded to 2 decimals**. This matches `gradebookcomponent/services/grades.py::compute_component_subtotal`.

### Quest score calculation (`gamification/quest_grading.py`)

```python
def get_student_quest_score(student, subject, term) -> float:
    """Return student's quest percentage across published, gradable quests
    in the subject/term. Missing attempts count as 0. Returns 0.0..100.0
    rounded to 2 decimals."""
    quests = Quest.objects.filter(
        module__subject=subject,
        module__term=term,
        status='published',
        counts_toward_grade=True,
    )
    if not quests.exists():
        return 0.0
    attempts = {a.quest_id: a for a in
                QuestAttempt.objects.filter(quest__in=quests, student=student)}
    total = 0.0
    for q in quests:
        a = attempts.get(q.id)
        total += (a.score * 100.0) if a else 0.0
    return round(total / quests.count(), 2)
```

### Gradebook code change

One branch added at the top of `compute_component_subtotal`:

```python
def compute_component_subtotal(student, subject, term, component):
    if component.gradebook_category == 'quest_completion':
        from gamification.quest_grading import get_student_quest_score
        return get_student_quest_score(student, subject, term)
    # ... existing ActivityTypePercentage loop unchanged ...
```

`compute_weighted_grade` is **not modified** — it already weights any subtotal by `component.percentage` uniformly.

### Opt-in semantics

- No `GradeBookComponents` row with `gradebook_category='quest_completion'` for the (teacher, subject, term) → quests do **not** affect grades. They remain visible in the quest map as pure gamification.
- Teacher creates such a row, sets `percentage` weight → quests contribute to the grade.
- Teacher can untick `counts_toward_grade` on individual quests they want as practice-only.

## Generation Pipeline

Triggered by `POST /gamification/quests/generate/<module_id>/` (teacher only).

1. Resolve `N = module.subject.quest_count_per_lesson`.
2. Create `QuestGenerationJob(status='queued')`. Return `job_id` immediately (HTTP 202).
3. Spawn background thread (Django `threading.Thread`, daemon). Inside the thread:
   1. Set job `status='running'`.
   2. Extract text from `module.file`:
      - `.pdf` → `pypdf`
      - `.docx` → `python-docx`
      - `.pptx` → `python-pptx`
      - `.txt` → read directly
      - other → fail job with `"Unsupported file type"`.
   3. Clean whitespace, truncate to ~20,000 chars hard cap (cost guardrail), chunk by paragraph.
   4. Resolve provider from `SiteSetting.quest_ai_provider`.
   5. Call `provider.generate(text, n=N)` — returns JSON matching schema below.
   6. Validate JSON with `jsonschema`. On failure, ONE retry with an error-corrective prompt. Second failure → fail job, log truncated raw output.
   7. Persist as `Quest` rows with `status='draft'`, `order=1..N`, `source_chunk` recorded, `ai_provider` snapshot recorded.
   8. Set job `status='complete'`, `finished_at=now()`.
4. Frontend polls `GET /gamification/quests/job/<job_id>/` every 2s; redirects to draft-review page on success, shows error on failure.

### LLM output schema (provider-agnostic)

```json
{
  "quests": [
    {
      "kind": "quiz",
      "title": "string <=200",
      "body": "prompt text",
      "payload": {"options": ["A","B","C","D"], "correct_index": 0},
      "source_chunk": "excerpt this was based on"
    },
    {
      "kind": "reading_check",
      "title": "...",
      "body": "instruction",
      "payload": {"reading": "...", "question": "...", "expected_keywords": ["x","y"]},
      "source_chunk": "..."
    },
    {
      "kind": "task",
      "title": "...",
      "body": "task statement",
      "payload": {"rubric": "...", "self_check": true},
      "source_chunk": "..."
    }
  ]
}
```

Validation enforces: exactly N quests, unique titles within job, payload shape matches `kind`.

### Provider abstraction (`gamification/ai_providers/`)

```python
class QuestProvider(Protocol):
    def generate(self, text: str, n: int) -> dict: ...

class AnthropicProvider:   # reuses settings.RAG_TUTOR_LLM_MODEL + ANTHROPIC_API_KEY
class OpenAIProvider:      # new dependency: openai SDK; OPENAI_API_KEY env var
```

Factory `get_provider()` reads `SiteSetting.quest_ai_provider`.

### Regeneration rules

- Regeneration overwrites all `status='draft'` quests for the module.
- Regeneration **never** touches `status='published'` quests (those need explicit teacher delete).

## Manual Authoring & Bulk Upload

The same `Quest` model and review/publish flow serve all three authoring modes. The differences are only at the *entry point*.

### Mode selector

On the lesson detail page, the teacher sees up to three buttons when no quests exist yet — **only the modes the organization admin has enabled** are rendered:

- **Generate with AI** → runs the generation pipeline (above). Hidden if `ai_mode_enabled=False`.
- **Create manually** → empty review page; teacher clicks "Add quest" to author each. Hidden if `manual_mode_enabled=False`.
- **Upload from file** → file picker for `.csv`/`.json`. Hidden if `upload_mode_enabled=False`.

If only one mode is enabled, that single button is shown. If two are enabled, two buttons. The server enforces the same gate on the receiving endpoints, returning 403 if a disabled mode is invoked directly.

Once any quest exists for the module (regardless of mode), the buttons collapse into the review page's normal "Add quest" / "Regenerate drafts" / "Import more" actions. Modes are **not exclusive**: a teacher can AI-generate 5 quests, manually add 2 more, and upload 3 from a CSV — they all live in the same `Quest` table for that module.

### Manual entry

Reuses the inline quest editor we already need for the review page. No additional UI. Quests created this way are saved with `status='draft'`, `ai_provider='manual'`. Teacher publishes when ready, same as AI drafts.

### Bulk upload (CSV / JSON)

**CSV template** (downloadable from the upload page):

```csv
kind,title,body,payload_json,counts_toward_grade
quiz,"Capital of France","Pick the capital","{""options"":[""Paris"",""Lyon"",""Nice"",""Marseille""],""correct_index"":0}",true
reading_check,"Photosynthesis basics","Read and answer","{""reading"":""...text..."",""question"":""What gas is released?"",""expected_keywords"":[""oxygen""]}",true
task,"Field sketch","Sketch a leaf cross-section","{""rubric"":""Labels include cuticle, mesophyll, stomata"",""self_check"":true}",false
```

**JSON template** — same shape as the LLM output schema's `quests` array, minus `source_chunk`:

```json
[
  {"kind":"quiz","title":"...","body":"...","payload":{"options":["A","B","C","D"],"correct_index":0},"counts_toward_grade":true}
]
```

**Parser (`gamification/quest_import.py`):**

1. Sniff format by file extension; reject otherwise.
2. Parse rows/items into the same in-memory dict shape as the LLM output.
3. Run the **same `jsonschema` validator** used for AI output (per-quest, not the wrapped envelope). Single validation path keeps behavior consistent.
4. On any row error → reject the whole upload, return a per-row error report. No partial imports.
5. On success → create `Quest` rows with `status='draft'`, `ai_provider='upload'`, `source_chunk=''`, `order` continuing from the current max for that module.

**Constraints:**

- File size hard cap: 1 MB.
- Row cap: 200 quests per upload.
- No requirement to match `Subject.quest_count_per_lesson` — that field only governs AI generation.

## UI Surfaces

### Registrar (organization admin)

- **Quest settings page** (`/accounts/registrar/quest-settings/`): three toggles (AI / Manual / Upload), one provider dropdown (Anthropic / OpenAI). Save button. Disabled-save guard if all three toggles are off. Audit fields (`updated_at`, `updated_by`) shown read-only.

### Teacher

- **Subject edit form:** new field "Quests per lesson" (default 5, min 1, max 20).
- **Lesson detail page (no quests yet):** three buttons — "Generate with AI", "Create manually", "Upload from file". After any quest exists, button bar collapses into the review page's actions.
- **AI mode:** shows spinner + status while the generation job runs; redirects to review page on success.
- **Upload mode:** file picker with "Download template (CSV)" and "Download template (JSON)" links; rejects whole file on any row error with per-row report.
- **Quest review page** (`/gamification/quests/module/<id>/review/`):
  - List of draft quests with inline edit, reorder, delete, add-manual, `counts_toward_grade` toggle.
  - "Publish all" button → batch flip drafts to published in one transaction.
  - Separate "Published" section, editable with a warning when attempts exist.
- **Gradebook editor (existing UI):** `gradebook_category` dropdown gains "Quest Completion" option. Teacher sets `percentage` weight as for any other component. No quest-specific UI here.

### Student

- **Quest map (existing template):** node states now compute from "all graded+published quests complete" rather than reading `StudentProgress.completed` directly. Signal on `QuestAttempt.save()` keeps `StudentProgress.completed` in sync so other app code is unaffected.
- **Module quest list page:** clicking a quest map node opens this — shows the lesson's published quests with completion checkmarks and a "Start" / "Continue" button.
- **Quest player page** (`/gamification/quests/module/<id>/play/`): renders the next unattempted quest based on its `kind`:
  - `quiz` → MCQ form, instant feedback.
  - `reading_check` → reading panel + short-answer; autograded by keyword match in `payload.expected_keywords`.
  - `task` → task statement + self-check checkbox (if `payload.self_check`), else queued for teacher review.
- **Student dashboard / quest map header:** small badge "Quest Level: 72.50%" per subject, **shown only when the teacher has enabled the gradebook component**. Same number the gradebook will use — no two reconciliations.

## Error Handling

| Condition | Behavior |
|---|---|
| Unsupported file type | Fail job fast, friendly message, no retry |
| Extracted text < 200 usable chars | Fail with "Lesson file appears empty or unreadable" |
| LLM request timeout (60s) | Fail; teacher can click Generate again |
| LLM returns invalid JSON | One automatic retry with corrective prompt; second failure logs truncated raw output to admin-only log |
| Concurrent generate clicks | DB partial-unique index rejects second job while first is running |
| Teacher edits published quest after attempts exist | Allowed, with a warning banner; existing attempts unchanged |

## Testing

- **Unit:** `quest_grading.get_student_quest_score` — zero quests, all unattempted, mixed scores, `counts_toward_grade=False` excluded, draft excluded.
- **Unit:** schema validation rejects wrong N (AI mode only), duplicate titles, mismatched payload shapes.
- **Unit:** CSV and JSON importer — happy path, malformed row rejects whole file, oversize file rejected, row cap enforced.
- **Unit:** `OrganizationQuestSettings.load()` creates default singleton; cannot save with all three modes disabled.
- **Integration:** disabled authoring mode is hidden in teacher UI **and** server returns 403 if endpoint is hit directly.
- **Integration:** registrar role required for quest-settings page; other roles get 403.
- **Unit:** each text extractor on a small fixture file.
- **Integration:** `compute_component_subtotal` returns identical float type/precision for a quest component as for a normal activity component.
- **Integration:** generation job end-to-end with a mocked provider that returns canned JSON.
- **Integration:** student completes all published quests in a module → `StudentProgress.completed=True` via signal.
- **Manual / smoke:** real PDF upload through the teacher UI, generate, edit, publish, student plays.

## Migration / Rollout

1. Create migrations: new models + `Subject.quest_count_per_lesson` + `gradebook_category` choice expansion (if implemented as a choice; if free-text already, no change needed).
2. Existing modules: no auto-generation. Teachers explicitly opt in per lesson.
3. Existing `StudentProgress` rows: untouched. Once a teacher generates and publishes quests for a module, the signal-driven recompute takes over for that module only.
4. Feature is usable end-to-end the moment migrations apply; no flag needed.

## Open Questions

- Should `expected_keywords` use stemming / case-insensitive match? Recommend: lowercase, strip punctuation, exact substring match, require ≥50% of keywords present. Configurable later.
- Cap regeneration count per module per day to limit cost? Defer until we see actual usage.
