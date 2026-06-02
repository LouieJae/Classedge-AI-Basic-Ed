# IDE Sub-B: Coding Badges, Badge Management & Teacher Auto-Checker

**Date:** 2026-04-18
**Status:** Approved
**Depends on:** IDE Sub-A (shipped), Gamification Engine (shipped), Side Activities (shipped)

---

## Overview

Add 9 coding-specific badges spanning IDE exercises and code katas, a per-student CodingStats model for efficient evaluation, badge progress tracking for all badges, a teacher badge management CRUD, and a teacher auto-checker dashboard for coding exercise grading.

---

## 1. CodingStats Model

**File:** `gamification/models.py`

New `OneToOneField` on User, tracking aggregated coding metrics:

```python
class CodingStats(models.Model):
    student = models.OneToOneField(User, on_delete=models.CASCADE, related_name="coding_stats")
    total_submissions = models.PositiveIntegerField(default=0)       # IDE exercise submissions (completed)
    perfect_submissions = models.PositiveIntegerField(default=0)     # IDE score == 1.0
    total_katas = models.PositiveIntegerField(default=0)             # code_kata completions
    perfect_katas = models.PositiveIntegerField(default=0)           # code_kata score == 1.0
    languages_used = models.JSONField(default=list)                  # e.g. ["python", "javascript"]
    fast_perfects = models.PositiveIntegerField(default=0)           # IDE perfect + execution_time_ms < 500
    current_streak = models.PositiveIntegerField(default=0)          # consecutive perfect (IDE + kata)
    best_streak = models.PositiveIntegerField(default=0)             # all-time high-water mark
    updated_at = models.DateTimeField(auto_now=True)
```

### Update Service

**File:** `gamification/coding_stats_service.py`

Two functions, called after grading completes:

#### `update_coding_stats(student, submission)`

Called from `ide/tasks.py` `run_code_submission` after grading:

1. Get or create `CodingStats` for student
2. Increment `total_submissions` (F expression)
3. If `submission.score == 1.0`:
   - Increment `perfect_submissions`
   - If `submission.execution_time_ms < 500`: increment `fast_perfects`
   - Increment `current_streak`
   - Update `best_streak = max(best_streak, current_streak)`
4. If `submission.score < 1.0`:
   - Reset `current_streak = 0`
5. If `submission.language` not in `languages_used`: append it
6. Save

#### `update_coding_stats_kata(student, attempt)`

Called from side activity submit view when `sub_type == "code_kata"`:

1. Get or create `CodingStats` for student
2. Increment `total_katas`
3. If `attempt.score == 1.0`:
   - Increment `perfect_katas`
   - Increment `current_streak`
   - Update `best_streak = max(best_streak, current_streak)`
4. If `attempt.score < 1.0`:
   - Reset `current_streak = 0`
5. Save

### Integration Points

- `ide/tasks.py` line ~122: after `award_xp()`, call `update_coding_stats(student, submission)`
- `gamification/side_activity_views.py` submit handler: after XP award for code_kata, call `update_coding_stats_kata(student, attempt)`

---

## 2. Nine Coding Badges

### Badge Definitions

Seeded via migration `0007_seed_coding_badges.py`:

| # | Code | Name | Tier | Icon | Criteria Type | Criteria |
|---|------|------|------|------|---------------|----------|
| 1 | `first_code` | First Compile | bronze | `🖥️` | `coding_first` | `{"type": "coding_first"}` |
| 2 | `bug_squasher` | Bug Squasher | bronze | `🐛` | `coding_perfect_count` | `{"type": "coding_perfect_count", "threshold": 5}` |
| 3 | `kata_warrior` | Kata Warrior | silver | `🥋` | `coding_kata_count` | `{"type": "coding_kata_count", "threshold": 25}` |
| 4 | `polyglot` | Polyglot | silver | `🌐` | `coding_polyglot` | `{"type": "coding_polyglot"}` |
| 5 | `speed_coder` | Speed Coder | silver | `⚡` | `coding_fast_perfect` | `{"type": "coding_fast_perfect", "threshold": 3}` |
| 6 | `code_streak` | Code Streak | gold | `🔗` | `coding_streak` | `{"type": "coding_streak", "threshold": 10}` |
| 7 | `algorithm_ace` | Algorithm Ace | gold | `🧮` | `coding_perfect_count` | `{"type": "coding_perfect_count", "threshold": 20}` |
| 8 | `code_centurion` | Code Centurion | gold | `💻` | `coding_total` | `{"type": "coding_total", "threshold": 100}` |
| 9 | `code_legend` | Code Legend | platinum | `🏅` | `coding_legend` | `{"type": "coding_legend", "perfect_threshold": 50, "kata_threshold": 100}` |

