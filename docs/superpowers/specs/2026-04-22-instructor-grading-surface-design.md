# Instructor Grading Surface — Design

**System:** Classedge LMS (`~/classedge`)
**Date:** 2026-04-22
**App:** `gradebookcomponent/` (extended)
**Origin:** Relocated from Classedge Content Generator M9 — grading is engagement/delivery, belongs in the LMS.

All function signatures in this spec include a `[Classedge LMS]` label per the repo-wide convention for Classedge-related code.

---

## 1. Scope & Goal

Deliver a teacher-facing grading surface with three primary screens:

1. **Gradebook home** — landing page showing one tile per subject the teacher owns or collaborates on, each with a "X items need grading" badge.
2. **Subject gradebook grid** — full-page grid (rows = students, columns = activities, cells = scores) for one subject and term, with weighted category subtotals and CSV export.
3. **Needs-grading queue + full-page grading view** — prioritised queue of ungraded submissions across all a teacher's subjects; click a row to open a full-page grading view with "Save & Next" workflow.

### 1.1 In scope

- New `feedback` text field on `StudentActivity`
- Six new URL routes in `gradebookcomponent`
- Six new templates (four full pages + two HTMX fragments)
- Needs-grading query service
- CSV export streaming
- Manual-override flow with required reason, writing to existing `ScoreChangeLog`
- Sidebar nav entry in `teacher_base.html` and a "Open Gradebook" shortcut on existing teacher-dashboard subject cards

### 1.2 Out of scope (deferred)

- Per-question feedback on essays (single feedback field per `StudentActivity` for v1)
- Bulk grade entry directly into grid cells (grade via queue or inline override)
- Grade release / publish workflow (existing `Activity.show_score` continues to control visibility)
- Student-facing changes
- Playwright / browser tests (not in current codebase convention)

### 1.3 Success criteria

- A teacher can reach the gradebook in one click from the sidebar and in one click from a dashboard subject card.
- A teacher sees at a glance how many items need their attention across all subjects.
- A teacher can grade essays/documents sequentially without returning to the queue between each.
- An override writes a `ScoreChangeLog` row with a non-empty reason.
- CSV export opens cleanly in Excel and matches on-screen scores, category subtotals, and weighted final grade.

---

## 2. Data model changes

### 2.1 New field

```python
# activity/models/student_activity_model.py

class StudentActivity(models.Model):
    ...
    feedback = models.TextField(blank=True, default="")
    # [Classedge LMS] Teacher-entered feedback shown to the student alongside their score.
```

- Blank allowed — most submissions will have no feedback.
- No length cap — essays may warrant long responses.
- Additive migration; no backfill required.

### 2.2 `ScoreChangeLog` audit guarantee

- Existing model in `activity/models/score_log_models.py` is reused as-is if it already has a non-null `reason` field.
- If `reason` is currently nullable, tighten it to `null=False, blank=False` in a new migration for future rows. Existing null rows remain untouched (backward-compatible).
- Every manual override writes exactly one `ScoreChangeLog` row capturing: `student_activity` (FK), `changed_by` (FK User), `old_score`, `new_score`, `reason`, `changed_at`.

### 2.3 Existing fields reused

- `Activity.is_graded` — gate for whether the activity counts as "to be graded"
- `Activity.show_score` — unchanged; controls student visibility
- `Activity.quiz_type` — classifier for manual-grade vs auto-grade
- `StudentActivity.total_score` — score storage
- `StudentActivity.is_editable` — manual-override gate
- `Subject.assign_teacher` + `Subject.collaborators` — ownership/access

### 2.4 No new permission keys

Use the existing `@teacher_or_admin_required` decorator from `roles/decorators.py`. Subject-level ownership follows the same `_authorize_subject` pattern used in `gamification/subject_analytics.py`.

---

## 3. URL structure & views

All views live in `gradebookcomponent/views/` and are registered under namespace `gradebook` in `gradebookcomponent/urls.py`.

