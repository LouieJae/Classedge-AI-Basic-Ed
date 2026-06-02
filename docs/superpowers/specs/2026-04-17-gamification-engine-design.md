# Gamification Engine — Design Spec

## Overview

A backend gamification system that awards XP, tracks streaks, calculates
levels, and evaluates badge criteria based on student actions in the existing
ClassEdge LMS. Wired to existing models (`StudentActivity`, `Attendance`,
Django login signal) via signals — no dependency on the AI content pipeline.

This is **Sub-project A** of the gamification feature. Sub-project B (student
dashboard UI redesign) will consume this engine's data.

## Scope

**In scope:**
- New `gamification/` Django app with 4 models
- XP award service with duplicate prevention
- Django signals wired to existing models
- Streak tracking (login, submission, accuracy) with freeze support
- Level calculation: `floor(sqrt(xp / 100))`
- Badge evaluation engine with declarative criteria JSON
- Teacher-awarded badge flow
- 15 starter badge definitions (data migration)
- Migration of legacy `accounts.Badge` data
- Removal of old badge model/views/forms/templates
- Full test suite (~25-30 tests)

**Out of scope:**
- Student dashboard UI (Sub-project B)
- Leaderboard views (Sub-project B)
- Side activities / mini-games (future sub-project)
- IDE gamification (future sub-project)
- Teacher gamification / Impact Points (future sub-project)
- AI-generated badge criteria (future)

## Data Models

### `gamification/models.py`

**StudentGamification** — one per student, auto-created on first XP award.

```python
class StudentGamification(models.Model):
    student = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="gamification",
    )
    total_xp = models.PositiveIntegerField(default=0)
    current_level = models.PositiveIntegerField(default=1)
    login_streak = models.PositiveIntegerField(default=0)
    submission_streak = models.PositiveIntegerField(default=0)
    accuracy_streak = models.PositiveIntegerField(default=0)
    streak_freezes_available = models.PositiveSmallIntegerField(default=1)
    last_active_date = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["total_xp"]),
        ]
```

**XPTransaction** — append-only log of every XP award.

```python
class XPTransaction(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="xp_transactions",
    )
    amount = models.IntegerField()  # positive (can be negative for rare corrections)
    reason = models.CharField(max_length=100)
    source_type = models.CharField(max_length=50)  # 'activity', 'login', 'attendance'
    source_id = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["student", "created_at"]),
            models.Index(fields=["source_type", "source_id"]),
        ]
```

**BadgeDefinition** — replaces old `accounts.Badge`. Defines available badges.

```python
class BadgeDefinition(models.Model):
    TIER_CHOICES = [
        ("bronze", "Bronze"),
        ("silver", "Silver"),
        ("gold", "Gold"),
        ("platinum", "Platinum"),
        ("hidden", "Hidden"),
        ("seasonal", "Seasonal"),
    ]
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    tier = models.CharField(max_length=20, choices=TIER_CHOICES)
    icon = models.CharField(max_length=50)  # emoji
    target_role = models.CharField(max_length=20, default="student")
    criteria_json = models.JSONField(default=dict)  # machine-readable criteria
    is_active = models.BooleanField(default=True)
```

**StudentBadge** — tracks which students have earned which badges.

```python
class StudentBadge(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="earned_badges",
    )
    badge = models.ForeignKey(BadgeDefinition, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)
    progress_percent = models.PositiveSmallIntegerField(default=100)
    awarded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="manually_awarded_badges",
    )
    award_reason = models.CharField(max_length=300, blank=True, default="")

    class Meta:
        unique_together = [("student", "badge")]
```

## XP Award Service

### `gamification/services.py`

Central function: `award_xp(student, amount, reason, source_type, source_id=None)`

1. Check for duplicate: if `XPTransaction` exists with same `source_type` +
   `source_id` + `student`, return `None` (no double award).
2. Create `XPTransaction` row.
3. Update `StudentGamification.total_xp` via `F()` expression (atomic).
4. Refresh from DB, recalculate `current_level = floor(sqrt(total_xp / 100))`.
5. Call `evaluate_badges(student)`.
6. Return the transaction.

`StudentGamification` is auto-created via `get_or_create` if it doesn't exist.

## Signal Wiring

### `gamification/signals.py`

Connected in `GamificationConfig.ready()`.