### Evaluator Functions

**File:** `gamification/badges.py`

8 new evaluator functions (one reused for two badges). All read from `CodingStats`:

```python
def _eval_coding_first(student, gam, criteria):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return False
    return (stats.total_submissions + stats.total_katas) >= 1

def _eval_coding_perfect_count(student, gam, criteria):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return False
    return stats.perfect_submissions >= criteria["threshold"]

def _eval_coding_kata_count(student, gam, criteria):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return False
    return stats.total_katas >= criteria["threshold"]

def _eval_coding_polyglot(student, gam, criteria):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return False
    return len(stats.languages_used) >= 2

def _eval_coding_fast_perfect(student, gam, criteria):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return False
    return stats.fast_perfects >= criteria["threshold"]

def _eval_coding_streak(student, gam, criteria):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return False
    return stats.best_streak >= criteria["threshold"]

def _eval_coding_total(student, gam, criteria):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return False
    return (stats.total_submissions + stats.total_katas) >= criteria["threshold"]

def _eval_coding_legend(student, gam, criteria):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return False
    return (stats.perfect_submissions >= criteria["perfect_threshold"]
            and stats.total_katas >= criteria["kata_threshold"])
```

Register in `EVALUATORS` dict:

```python
EVALUATORS = {
    # ... existing evaluators ...
    "coding_first": _eval_coding_first,
    "coding_perfect_count": _eval_coding_perfect_count,
    "coding_kata_count": _eval_coding_kata_count,
    "coding_polyglot": _eval_coding_polyglot,
    "coding_fast_perfect": _eval_coding_fast_perfect,
    "coding_streak": _eval_coding_streak,
    "coding_total": _eval_coding_total,
    "coding_legend": _eval_coding_legend,
}
```

---

## 3. Badge Progress Tracking

### Progress Computer Functions

**File:** `gamification/badges.py`

New function `compute_badge_progress(student, badge)` returns 0-100 integer:

```python
def compute_badge_progress(student, badge):
    criteria = badge.criteria_json
    if not criteria or "type" not in criteria:
        return 0
    computer = PROGRESS_COMPUTERS.get(criteria["type"])
    if not computer:
        return 0
    gam = StudentGamification.objects.filter(student=student).first()
    if not gam:
        return 0
    return computer(student, gam, criteria)
```

`PROGRESS_COMPUTERS` dict — one lambda/function per criteria type:

```python
PROGRESS_COMPUTERS = {
    # General badges
    "xp_total": lambda s, g, c: min(100, int(g.total_xp / c["threshold"] * 100)),
    "streak": lambda s, g, c: min(100, int(getattr(g, f'{c["streak"]}_streak', 0) / c["threshold"] * 100)),
    "level": lambda s, g, c: min(100, int(g.current_level / c["threshold"] * 100)),
    "badges_earned": lambda s, g, c: _progress_badges_earned(s, c),
    "activity_score": lambda s, g, c: _progress_activity_score(s, c),

    # Side activity badges
    "side_activity_count": lambda s, g, c: _progress_sa_count(s, c),
    "side_activity_count_type": lambda s, g, c: _progress_sa_count_type(s, c),
    "side_activity_speed": lambda s, g, c: _progress_sa_speed(s, c),
    "side_activity_typing_wpm": lambda s, g, c: _progress_sa_typing(s, c),
    "side_activity_all_in_subject": lambda s, g, c: _progress_sa_all_subject(s, c),

    # Coding badges
    "coding_first": lambda s, g, c: _progress_coding_first(s),
    "coding_perfect_count": lambda s, g, c: _progress_coding_stat(s, "perfect_submissions", c["threshold"]),
    "coding_kata_count": lambda s, g, c: _progress_coding_stat(s, "total_katas", c["threshold"]),
    "coding_polyglot": lambda s, g, c: _progress_coding_polyglot(s),
    "coding_fast_perfect": lambda s, g, c: _progress_coding_stat(s, "fast_perfects", c["threshold"]),
    "coding_streak": lambda s, g, c: _progress_coding_stat(s, "best_streak", c["threshold"]),
    "coding_total": lambda s, g, c: _progress_coding_total(s, c["threshold"]),
    "coding_legend": lambda s, g, c: _progress_coding_legend(s, c),
}
```

Helper examples:

```python
def _progress_coding_stat(student, field, threshold):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return 0
    return min(100, int(getattr(stats, field, 0) / threshold * 100))

def _progress_coding_legend(student, criteria):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return 0
    p1 = min(50, int(stats.perfect_submissions / criteria["perfect_threshold"] * 50))
    p2 = min(50, int(stats.total_katas / criteria["kata_threshold"] * 50))
    return p1 + p2
```

### UI Integration