| URL | View | Method | Purpose |
|---|---|---|---|
| `/gradebook/` | `gradebook_home` | GET | Teacher's subject tiles with pending-grading counts |
| `/gradebook/subject/<int:subject_id>/` | `subject_gradebook` | GET | Full-page grid for one subject |
| `/gradebook/subject/<int:subject_id>/export.csv` | `subject_gradebook_csv` | GET | CSV download |
| `/gradebook/queue/` | `grading_queue` | GET | Ungraded submissions across all subjects |
| `/gradebook/grade/<int:student_activity_id>/` | `grade_submission` | GET/POST | Full-page grading view; POST saves score+feedback |
| `/gradebook/override/<int:student_activity_id>/` | `override_score` | POST | HTMX inline override from the grid |

### 3.1 View signatures

```python
# gradebookcomponent/views/gradebook_views.py

@teacher_or_admin_required
def gradebook_home(request):
    """[Classedge LMS] List subjects the teacher owns or collaborates on, with pending counts."""
    ...

@teacher_or_admin_required
def subject_gradebook(request, subject_id):
    """[Classedge LMS] Per-subject grid: students × activities, with weighted subtotals sidebar."""
    ...

@teacher_or_admin_required
def subject_gradebook_csv(request, subject_id):
    """[Classedge LMS] CSV export: raw scores + category subtotals + weighted final grade."""
    ...

@teacher_or_admin_required
def grading_queue(request):
    """[Classedge LMS] Needs-grading queue across all subjects the teacher owns."""
    ...

@teacher_or_admin_required
def grade_submission(request, student_activity_id):
    """[Classedge LMS] Full-page grading view with Save & Next progression."""
    ...

@teacher_or_admin_required
@require_POST
def override_score(request, student_activity_id):
    """[Classedge LMS] HTMX POST: override an auto-graded score; reason is required."""
    ...
```

### 3.2 Authorisation helper

```python
# gradebookcomponent/services/access.py

def authorize_subject_access(user, subject):
    """[Classedge LMS] Raise PermissionDenied unless user owns or collaborates on the subject."""
    if subject.assign_teacher_id != user.id and user not in subject.collaborators.all():
        raise PermissionDenied
```

`grade_submission` and `override_score` call `authorize_subject_access(request.user, student_activity.activity.subject)`.

### 3.3 HTMX conventions

- Override trigger: cell in the grid posts to `/gradebook/override/<id>/` with `hx-target` swapping the cell back with the re-rendered fragment (`_gradebook_cell.html`).
- The override modal (`_override_form.html`) is a fragment loaded via `hx-get` on cell click for rows where `is_editable=True`.
- Queue list is a plain full-page render — navigation to the grading view is a standard `<a>`.

---

## 4. Templates & nav integration

### 4.1 New templates

Path: `gradebookcomponent/templates/gradebookcomponent/`

| Template | Extends | Role |
|---|---|---|
| `gradebook_home.html` | `teacher_base.html` | Tile grid, one per subject |
| `subject_gradebook.html` | `teacher_base.html` | Full-page grid + right-rail subtotals |
| `grading_queue.html` | `teacher_base.html` | Ungraded submissions across subjects |
| `grade_submission.html` | `teacher_base.html` | Split layout: student answer left, form right |
| `_gradebook_cell.html` | — | HTMX fragment: one re-rendered grid cell |
| `_override_form.html` | — | HTMX fragment: override modal with required reason |

### 4.2 Nav entry

Added to sidebar inside `templates/teacher_base.html`, placed below "Dashboard" and above "Challenges":

```html
<!-- [Classedge LMS] Instructor Gradebook nav entry -->
<a href="{% url 'gradebook:home' %}"
   class="{% if request.resolver_match.namespace == 'gradebook' %}active{% endif %}">
  <span class="icon">📊</span> Gradebook
</a>
```

Icon uses the same emoji/glyph convention as SP2–SP3.

### 4.3 Dashboard shortcut

Each subject card on `gamification/templates/gamification/teacher_dashboard.html` gets:

```html
<a href="{% url 'gradebook:subject' subject.id %}" class="card-cta">Open Gradebook →</a>
```

Single-line edit per card.

### 4.4 Styling

- Reuse `teacher_base.html` tokens — cream `#faf7f2`, forest `#1b4332`, gold `#b7925a`, rose `#c08479`, ink `#2d3142`; Fraunces (display) + Inter Tight (body).
- Inline `<style>` blocks per template (matches shipped SP1–SP3).
- Sticky first column + sticky header row on the grid via CSS `position: sticky`.
- Cell color semantics:
  - Graded: forest on cream
  - Ungraded (manual-grade type): gold background
  - Not attempted: rose tint, dash glyph
  - Overridden: small star icon trailing the score