| Signal | Source | Condition | XP | reason | source_type | source_id |
|--------|--------|-----------|-----|--------|-------------|-----------|
| `post_save` | `StudentActivity` | `created=True` | +50 | "Assignment submitted" | `activity` | `student_activity.pk` |
| `post_save` | `StudentActivity` | `created=True` and submitted >24h before `term.end_date` | +75 (instead of +50) | "Early submission" | `activity` | `student_activity.pk` |
| `post_save` | `StudentActivity` | `total_score / activity.max_score >= 0.9` | +30 | "Score >=90%" | `activity_score_90` | `student_activity.pk` |
| `post_save` | `StudentActivity` | `total_score / activity.max_score >= 0.75` (and < 0.9) | +15 | "Score >=75%" | `activity_score_75` | `student_activity.pk` |
| `user_logged_in` | Django auth | Once per calendar day (skip if `last_active_date == today`) | +5 | "Daily login" | `login` | `date.today().toordinal()` |
| `post_save` | `Attendance` | All 5 weekdays present in the same week for the subject | +50 | "Perfect attendance week" | `attendance_week` | Week number hash |

**Duplicate prevention:** Each signal uses a unique `source_type` + `source_id`
combination. The `award_xp` function checks for existing transactions before
creating new ones. For login, dedup is by checking `last_active_date == today`.

**Signal guards:** All signals check `created=True` where applicable to avoid
firing on updates. Score-based signals fire on both create and update (a score
might be entered after initial submission).

## Streak Engine

### `gamification/streaks.py`

Three functions, each operating on `StudentGamification` with `select_for_update()`:

**`update_login_streak(student)`** — called from login signal handler.
- If `last_active_date` is yesterday: `login_streak += 1`
- If `last_active_date` is today: no-op
- If `last_active_date` is older:
  - If `streak_freezes_available > 0` and gap is exactly 1 day: decrement freeze, keep streak
  - Else: reset `login_streak = 1`
- Set `last_active_date = today`

**`update_submission_streak(student, is_on_time)`** — called from StudentActivity signal.
- If `is_on_time`: `submission_streak += 1`
- Else: `submission_streak = 0`

**`update_accuracy_streak(student, score_pct)`** — called from StudentActivity signal.
- If `score_pct >= 80`: `accuracy_streak += 1`
- Else: `accuracy_streak = 0`

After each streak update, calls `evaluate_badges(student)`.

**Monthly freeze reset:** Management command `reset_streak_freezes` sets
`streak_freezes_available = 1` for all students. Run via cron on the 1st of
each month (or Celery Beat if available).

## Badge Evaluation Engine

### `gamification/badges.py`

**`evaluate_badges(student)`** — checks all unevaluated badges:

1. Load active `BadgeDefinition` rows where `target_role='student'`
2. Exclude badges the student already has (`StudentBadge` lookup)
3. For each remaining badge, call the evaluator for its `criteria_json["type"]`
4. If criteria met, create `StudentBadge` with `progress_percent=100`

**Evaluator registry** — dict mapping `type` string to a function:

```python
EVALUATORS = {
    "xp_total": _eval_xp_total,         # {"type": "xp_total", "threshold": 1000}
    "streak": _eval_streak,              # {"type": "streak", "streak": "login", "threshold": 7}
    "badges_earned": _eval_badges_count, # {"type": "badges_earned", "threshold": 10}
    "activity_score": _eval_activity_score,  # {"type": "activity_score", "min_pct": 90, "count": 5}
    "level": _eval_level,                # {"type": "level", "threshold": 5}
}
```

Each evaluator receives `(student, criteria_json)` and returns `bool`.

**Teacher-awarded badges** bypass evaluation — a dedicated view creates
`StudentBadge` directly with `awarded_by` set. No criteria needed.

### Starter Badge Definitions (data migration)