**Badge collection page** (`gamification/templates/gamification/badge_collection.html`):
- Earned badges: show as-is (gold border, earned date)
- Unearned badges: show greyed out with progress bar underneath, e.g. "3/5 perfect submissions"
- Pass progress data via view context: list of `{"badge": badge, "earned": bool, "progress": int}`

**Student dashboard badge widget** (`gamification/templates/gamification/includes/badge_widget.html`):
- Add "Almost There" section showing top 3 unearned badges by highest progress (> 0, < 100)
- Clickable → links to badge collection page

---

## 4. Badge Management CRUD

### Permission

- Permission key: `manage_badges`
- Added to `PERMISSION_CHOICES`, `DEFAULT_ROLE_PERMISSIONS` (Teacher, Admin)
- Frontend: `ProtectedRoute` guard
- Backend: role check in views

### Views

**File:** `gamification/views.py` (add to existing)

#### `badge_list(request)` — GET

- Query all `BadgeDefinition` objects, annotate with `earned_count` (count of `StudentBadge`)
- Group by category: General (xp_total, streak, level, badges_earned, activity_score), Side Activity (side_activity_*), Coding (coding_*)
- Render table: name, icon, tier, description, active toggle, earned count, actions (edit, award if manual)

#### `badge_edit(request, badge_id)` — GET/POST

- Form fields: `name`, `description`, `icon`, `tier`, `is_active`
- `criteria_json` displayed as read-only formatted JSON
- `code` displayed as read-only (immutable identifier)
- On save: update fields, redirect to badge_list with success message

#### `badge_manual_award(request, badge_id)` — GET/POST

- Only for badges with empty `criteria_json` (manual-award badges like `honor_roll`)
- Form: student select (searchable dropdown), award reason text
- On submit: create `StudentBadge(student=selected, badge=badge, awarded_by=request.user, award_reason=reason)`
- Prevent duplicate awards (unique_together already enforced)

### URLs

```python
path("gamification/badges/manage/", views.badge_list, name="badge_management"),
path("gamification/badges/<int:badge_id>/edit/", views.badge_edit, name="badge_edit"),
path("gamification/badges/<int:badge_id>/award/", views.badge_manual_award, name="badge_manual_award"),
```

### Templates

- `gamification/badge_management.html` — extends `base.html`, table with category tabs, inline active toggle (AJAX PATCH or form POST)
- `gamification/badge_edit.html` — extends `base.html`, standard form layout
- `gamification/badge_award.html` — extends `base.html`, student search + reason form

---

## 5. Teacher Auto-Checker Dashboard

### Views

**File:** `ide/views.py` (add to existing)

#### `coding_overview(request)` — GET

Bulk overview of all coding exercises the teacher has access to:

- Query all `CodingExercise` objects (filtered by teacher's subjects/classes)
- For each exercise, annotate:
  - `total_students` — students in the class
  - `attempted_count` — distinct students with at least one `CodeSubmission`
  - `avg_score` — average of best submission scores
  - `completion_rate` — `attempted_count / total_students * 100`
  - `perfect_count` — students with score == 1.0
- Render table sorted by activity date (newest first)
- Each row links to exercise-level detail

#### `coding_exercise_results(request, exercise_id)` — GET

All submissions for a specific exercise:

- Query all `CodeSubmission` objects for this exercise, grouped by student (show best + most recent)
- For each student row:
  - Student name
  - Best score (highlighted: green >=90%, yellow >=50%, red <50%)
  - Number of attempts
  - Pass/fail per test case (checkmark/cross icons)
  - Execution time (best submission)
  - Last submitted at
  - Score override button
- Students who haven't attempted shown at bottom (greyed out, "Not Attempted")

#### `coding_score_override(request, submission_id)` — POST

Teacher manually adjusts a submission's score:

- Form fields: `new_score` (0.0-1.0 float), `override_note` (text, required)
- Updates `CodeSubmission.score` to new value
- Updates `CodeSubmission.result_json` — adds `"override": {"by": teacher_id, "original_score": old_score, "new_score": new_score, "note": note, "at": timestamp}`
- Recalculates `StudentActivity.total_score` based on new score
- Does NOT re-trigger XP (original XP award stands; teacher can manually award XP separately if needed)

### Permission

- Permission key: `view_coding_results` (covers overview + results + override)
- Added to `PERMISSION_CHOICES`, `DEFAULT_ROLE_PERMISSIONS` (Teacher, Admin)

### URLs

```python
path("ide/overview/", views.coding_overview, name="coding_overview"),
path("ide/exercise/<int:exercise_id>/results/", views.coding_exercise_results, name="coding_exercise_results"),
path("ide/submission/<int:submission_id>/override/", views.coding_score_override, name="coding_score_override"),
```

### Templates

- `ide/coding_overview.html` — extends `base.html`, table with completion sparkbars, links to detail
- `ide/coding_exercise_results.html` — extends `base.html`, student submission table, per-test pass/fail grid, score override modal
- Score override: inline modal with score input (0-100% displayed, stored as 0-1.0), note textarea, confirm button

---

## 6. Tests

### Evaluator Tests (~9) — `gamification/tests/test_badges.py`

One test per evaluator type + edge cases:

1. `test_coding_first_badge` — 1 submission triggers badge
2. `test_coding_perfect_count_below_threshold` — 4 perfects, needs 5, not awarded
3. `test_coding_perfect_count_at_threshold` — 5 perfects → bug_squasher awarded
4. `test_coding_kata_count` — 25 katas → kata_warrior
5. `test_coding_polyglot` — both languages in languages_used → polyglot
6. `test_coding_fast_perfect` — 3 fast perfects → speed_coder
7. `test_coding_streak` — best_streak=10 → code_streak
8. `test_coding_total` — 100 combined → code_centurion
9. `test_coding_legend_compound` — meets both thresholds → code_legend; fails if only one met

### CodingStats Service Tests (~5) — `gamification/tests/test_coding_stats.py`

1. `test_update_stats_perfect_submission` — increments total_submissions, perfect_submissions, current_streak
2. `test_update_stats_failed_resets_streak` — non-perfect resets current_streak, preserves best_streak
3. `test_update_stats_new_language` — appends to languages_used, no duplicates
4. `test_update_stats_kata_completion` — increments total_katas, streak
5. `test_update_stats_fast_perfect` — score=1.0 + execution_time_ms<500 increments fast_perfects

### Badge Management Tests (~4) — `gamification/tests/test_badge_management.py`

1. `test_teacher_sees_badge_list` — 200 response, all badges in context
2. `test_student_cannot_access_badge_management` — 302 redirect
3. `test_toggle_badge_active` — POST toggles is_active field
4. `test_manual_award_creates_student_badge` — POST with student_id → StudentBadge created with awarded_by

### Progress Computer Tests (~2) — `gamification/tests/test_badges.py`

1. `test_progress_partial` — coding_perfect_count with 3/5 → returns 60
2. `test_progress_caps_at_100` — over threshold → returns 100

### Auto-Checker Tests (~3) — `ide/tests/test_auto_checker.py`

1. `test_coding_overview_shows_exercises` — teacher sees all exercises with stats
2. `test_coding_results_shows_submissions` — per-exercise view lists student submissions
3. `test_score_override_updates_submission` — POST changes score, adds override to result_json

**Total: ~23 tests**

---

## 7. Migration Plan

1. `0007_codingstats.py` — create CodingStats model
2. `0008_seed_coding_badges.py` — seed 9 coding badge definitions
3. `0009_backfill_coding_stats.py` — data migration to backfill CodingStats for existing students with CodeSubmission or code_kata attempts (one-time)

---

## 8. File Changes Summary

### New Files
- `gamification/coding_stats_service.py` — update_coding_stats, update_coding_stats_kata
- `gamification/migrations/0007_codingstats.py`
- `gamification/migrations/0008_seed_coding_badges.py`
- `gamification/migrations/0009_backfill_coding_stats.py`
- `gamification/templates/gamification/badge_management.html`
- `gamification/templates/gamification/badge_edit.html`
- `gamification/templates/gamification/badge_award.html`
- `ide/templates/ide/coding_overview.html`
- `ide/templates/ide/coding_exercise_results.html`
- `gamification/tests/test_coding_stats.py`
- `gamification/tests/test_badge_management.py`
- `ide/tests/test_auto_checker.py`

### Modified Files
- `gamification/models.py` — add CodingStats model
- `gamification/badges.py` — add 8 evaluators, PROGRESS_COMPUTERS dict, compute_badge_progress()
- `gamification/views.py` — add badge_list, badge_edit, badge_manual_award views
- `gamification/urls.py` — add 3 badge management URL patterns
- `gamification/templates/gamification/badge_collection.html` — add progress bars for unearned badges
- `gamification/templates/gamification/includes/badge_widget.html` — add "Almost There" section
- `ide/tasks.py` — call update_coding_stats after grading
- `ide/views.py` — add coding_overview, coding_exercise_results, coding_score_override views
- `ide/urls.py` — add 3 auto-checker URL patterns
- `gamification/side_activity_views.py` — call update_coding_stats_kata for code_kata submissions
- `gamification/tests/test_badges.py` — add 9 evaluator tests + 2 progress tests
- Permission files: PERMISSION_CHOICES, DEFAULT_ROLE_PERMISSIONS, ProtectedRoute configs