- Activities overflow horizontally when > ~50 columns; no pagination in v1.

---

## 5. Needs-grading queue query

Service: `gradebookcomponent/services/queue.py`

### 5.1 Function

```python
def get_needs_grading_for_teacher(user):
    """[Classedge LMS] Return StudentActivity queryset (oldest first) needing teacher attention."""
    ...
```

### 5.2 Inclusion criteria

A `StudentActivity` qualifies if **all** of:

1. Its `Activity.subject.assign_teacher == user` **or** `user in subject.collaborators.all()`
2. `Activity.is_graded == True`
3. The student has submitted at least one `StudentQuestion` for this activity

…**and any one of:**

- **Manual-grade types** — `Activity.quiz_type` in `{Essay, Document, Participation, Direct Score}` **AND** `StudentActivity.total_score IS NULL`
- **Flagged auto-grade** — `Activity.quiz_type` NOT in the manual set **AND** `StudentActivity.is_editable == True` **AND** `StudentActivity.total_score == 0` **AND** at least one `StudentQuestion.student_answer` is non-empty (filters false-positive legitimate zeros)

### 5.3 Query strategy

- Two querysets (manual-grade set + flagged auto-grade set) combined with `.union()`, ordered by the annotated `latest_submission_time ASC` (max `StudentQuestion.submission_time` for the `StudentActivity`, falling back to `StudentActivity.end_time` if no questions yet)
- `select_related('student', 'activity__subject', 'activity__activity_type')` on each subquery to avoid N+1 in the queue template
- Per-request caching (via `functools.lru_cache` on a helper or a request attribute) so badges and list share one query

### 5.4 UI differentiation

- Row badge: **`Needs grading`** (manual) or **`Review auto-grade`** (flagged)
- Filter chips on `/gradebook/queue/`: `All`, `Needs grading`, `Review auto-grade`, plus a subject dropdown

### 5.5 Count helper

```python
def count_needs_grading_for_subject(user, subject):
    """[Classedge LMS] Count for a single subject — feeds tile badges and dashboard shortcuts."""
    ...
```

### 5.6 Edge cases

- Student dropped / unenrolled → excluded via enrollment check on Subject
- Activity past `end_time` but not submitted → not in queue (nothing to grade)
- `is_graded=False` (practice) → never in queue
- Retake submissions → only the latest retake is shown (one row per student × activity), picked using `RetakeRecord` max or the canonical aggregate on `StudentActivity`

---

## 6. CSV export format

Service: `gradebookcomponent/services/csv_export.py`

### 6.1 Function

```python
def build_gradebook_csv(subject, term):
    """[Classedge LMS] Generator yielding CSV rows for a subject + term."""
    ...
```

### 6.2 Filename

`gradebook_<subject-slug>_<term-name>_<YYYY-MM-DD>.csv`

### 6.3 Column order

| # | Header | Source |
|---|---|---|
| 1 | `Student ID` | `student.id_number` |
| 2 | `Last Name` | `student.last_name` |
| 3 | `First Name` | `student.first_name` |
| 4..N | `<Activity Name> (<max_score>)` | one column per activity in the term, chronological by `start_time` |
| N+1..N+K | `<Category Name> Subtotal (%)` | one per `GradeBookComponents` row |
| Last | `Final Grade (%)` | weighted sum |

### 6.4 Cell value rules

- Raw: numeric `total_score`; empty string if `NULL`; `0` if submitted-zero
- Overridden: numeric with trailing `*` (e.g., `8.5*`) — Excel-scannable
- Subtotals + final grade: two decimals, never empty; `NULL` scores treated as 0 for the weighted calc (matches existing `studentTotalScore` math)

### 6.5 Shared weighted-grade helper

Extract existing weighted-grade logic from the current `studentTotalScore` view into:

```python
def compute_weighted_grade(student, subject, term):
    """[Classedge LMS] Compute weighted final grade using GradeBookComponents + ActivityTypePercentage."""
    ...
```

Both the CSV export and the on-screen grid right-rail call this single function. This extraction is the only refactor this feature requires.