| Code | Name | Tier | Criteria | Icon |
|------|------|------|----------|------|
| `first_login` | First Login | bronze | `{"type": "xp_total", "threshold": 5}` | :wave: |
| `week_warrior` | Week Warrior | silver | `{"type": "streak", "streak": "login", "threshold": 7}` | :fire: |
| `month_master` | Month Master | gold | `{"type": "streak", "streak": "login", "threshold": 30}` | :star2: |
| `sharpshooter` | Sharpshooter | silver | `{"type": "activity_score", "min_pct": 90, "count": 5}` | :dart: |
| `perfect_score` | Perfect Score | gold | `{"type": "activity_score", "min_pct": 100, "count": 1}` | :100: |
| `bookworm` | Bookworm | silver | `{"type": "xp_total", "threshold": 2500}` | :books: |
| `scholar` | Scholar | platinum | `{"type": "xp_total", "threshold": 10000}` | :mortar_board: |
| `on_fire` | On Fire | silver | `{"type": "streak", "streak": "submission", "threshold": 10}` | :zap: |
| `consistent` | Consistent | gold | `{"type": "streak", "streak": "accuracy", "threshold": 20}` | :bullseye: |
| `level_5` | Rising Star | bronze | `{"type": "level", "threshold": 5}` | :seedling: |
| `level_10` | Veteran | silver | `{"type": "level", "threshold": 10}` | :shield: |
| `level_20` | Legend | gold | `{"type": "level", "threshold": 20}` | :crown: |
| `collector` | Collector | silver | `{"type": "badges_earned", "threshold": 10}` | :gem: |
| `honor_roll` | Honor Roll | platinum | `{}` (teacher-awarded only) | :trophy: |
| `early_bird` | Early Bird | bronze | `{"type": "xp_total", "threshold": 100}` | :sunrise: |

## Legacy Badge Migration

**Data migration (RunPython in a Django migration):**

1. For each `accounts.Badge` row:
   - Create `BadgeDefinition(code=f"legacy_{badge.pk}", name=badge.name, description=badge.description or "", tier="bronze", icon="🏅", criteria_json={}, is_active=True)`
2. For each profile in `badge.profiles.all()`:
   - Look up the `CustomUser` for the profile
   - Create `StudentBadge(student=user, badge=definition, awarded_by=None, award_reason="Migrated from legacy badge system")`
3. Migration depends on both the gamification model migration and the accounts app

**Post-migration cleanup (separate commit):**
- Remove `accounts/models/badge_models.py`
- Remove `accounts/views/badge_views.py`
- Remove `accounts/forms/badge_forms.py`
- Remove `accounts/templates/accounts/badge/*.html`
- Remove badge URL patterns from `accounts/urls.py`
- Remove `Badge` from `accounts/models/__init__.py`
- Create accounts migration that deletes the old `Badge` model + M2M table

## Teacher Badge Award

**`gamification/views.py`** — `award_badge_view`:
- Teacher selects student + badge definition + writes a reason
- Creates `StudentBadge` with `awarded_by=request.user`
- Protected by `@login_required` + role check (teacher/admin only)
- Simple form: dropdown of students (filtered to teacher's subjects), dropdown of badge definitions, text field for reason

**Visibility rules:**
- Students see all their badges identically (no "awarded by" label)
- Teachers/admins see "Awarded by {name}" label on teacher-awarded badges

## Configuration

In `lms/settings.py`:

```python
# Gamification
GAMIFICATION_XP_RATES = {
    "submission": 50,
    "early_submission": 75,
    "score_90": 30,
    "score_75": 15,
    "daily_login": 5,
    "perfect_attendance_week": 50,
}
GAMIFICATION_STREAK_FREEZE_MONTHLY = 1
```

## Testing

### Test files

- `gamification/tests/test_models.py` — model creation, constraints, unique_together
- `gamification/tests/test_services.py` — award_xp atomicity, level calc, duplicate prevention
- `gamification/tests/test_signals.py` — XP on StudentActivity save, login signal, attendance
- `gamification/tests/test_streaks.py` — increment, reset, freeze, month rollover
- `gamification/tests/test_badges.py` — each evaluator type, teacher award, starter seed
- `gamification/tests/test_migration.py` — legacy data migrated correctly

### Key test cases (~25-30)

**Services:**
- award_xp creates transaction + updates total_xp atomically
- Duplicate source_type+source_id returns None
- Level formula: 0 XP = level 1, 10000 XP = level 10, 40000 XP = level 20

**Signals:**
- StudentActivity create fires submission XP
- StudentActivity create does not double-fire on update
- Score >= 90% awards +30, >= 75% awards +15, both don't stack
- Login signal awards +5 once per day
- Perfect attendance week awards +50

**Streaks:**
- Consecutive login days increment login_streak
- Gap > 1 day resets login_streak
- Freeze preserves streak on 1-day gap, decrements freeze count
- On-time submission increments, late resets
- Score >= 80% increments accuracy, below resets

**Badges:**
- xp_total evaluator returns True when threshold met
- streak evaluator checks correct streak field
- activity_score evaluator counts qualifying scores
- level evaluator checks current_level
- Teacher award creates StudentBadge with awarded_by set
- Starter seed migration creates 15 badge definitions

**Migration:**
- Legacy badges create BadgeDefinition + StudentBadge rows
- Profile M2M data maps to correct students