### 6.6 Response

- `StreamingHttpResponse` wrapping the generator
- `Content-Type: text/csv; charset=utf-8`
- `Content-Disposition: attachment; filename="<filename>"`
- Handles large classes without memory spikes

### 6.7 Permissions

Same `@teacher_or_admin_required` plus `authorize_subject_access`.

---

## 7. Override flow & audit

### 7.1 Entry points

- **From the grid** — click a cell where `StudentActivity.is_editable == True`; HTMX loads `_override_form.html` into a modal. On submit, HTMX POSTs to `/gradebook/override/<id>/`, which re-renders the cell with `_gradebook_cell.html`.
- **From the grading view** — the "Override auto-grade" panel on `grade_submission.html` routes through the same `override_score` view for consistency.

### 7.2 Required fields on override

- `new_score` — numeric, within `[0, Activity.max_score]`
- `reason` — non-empty string; server-side validated (`HttpResponseBadRequest` if blank)

### 7.3 Write path

```python
def apply_override(student_activity, new_score, reason, changed_by):
    """[Classedge LMS] Persist override and write ScoreChangeLog atomically."""
    with transaction.atomic():
        old = student_activity.total_score
        student_activity.total_score = new_score
        student_activity.save(update_fields=["total_score"])
        ScoreChangeLog.objects.create(
            student_activity=student_activity,
            changed_by=changed_by,
            old_score=old,
            new_score=new_score,
            reason=reason,
        )
```

### 7.4 Idempotency

Overrides are not idempotent — a second override writes a second log row. This is intentional; the teacher is explicitly making a new decision.

---

## 8. Testing strategy

Tests in `gradebookcomponent/tests/`, run with `--keepdb` against `test_neondb` per codebase convention.

### 8.1 Test files

| File | Covers |
|---|---|
| `test_queue_service.py` | `get_needs_grading_for_teacher` — all inclusion criteria + every edge case in §5.6 |
| `test_gradebook_views.py` | All six views — auth, ownership denial, happy path |
| `test_grading_flow.py` | Submit essay → queue → grade → save → feedback persisted → next appears |
| `test_override.py` | Override with reason → `ScoreChangeLog` row; without reason → 400 |
| `test_csv_export.py` | Column order, subtotals, weighted total, override `*` marker, streaming response |
| `test_permissions.py` | Non-teacher denied; teacher without subject denied; collaborator allowed |
| `test_function_labels.py` | Asserts every public view in `gradebookcomponent/views/` has `[Classedge LMS]` in docstring or leading comment |

### 8.2 Helpers

Reuse `_create_test_user(username, role_name)` and `_create_subject()` from `ai_content/tests/test_models.py`.

### 8.3 Must-have assertions

- Queue excludes `is_graded=False` activities
- Queue excludes unenrolled students
- Retake: latest retake only (one row per student × activity)
- Flagged auto-grade requires non-empty `student_answer` on at least one question
- Override without reason → 400 and no `ScoreChangeLog` row
- Override creates exactly one `ScoreChangeLog` row per override
- CSV response is a `StreamingHttpResponse`
- Weighted-grade output matches the existing `studentTotalScore` view for identical inputs

### 8.4 Test count target

~25–30 tests, matching the density of shipped milestones (SP1 = 8, SP2 = 15, SP3 = 15, IDE Sub-B = 33).

---

## 9. Milestones / commits

Suggested commit ordering for implementation:

1. `StudentActivity.feedback` field + migration
2. `authorize_subject_access` helper + `compute_weighted_grade` extraction (pure refactor, tests first)
3. `get_needs_grading_for_teacher` service + tests
4. `gradebook_home` view + template + nav entry
5. `subject_gradebook` view + template + grid HTMX fragments
6. `grading_queue` view + template
7. `grade_submission` view + template + Save & Next flow
8. `override_score` view + modal fragment + `ScoreChangeLog` write
9. `subject_gradebook_csv` view + streaming export + tests
10. Dashboard shortcut on teacher-dashboard subject cards
11. `test_function_labels.py` as the final gate

---

## 10. Open questions

None at spec time. The only small unknown is whether the existing `ScoreChangeLog.reason` is currently nullable — confirmed during migration authoring (Step 1/2 of §9). Tightening it is a cheap additive change.
