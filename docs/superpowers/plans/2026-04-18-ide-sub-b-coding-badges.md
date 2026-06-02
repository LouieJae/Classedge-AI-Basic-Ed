# IDE Sub-B: Coding Badges, Badge Management & Teacher Auto-Checker — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 9 coding-specific badges with a CodingStats aggregate model, badge progress tracking for all badges, teacher badge management CRUD, and a teacher auto-checker dashboard for coding exercises.

**Architecture:** CodingStats (OneToOne on User) is updated by service functions called from `ide/tasks.py` and `gamification/side_activity_views.py`. Eight new evaluator functions in `badges.py` read from CodingStats. Progress computers are computed on read (not stored). Badge management and auto-checker are teacher-only views using the `@teacher_or_admin_required` decorator from `roles/decorators.py`.

**Tech Stack:** Django 5.0.7, PostgreSQL, Celery, DRF. Tests use `django.test.TestCase` with `--keepdb`. Test DB is `test_neondb`.

**Test command:** `~/classedge/env/bin/python manage.py test <app.tests.module> --keepdb -v2`

---

## File Structure

### New Files
| File | Responsibility |
|------|---------------|
| `gamification/coding_stats_service.py` | `update_coding_stats()`, `update_coding_stats_kata()` |
| `gamification/migrations/0006_codingstats.py` | CodingStats model migration (auto-generated) |
| `gamification/migrations/0007_seed_coding_badges.py` | Seed 9 coding badge definitions |
| `gamification/tests/test_coding_stats.py` | CodingStats service tests |
| `gamification/tests/test_badge_management.py` | Badge management view tests |
| `gamification/templates/gamification/badge_management.html` | Teacher badge list with active toggle |
| `gamification/templates/gamification/badge_edit.html` | Teacher badge edit form |
| `gamification/templates/gamification/badge_award.html` | Manual badge award form |
| `ide/templates/ide/coding_overview.html` | Bulk coding exercise overview |
| `ide/templates/ide/coding_exercise_results.html` | Per-exercise student results + override |
| `ide/tests/test_auto_checker.py` | Auto-checker view tests |

### Modified Files
| File | Changes |
|------|---------|
| `gamification/models.py:99-101` | Add CodingStats model after StudentBadge |
| `gamification/badges.py:144-159` | Add 8 evaluators + progress computers + `compute_badge_progress()` |
| `gamification/views.py:163-188` | Update `badge_collection` to include progress; add badge management views |
| `gamification/urls.py:1-18` | Add badge management + auto-checker URL patterns |
| `gamification/side_activity_views.py:114-159` | Call `update_coding_stats_kata` on code_kata submit |
| `ide/tasks.py:120-126` | Call `update_coding_stats` after grading |
| `ide/views.py:136` | Add auto-checker views |
| `ide/urls.py:1-11` | Add auto-checker URL patterns |
| `gamification/tests/test_badges.py:119-128` | Update seed count from 25 to 34; add evaluator + progress tests |
| `gamification/templates/gamification/badge_collection.html:14-28` | Add progress bars for unearned badges |
| `gamification/templates/gamification/student_dashboard.html:85-113` | Add "Almost There" section |

---

### Task 1: CodingStats Model

**Files:**
- Modify: `gamification/models.py:99-101`
- Create: `gamification/migrations/0006_codingstats.py` (auto-generated)
- Test: `gamification/tests/test_coding_stats.py`

- [ ] **Step 1: Write the failing test for CodingStats creation**

In `gamification/tests/test_coding_stats.py`:

```python
from django.test import TestCase
from ai_content.tests.test_models import _create_test_user
from gamification.models import CodingStats


class CodingStatsModelTests(TestCase):
    def test_create_coding_stats(self):
        student = _create_test_user(username="cs_student", role_name="student")
        stats = CodingStats.objects.create(student=student)
        self.assertEqual(stats.total_submissions, 0)
        self.assertEqual(stats.perfect_submissions, 0)
        self.assertEqual(stats.total_katas, 0)
        self.assertEqual(stats.perfect_katas, 0)
        self.assertEqual(stats.languages_used, [])
        self.assertEqual(stats.fast_perfects, 0)
        self.assertEqual(stats.current_streak, 0)
        self.assertEqual(stats.best_streak, 0)

    def test_one_per_student(self):
        student = _create_test_user(username="cs_unique", role_name="student")
        CodingStats.objects.create(student=student)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            CodingStats.objects.create(student=student)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `~/classedge/env/bin/python manage.py test gamification.tests.test_coding_stats --keepdb -v2`
Expected: `ImportError: cannot import name 'CodingStats'`

- [ ] **Step 3: Add CodingStats model**

In `gamification/models.py`, add before the final import line (line 101):

```python
class CodingStats(models.Model):
    student = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="coding_stats",
    )
    total_submissions = models.PositiveIntegerField(default=0)
    perfect_submissions = models.PositiveIntegerField(default=0)
    total_katas = models.PositiveIntegerField(default=0)
    perfect_katas = models.PositiveIntegerField(default=0)
    languages_used = models.JSONField(default=list)
    fast_perfects = models.PositiveIntegerField(default=0)
    current_streak = models.PositiveIntegerField(default=0)
    best_streak = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"CodingStats({self.student}) subs={self.total_submissions} katas={self.total_katas}"
```

- [ ] **Step 4: Generate and run migration**

```bash
cd ~/classedge && ./env/bin/python manage.py makemigrations gamification --name codingstats
./env/bin/python manage.py migrate --run-syncdb
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `~/classedge/env/bin/python manage.py test gamification.tests.test_coding_stats --keepdb -v2`
Expected: 2 tests PASS

- [ ] **Step 6: Commit**

```bash
git add gamification/models.py gamification/migrations/0006_codingstats.py gamification/tests/test_coding_stats.py
git commit -m "feat(gamification): add CodingStats model for per-student coding aggregates"
```

---

### Task 2: CodingStats Update Service

**Files:**
- Create: `gamification/coding_stats_service.py`
- Test: `gamification/tests/test_coding_stats.py`

- [ ] **Step 1: Write failing tests for update_coding_stats**

Append to `gamification/tests/test_coding_stats.py`:

```python
from unittest.mock import patch
from datetime import date

from django.test import override_settings

from activity.models.activity_model import Activity, ActivityType
from course.models.semester_model import Semester
from course.models.term_model import Term
from ide.models import CodingExercise, CodeSubmission
from gamification.coding_stats_service import update_coding_stats, update_coding_stats_kata
from gamification.side_activity_models import SideActivity, SideActivityAttempt
from django.utils import timezone

_GAM_SETTINGS = {
    "GAMIFICATION_XP_RATES": {
        "submission": 50, "early_submission": 75, "score_90": 30,
        "score_75": 15, "daily_login": 5, "perfect_attendance_week": 50,
    },
    "GAMIFICATION_STREAK_FREEZE_MONTHLY": 1,
}


@override_settings(**_GAM_SETTINGS)
class UpdateCodingStatsTests(TestCase):
    def setUp(self):
        self.student = _create_test_user(username="ucs_student", role_name="student")
        self.subject = _create_subject()
        self.semester = Semester.objects.create(
            semester_name="Sem", start_date=date(2026, 1, 1), end_date=date(2027, 12, 31),
        )
        self.term = Term.objects.create(
            term_name="Prelim", semester=self.semester,
            start_date=date(2026, 8, 15), end_date=date(2026, 10, 15),
        )
        self.activity_type, _ = ActivityType.objects.get_or_create(name="Coding")
        self.activity = Activity.objects.create(
            activity_name="Test Ex", activity_type=self.activity_type,
            subject=self.subject, term=self.term, max_score=100,
        )
        self.exercise = CodingExercise.objects.create(
            activity=self.activity, language="python",
            starter_code="", solution_code="",
            test_cases=[{"input": "1", "expected_output": "1"}],
        )

    def _make_submission(self, score=1.0, execution_time_ms=100, language="python"):
        sub = CodeSubmission.objects.create(
            student=self.student, exercise=self.exercise,
            code="print(1)", language=language,
            status="completed", score=score,
            execution_time_ms=execution_time_ms,
        )
        return sub

    def test_perfect_submission_increments_stats(self):
        sub = self._make_submission(score=1.0, execution_time_ms=100)
        update_coding_stats(self.student, sub)
        stats = CodingStats.objects.get(student=self.student)
        self.assertEqual(stats.total_submissions, 1)
        self.assertEqual(stats.perfect_submissions, 1)
        self.assertEqual(stats.current_streak, 1)
        self.assertEqual(stats.best_streak, 1)

    def test_failed_submission_resets_streak(self):
        sub1 = self._make_submission(score=1.0)
        update_coding_stats(self.student, sub1)
        sub2 = self._make_submission(score=0.5)
        update_coding_stats(self.student, sub2)
        stats = CodingStats.objects.get(student=self.student)
        self.assertEqual(stats.total_submissions, 2)
        self.assertEqual(stats.perfect_submissions, 1)
        self.assertEqual(stats.current_streak, 0)
        self.assertEqual(stats.best_streak, 1)

    def test_new_language_appended(self):
        sub1 = self._make_submission(language="python")
        update_coding_stats(self.student, sub1)
        # Create a JS exercise
        act2 = Activity.objects.create(
            activity_name="JS Ex", activity_type=self.activity_type,
            subject=self.subject, term=self.term, max_score=100,
        )
        ex2 = CodingExercise.objects.create(
            activity=act2, language="javascript",
            starter_code="", solution_code="",
            test_cases=[{"input": "", "expected_output": "hello"}],
        )
        sub2 = CodeSubmission.objects.create(
            student=self.student, exercise=ex2,
            code="console.log('hello')", language="javascript",
            status="completed", score=1.0, execution_time_ms=50,
        )
        update_coding_stats(self.student, sub2)
        stats = CodingStats.objects.get(student=self.student)
        self.assertEqual(sorted(stats.languages_used), ["javascript", "python"])

    def test_fast_perfect_detection(self):
        sub = self._make_submission(score=1.0, execution_time_ms=300)
        update_coding_stats(self.student, sub)
        stats = CodingStats.objects.get(student=self.student)
        self.assertEqual(stats.fast_perfects, 1)

    def test_slow_perfect_not_fast(self):
        sub = self._make_submission(score=1.0, execution_time_ms=600)
        update_coding_stats(self.student, sub)
        stats = CodingStats.objects.get(student=self.student)
        self.assertEqual(stats.fast_perfects, 0)
```

- [ ] **Step 2: Write failing test for update_coding_stats_kata**

Append to the same file:

```python
@override_settings(**_GAM_SETTINGS)
class UpdateCodingStatsKataTests(TestCase):
    def setUp(self):
        self.student = _create_test_user(username="kata_stu", role_name="student")
        self.teacher = _create_test_user(username="kata_teach", role_name="teacher")
        self.subject = _create_subject()

    def _make_kata_attempt(self, score=1.0):
        kata = SideActivity.objects.create(
            subject=self.subject, sub_type="code_kata",
            title="Kata 1", content_json={"test_cases": [{"input": "1", "expected": "1"}]},
            xp_reward=10, created_by=self.teacher,
        )
        attempt = SideActivityAttempt.objects.create(
            student=self.student, side_activity=kata,
            completed_at=timezone.now(), score=score,
            time_taken_seconds=30, xp_awarded=10,
        )
        return attempt

    def test_kata_completion_increments(self):
        attempt = self._make_kata_attempt(score=1.0)
        update_coding_stats_kata(self.student, attempt)
        stats = CodingStats.objects.get(student=self.student)
        self.assertEqual(stats.total_katas, 1)
        self.assertEqual(stats.perfect_katas, 1)
        self.assertEqual(stats.current_streak, 1)

    def test_failed_kata_resets_streak(self):
        a1 = self._make_kata_attempt(score=1.0)
        update_coding_stats_kata(self.student, a1)
        a2 = self._make_kata_attempt(score=0.3)
        update_coding_stats_kata(self.student, a2)
        stats = CodingStats.objects.get(student=self.student)
        self.assertEqual(stats.total_katas, 2)
        self.assertEqual(stats.perfect_katas, 1)
        self.assertEqual(stats.current_streak, 0)
        self.assertEqual(stats.best_streak, 1)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `~/classedge/env/bin/python manage.py test gamification.tests.test_coding_stats --keepdb -v2`
Expected: `ImportError: cannot import name 'update_coding_stats'`

- [ ] **Step 4: Implement the service**

Create `gamification/coding_stats_service.py`:

```python
from gamification.models import CodingStats


def update_coding_stats(student, submission):
    """Update CodingStats after a CodeSubmission is graded."""
    stats, _ = CodingStats.objects.get_or_create(student=student)

    stats.total_submissions += 1

    if submission.score == 1.0:
        stats.perfect_submissions += 1
        stats.current_streak += 1
        if stats.current_streak > stats.best_streak:
            stats.best_streak = stats.current_streak
        if submission.execution_time_ms is not None and submission.execution_time_ms < 500:
            stats.fast_perfects += 1
    else:
        stats.current_streak = 0

    lang = submission.language
    if lang and lang not in stats.languages_used:
        stats.languages_used = stats.languages_used + [lang]

    stats.save()


def update_coding_stats_kata(student, attempt):
    """Update CodingStats after a code_kata SideActivityAttempt completes."""
    stats, _ = CodingStats.objects.get_or_create(student=student)

    stats.total_katas += 1

    if attempt.score is not None and attempt.score == 1.0:
        stats.perfect_katas += 1
        stats.current_streak += 1
        if stats.current_streak > stats.best_streak:
            stats.best_streak = stats.current_streak
    else:
        stats.current_streak = 0

    stats.save()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `~/classedge/env/bin/python manage.py test gamification.tests.test_coding_stats --keepdb -v2`
Expected: All 9 tests PASS

- [ ] **Step 6: Commit**

```bash
git add gamification/coding_stats_service.py gamification/tests/test_coding_stats.py
git commit -m "feat(gamification): add CodingStats update service for IDE and kata submissions"
```

---

### Task 3: Wire CodingStats into IDE Task and Side Activity Submit

**Files:**
- Modify: `ide/tasks.py:120-126`
- Modify: `gamification/side_activity_views.py:114-159`

- [ ] **Step 1: Wire update_coding_stats into ide/tasks.py**

In `ide/tasks.py`, add import at the top (after line 6):

```python
from gamification.coding_stats_service import update_coding_stats
```

After line 119 (after the StudentActivity update block, before XP award), add:

```python
    # Update coding stats
    update_coding_stats(submission.student, submission)
```

The full block around lines 119-127 should now read:

```python
    if not created and total_score > sa.total_score:
        sa.total_score = total_score
        sa.save(update_fields=["total_score"])

    # Update coding stats
    update_coding_stats(submission.student, submission)

    # Award XP based on score
    if score >= 0.9:
        award_xp(submission.student, 30, "Coding exercise score >= 90%", "coding", source_id=submission.pk)
    elif score >= 0.5:
        award_xp(submission.student, 10, "Coding exercise score >= 50%", "coding", source_id=submission.pk)
```

- [ ] **Step 2: Wire update_coding_stats_kata into side_activity_views.py**

In `gamification/side_activity_views.py`, add import at the top (after line 12):

```python
from gamification.coding_stats_service import update_coding_stats_kata
```

In `side_activity_submit` (the JSON endpoint, around line 146), after the `award_xp` call, add the kata stats update. The block should read:

```python
    if first_completion:
        award_xp(
            request.user, xp,
            reason=f"Side activity: {activity.title}",
            source_type="side_activity",
            source_id=activity.pk,
        )

    # Update coding stats for code_kata type
    if activity.sub_type == "code_kata":
        attempt = SideActivityAttempt.objects.filter(
            student=request.user, side_activity=activity,
        ).order_by("-started_at").first()
        if attempt:
            update_coding_stats_kata(request.user, attempt)
```

Also do the same in `side_activity_play` (the form POST handler, around line 90). After the `award_xp` block:

```python
        if first_completion:
            award_xp(
                request.user, xp,
                reason=f"Side activity: {activity.title}",
                source_type="side_activity",
                source_id=activity.pk,
            )

        # Update coding stats for code_kata type
        if activity.sub_type == "code_kata":
            update_coding_stats_kata(request.user, SideActivityAttempt.objects.filter(
                student=request.user, side_activity=activity,
            ).order_by("-started_at").first())
```

- [ ] **Step 3: Run existing tests to verify no regressions**

Run: `~/classedge/env/bin/python manage.py test ide.tests gamification.tests --keepdb -v2`
Expected: All existing tests PASS

- [ ] **Step 4: Commit**

```bash
git add ide/tasks.py gamification/side_activity_views.py
git commit -m "feat: wire CodingStats updates into IDE task and side activity submit"
```

---

### Task 4: Seed 9 Coding Badges

**Files:**
- Create: `gamification/migrations/0007_seed_coding_badges.py`
- Modify: `gamification/tests/test_badges.py:119-128`

- [ ] **Step 1: Update seed count test**

In `gamification/tests/test_badges.py`, change line 123:

```python
    def test_starter_badges_exist(self):
        # 15 starter + 10 side activity + 9 coding = 34
        self.assertEqual(BadgeDefinition.objects.count(), 34)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `~/classedge/env/bin/python manage.py test gamification.tests.test_badges.SeedBadgesTests --keepdb -v2`
Expected: FAIL — `25 != 34`

- [ ] **Step 3: Create seed migration**

Create `gamification/migrations/0007_seed_coding_badges.py`:

```python
from django.db import migrations

CODING_BADGES = [
    ("first_code", "First Compile", "Complete your first coding activity", "bronze", "\U0001f5a5\ufe0f", {"type": "coding_first"}),
    ("bug_squasher", "Bug Squasher", "Pass all tests on 5 coding exercises", "bronze", "\U0001f41b", {"type": "coding_perfect_count", "threshold": 5}),
    ("kata_warrior", "Kata Warrior", "Complete 25 code katas", "silver", "\U0001f94b", {"type": "coding_kata_count", "threshold": 25}),
    ("polyglot", "Polyglot", "Pass exercises in both Python and JavaScript", "silver", "\U0001f310", {"type": "coding_polyglot"}),
    ("speed_coder", "Speed Coder", "All-tests-pass with execution under 500ms on 3 exercises", "silver", "\u26a1", {"type": "coding_fast_perfect", "threshold": 3}),
    ("code_streak", "Code Streak", "10 consecutive perfect coding submissions", "gold", "\U0001f517", {"type": "coding_streak", "threshold": 10}),
    ("algorithm_ace", "Algorithm Ace", "Score 100% on 20 coding exercises", "gold", "\U0001f9ee", {"type": "coding_perfect_count", "threshold": 20}),
    ("code_centurion", "Code Centurion", "Complete 100 coding activities", "gold", "\U0001f4bb", {"type": "coding_total", "threshold": 100}),
    ("code_legend", "Code Legend", "Score 100% on 50 exercises and complete 100 katas", "platinum", "\U0001f3c5", {"type": "coding_legend", "perfect_threshold": 50, "kata_threshold": 100}),
]


def seed_badges(apps, schema_editor):
    BadgeDefinition = apps.get_model("gamification", "BadgeDefinition")
    for code, name, desc, tier, icon, criteria in CODING_BADGES:
        BadgeDefinition.objects.get_or_create(
            code=code,
            defaults={"name": name, "description": desc, "tier": tier, "icon": icon, "criteria_json": criteria},
        )


def reverse_seed(apps, schema_editor):
    BadgeDefinition = apps.get_model("gamification", "BadgeDefinition")
    codes = [b[0] for b in CODING_BADGES]
    BadgeDefinition.objects.filter(code__in=codes).delete()


class Migration(migrations.Migration):
    dependencies = [("gamification", "0006_codingstats")]
    operations = [migrations.RunPython(seed_badges, reverse_seed)]
```

- [ ] **Step 4: Run migration**

```bash
cd ~/classedge && ./env/bin/python manage.py migrate gamification
```

- [ ] **Step 5: Run seed test to verify it passes**

Run: `~/classedge/env/bin/python manage.py test gamification.tests.test_badges.SeedBadgesTests --keepdb -v2`
Expected: PASS — 34 badges found

- [ ] **Step 6: Commit**

```bash
git add gamification/migrations/0007_seed_coding_badges.py gamification/tests/test_badges.py
git commit -m "feat(gamification): seed 9 coding badge definitions"
```

---

### Task 5: Coding Badge Evaluators

**Files:**
- Modify: `gamification/badges.py:1-159`
- Modify: `gamification/tests/test_badges.py`

- [ ] **Step 1: Write failing evaluator tests**

Append to `gamification/tests/test_badges.py`, after the `SeedBadgesTests` class:

```python
from gamification.models import CodingStats


class CodingBadgeEvaluatorTests(TestCase):
    def setUp(self):
        self.student = _create_test_user(username="coding_eval", role_name="student")
        self.gam = StudentGamification.objects.create(student=self.student, total_xp=0, current_level=1)

    def test_coding_first_badge(self):
        badge = BadgeDefinition.objects.create(
            code="t_first", name="First", description="d", tier="bronze", icon="x",
            criteria_json={"type": "coding_first"},
        )
        CodingStats.objects.create(student=self.student, total_submissions=1)
        evaluate_badges(self.student)
        self.assertTrue(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_coding_first_not_met(self):
        badge = BadgeDefinition.objects.create(
            code="t_first_no", name="First No", description="d", tier="bronze", icon="x",
            criteria_json={"type": "coding_first"},
        )
        CodingStats.objects.create(student=self.student, total_submissions=0, total_katas=0)
        evaluate_badges(self.student)
        self.assertFalse(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_coding_perfect_count_at_threshold(self):
        badge = BadgeDefinition.objects.create(
            code="t_perf5", name="Perf5", description="d", tier="bronze", icon="x",
            criteria_json={"type": "coding_perfect_count", "threshold": 5},
        )
        CodingStats.objects.create(student=self.student, perfect_submissions=5)
        evaluate_badges(self.student)
        self.assertTrue(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_coding_perfect_count_below_threshold(self):
        badge = BadgeDefinition.objects.create(
            code="t_perf5_no", name="Perf5 No", description="d", tier="bronze", icon="x",
            criteria_json={"type": "coding_perfect_count", "threshold": 5},
        )
        CodingStats.objects.create(student=self.student, perfect_submissions=4)
        evaluate_badges(self.student)
        self.assertFalse(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_coding_kata_count(self):
        badge = BadgeDefinition.objects.create(
            code="t_kata25", name="Kata25", description="d", tier="silver", icon="x",
            criteria_json={"type": "coding_kata_count", "threshold": 25},
        )
        CodingStats.objects.create(student=self.student, total_katas=25)
        evaluate_badges(self.student)
        self.assertTrue(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_coding_polyglot(self):
        badge = BadgeDefinition.objects.create(
            code="t_poly", name="Poly", description="d", tier="silver", icon="x",
            criteria_json={"type": "coding_polyglot"},
        )
        CodingStats.objects.create(student=self.student, languages_used=["python", "javascript"])
        evaluate_badges(self.student)
        self.assertTrue(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_coding_polyglot_one_lang(self):
        badge = BadgeDefinition.objects.create(
            code="t_poly_no", name="Poly No", description="d", tier="silver", icon="x",
            criteria_json={"type": "coding_polyglot"},
        )
        CodingStats.objects.create(student=self.student, languages_used=["python"])
        evaluate_badges(self.student)
        self.assertFalse(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_coding_fast_perfect(self):
        badge = BadgeDefinition.objects.create(
            code="t_fast3", name="Fast3", description="d", tier="silver", icon="x",
            criteria_json={"type": "coding_fast_perfect", "threshold": 3},
        )
        CodingStats.objects.create(student=self.student, fast_perfects=3)
        evaluate_badges(self.student)
        self.assertTrue(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_coding_streak(self):
        badge = BadgeDefinition.objects.create(
            code="t_streak10", name="Streak10", description="d", tier="gold", icon="x",
            criteria_json={"type": "coding_streak", "threshold": 10},
        )
        CodingStats.objects.create(student=self.student, best_streak=10)
        evaluate_badges(self.student)
        self.assertTrue(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_coding_total(self):
        badge = BadgeDefinition.objects.create(
            code="t_total100", name="Total100", description="d", tier="gold", icon="x",
            criteria_json={"type": "coding_total", "threshold": 100},
        )
        CodingStats.objects.create(student=self.student, total_submissions=60, total_katas=40)
        evaluate_badges(self.student)
        self.assertTrue(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_coding_legend_both_met(self):
        badge = BadgeDefinition.objects.create(
            code="t_legend", name="Legend", description="d", tier="platinum", icon="x",
            criteria_json={"type": "coding_legend", "perfect_threshold": 50, "kata_threshold": 100},
        )
        CodingStats.objects.create(student=self.student, perfect_submissions=50, total_katas=100)
        evaluate_badges(self.student)
        self.assertTrue(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_coding_legend_only_one_met(self):
        badge = BadgeDefinition.objects.create(
            code="t_legend_no", name="Legend No", description="d", tier="platinum", icon="x",
            criteria_json={"type": "coding_legend", "perfect_threshold": 50, "kata_threshold": 100},
        )
        CodingStats.objects.create(student=self.student, perfect_submissions=50, total_katas=10)
        evaluate_badges(self.student)
        self.assertFalse(StudentBadge.objects.filter(student=self.student, badge=badge).exists())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `~/classedge/env/bin/python manage.py test gamification.tests.test_badges.CodingBadgeEvaluatorTests --keepdb -v2`
Expected: FAIL — evaluator type not found in EVALUATORS

- [ ] **Step 3: Implement the 8 evaluator functions**

In `gamification/badges.py`, add import at the top (after line 3):

```python
from gamification.models import CodingStats
```

Add the evaluator functions before the `EVALUATORS` dict (before line 144):

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
    return (
        stats.perfect_submissions >= criteria["perfect_threshold"]
        and stats.total_katas >= criteria["kata_threshold"]
    )
```

Add to the `EVALUATORS` dict (extend it):

```python
EVALUATORS = {
    # ... existing entries stay as-is ...
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `~/classedge/env/bin/python manage.py test gamification.tests.test_badges --keepdb -v2`
Expected: All tests PASS (existing + 13 new)

- [ ] **Step 5: Commit**

```bash
git add gamification/badges.py gamification/tests/test_badges.py
git commit -m "feat(gamification): add 8 coding badge evaluator functions"
```

---

### Task 6: Badge Progress Computers

**Files:**
- Modify: `gamification/badges.py`
- Modify: `gamification/tests/test_badges.py`

- [ ] **Step 1: Write failing progress tests**

Append to `gamification/tests/test_badges.py`:

```python
from gamification.badges import compute_badge_progress


class BadgeProgressTests(TestCase):
    def setUp(self):
        self.student = _create_test_user(username="prog_stu", role_name="student")
        self.gam = StudentGamification.objects.create(student=self.student, total_xp=0, current_level=1)

    def test_progress_partial_xp(self):
        badge = BadgeDefinition.objects.create(
            code="p_xp", name="XP", description="d", tier="bronze", icon="x",
            criteria_json={"type": "xp_total", "threshold": 100},
        )
        self.gam.total_xp = 50
        self.gam.save()
        self.assertEqual(compute_badge_progress(self.student, badge), 50)

    def test_progress_caps_at_100(self):
        badge = BadgeDefinition.objects.create(
            code="p_xp_cap", name="XP Cap", description="d", tier="bronze", icon="x",
            criteria_json={"type": "xp_total", "threshold": 100},
        )
        self.gam.total_xp = 200
        self.gam.save()
        self.assertEqual(compute_badge_progress(self.student, badge), 100)

    def test_progress_coding_perfect(self):
        badge = BadgeDefinition.objects.create(
            code="p_perf", name="Perf", description="d", tier="bronze", icon="x",
            criteria_json={"type": "coding_perfect_count", "threshold": 10},
        )
        CodingStats.objects.create(student=self.student, perfect_submissions=3)
        self.assertEqual(compute_badge_progress(self.student, badge), 30)

    def test_progress_coding_legend_compound(self):
        badge = BadgeDefinition.objects.create(
            code="p_legend", name="Legend", description="d", tier="platinum", icon="x",
            criteria_json={"type": "coding_legend", "perfect_threshold": 50, "kata_threshold": 100},
        )
        CodingStats.objects.create(student=self.student, perfect_submissions=25, total_katas=50)
        # 25/50 = 50% of first half (25 pts) + 50/100 = 50% of second half (25 pts) = 50
        self.assertEqual(compute_badge_progress(self.student, badge), 50)

    def test_progress_empty_criteria(self):
        badge = BadgeDefinition.objects.create(
            code="p_empty", name="Empty", description="d", tier="platinum", icon="x",
            criteria_json={},
        )
        self.assertEqual(compute_badge_progress(self.student, badge), 0)

    def test_progress_streak(self):
        badge = BadgeDefinition.objects.create(
            code="p_streak", name="Streak", description="d", tier="silver", icon="x",
            criteria_json={"type": "streak", "streak": "login", "threshold": 7},
        )
        self.gam.login_streak = 3
        self.gam.save()
        self.assertEqual(compute_badge_progress(self.student, badge), 42)  # 3/7 = 42%

    def test_progress_level(self):
        badge = BadgeDefinition.objects.create(
            code="p_level", name="Level", description="d", tier="gold", icon="x",
            criteria_json={"type": "level", "threshold": 10},
        )
        self.gam.current_level = 4
        self.gam.save()
        self.assertEqual(compute_badge_progress(self.student, badge), 40)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `~/classedge/env/bin/python manage.py test gamification.tests.test_badges.BadgeProgressTests --keepdb -v2`
Expected: `ImportError: cannot import name 'compute_badge_progress'`

- [ ] **Step 3: Implement compute_badge_progress and PROGRESS_COMPUTERS**

In `gamification/badges.py`, add after the `EVALUATORS` dict:

```python
# ---------------------------------------------------------------------------
# Badge Progress Computers — return 0-100 int
# ---------------------------------------------------------------------------

def _progress_coding_stat(student, field, threshold):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return 0
    return min(100, int(getattr(stats, field, 0) / threshold * 100))


def _progress_coding_first(student):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return 0
    return 100 if (stats.total_submissions + stats.total_katas) >= 1 else 0


def _progress_coding_total(student, threshold):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return 0
    return min(100, int((stats.total_submissions + stats.total_katas) / threshold * 100))


def _progress_coding_polyglot(student):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return 0
    return min(100, len(stats.languages_used) * 50)


def _progress_coding_legend(student, criteria):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return 0
    p1 = min(50, int(stats.perfect_submissions / criteria["perfect_threshold"] * 50))
    p2 = min(50, int(stats.total_katas / criteria["kata_threshold"] * 50))
    return p1 + p2


def _progress_badges_earned(student, criteria):
    count = StudentBadge.objects.filter(student=student).count()
    return min(100, int(count / criteria["threshold"] * 100))


PROGRESS_COMPUTERS = {
    "xp_total": lambda s, g, c: min(100, int(g.total_xp / c["threshold"] * 100)),
    "streak": lambda s, g, c: min(100, int(getattr(g, f'{c["streak"]}_streak', 0) / c["threshold"] * 100)),
    "level": lambda s, g, c: min(100, int(g.current_level / c["threshold"] * 100)),
    "badges_earned": lambda s, g, c: _progress_badges_earned(s, c),
    "coding_first": lambda s, g, c: _progress_coding_first(s),
    "coding_perfect_count": lambda s, g, c: _progress_coding_stat(s, "perfect_submissions", c["threshold"]),
    "coding_kata_count": lambda s, g, c: _progress_coding_stat(s, "total_katas", c["threshold"]),
    "coding_polyglot": lambda s, g, c: _progress_coding_polyglot(s),
    "coding_fast_perfect": lambda s, g, c: _progress_coding_stat(s, "fast_perfects", c["threshold"]),
    "coding_streak": lambda s, g, c: _progress_coding_stat(s, "best_streak", c["threshold"]),
    "coding_total": lambda s, g, c: _progress_coding_total(s, c["threshold"]),
    "coding_legend": lambda s, g, c: _progress_coding_legend(s, c),
}


def compute_badge_progress(student, badge):
    """Compute progress (0-100) for a badge the student hasn't earned yet."""
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `~/classedge/env/bin/python manage.py test gamification.tests.test_badges.BadgeProgressTests --keepdb -v2`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add gamification/badges.py gamification/tests/test_badges.py
git commit -m "feat(gamification): add badge progress computers for all badge types"
```

---

### Task 7: Update Badge Collection UI with Progress Bars

**Files:**
- Modify: `gamification/views.py:163-188`
- Modify: `gamification/templates/gamification/badge_collection.html`

- [ ] **Step 1: Update badge_collection view to include progress**

In `gamification/views.py`, add import at top:

```python
from gamification.badges import compute_badge_progress
```

Replace the `badge_collection` view (lines 163-188) with:

```python
@login_required
def badge_collection(request):
    user = request.user
    tier_order = {"platinum": 0, "gold": 1, "silver": 2, "bronze": 3, "hidden": 4, "seasonal": 5}

    all_badges = BadgeDefinition.objects.filter(is_active=True)
    all_badges = sorted(all_badges, key=lambda b: (tier_order.get(b.tier, 6), b.name))

    earned_map = {}
    for sb in StudentBadge.objects.filter(student=user).select_related("badge"):
        earned_map[sb.badge_id] = sb

    badges = []
    for bd in all_badges:
        sb = earned_map.get(bd.pk)
        progress = 0
        if not sb:
            progress = compute_badge_progress(user, bd)
        badges.append({
            "definition": bd,
            "earned": sb is not None,
            "earned_at": sb.earned_at if sb else None,
            "progress": progress,
        })

    return render(request, "gamification/badge_collection.html", {
        "badges": badges,
        "earned_count": len(earned_map),
        "total_count": len(all_badges),
    })
```

- [ ] **Step 2: Update badge_collection.html template with progress bars**

Replace `gamification/templates/gamification/badge_collection.html` with:

```html
{% extends 'student_base.html' %}
{% block title %}Badge Collection{% endblock %}
{% block content %}
<div class="container-fluid py-4" style="max-width:1100px;">
    <div class="d-flex justify-content-between align-items-start mb-4">
        <div>
            <h3 style="font-family:var(--display);font-weight:700;letter-spacing:-0.02em;">Badge Collection</h3>
            <p style="color:var(--text-dim);font-size:14px;">{{ earned_count }} of {{ total_count }} unlocked</p>
        </div>
        <a href="{% url 'student_dashboard' %}" class="btn btn-outline-secondary btn-sm" style="border-color:var(--border);color:var(--text-dim);">&larr; Dashboard</a>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:16px;">
        {% for b in badges %}
        <div class="badge{% if not b.earned %} locked{% endif %}" style="padding:24px 16px;aspect-ratio:auto;min-height:180px;">
            <div class="ico" style="font-size:40px;margin-bottom:8px;">{{ b.definition.icon }}</div>
            <div class="name" style="font-size:12px;margin-bottom:4px;">{{ b.definition.name }}</div>
            {% if b.earned %}
            <div style="font-size:11px;color:var(--text-dim);margin-top:4px;">{{ b.definition.description|truncatechars:50 }}</div>
            <div style="font-size:10px;color:var(--text-muted);margin-top:8px;">
                <span class="badge" style="background:var(--surface-2);color:var(--gold);font-size:10px;padding:2px 8px;border-radius:100px;">{{ b.definition.tier|upper }}</span>
            </div>
            {% else %}
            <div style="font-size:11px;color:var(--text-muted);margin-top:4px;">{{ b.definition.description|truncatechars:50 }}</div>
            {% if b.progress > 0 %}
            <div style="margin-top:8px;">
                <div style="background:var(--surface-2);border-radius:4px;height:6px;overflow:hidden;">
                    <div style="background:var(--accent);height:100%;width:{{ b.progress }}%;border-radius:4px;transition:width .3s;"></div>
                </div>
                <div style="font-size:10px;color:var(--text-muted);margin-top:2px;">{{ b.progress }}%</div>
            </div>
            {% endif %}
            {% endif %}
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
```

- [ ] **Step 3: Run existing tests to verify no regressions**

Run: `~/classedge/env/bin/python manage.py test gamification.tests --keepdb -v2`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add gamification/views.py gamification/templates/gamification/badge_collection.html
git commit -m "feat(gamification): add progress bars to badge collection page"
```

---

### Task 8: "Almost There" Widget on Student Dashboard

**Files:**
- Modify: `gamification/views.py:21-127` (student_dashboard)
- Modify: `gamification/templates/gamification/student_dashboard.html:85-113`

- [ ] **Step 1: Update student_dashboard view to include almost-there badges**

In the `student_dashboard` view (around line 75, after `earned_count`), add:

```python
    # Almost-there badges: top 3 unearned by progress
    earned_ids = set(earned_map.keys()) if 'earned_map' not in dir() else set(
        StudentBadge.objects.filter(student=user).values_list("badge_id", flat=True)
    )
    almost_there = []
    for bd in BadgeDefinition.objects.filter(is_active=True).exclude(pk__in=earned_ids):
        prog = compute_badge_progress(user, bd)
        if 0 < prog < 100:
            almost_there.append({"badge": bd, "progress": prog})
    almost_there.sort(key=lambda x: -x["progress"])
    almost_there = almost_there[:3]
```

Wait — the view already has `earned_count` computed from `StudentBadge`. Let me be more precise. In `gamification/views.py`, inside `student_dashboard`, after line 76 (`earned_count = StudentBadge.objects.filter(student=user).count()`), add:

```python
    earned_badge_ids = set(
        StudentBadge.objects.filter(student=user).values_list("badge_id", flat=True)
    )
    almost_there = []
    for bd in BadgeDefinition.objects.filter(is_active=True).exclude(pk__in=earned_badge_ids):
        prog = compute_badge_progress(user, bd)
        if 0 < prog < 100:
            almost_there.append({"badge": bd, "progress": prog})
    almost_there.sort(key=lambda x: -x["progress"])
    almost_there = almost_there[:3]
```

Add `"almost_there": almost_there,` to the context dict (around line 126).

- [ ] **Step 2: Add "Almost There" section to student_dashboard.html**

In `gamification/templates/gamification/student_dashboard.html`, after the badge grid closing `</div>` and before the `<div class="badge-footer">` (around line 109), add:

```html
    {% if almost_there %}
    <div style="margin-top:16px;padding-top:12px;border-top:1px solid var(--border);">
      <h3 style="font-size:13px;color:var(--text-dim);margin-bottom:8px;">Almost There</h3>
      {% for item in almost_there %}
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
        <span style="font-size:20px;">{{ item.badge.icon }}</span>
        <div style="flex:1;">
          <div style="font-size:12px;font-weight:600;">{{ item.badge.name }}</div>
          <div style="background:var(--surface-2);border-radius:4px;height:5px;overflow:hidden;margin-top:3px;">
            <div style="background:var(--accent);height:100%;width:{{ item.progress }}%;border-radius:4px;"></div>
          </div>
        </div>
        <span style="font-size:11px;color:var(--text-muted);">{{ item.progress }}%</span>
      </div>
      {% endfor %}
    </div>
    {% endif %}
```

- [ ] **Step 3: Run existing tests to verify no regressions**

Run: `~/classedge/env/bin/python manage.py test gamification.tests --keepdb -v2`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add gamification/views.py gamification/templates/gamification/student_dashboard.html
git commit -m "feat(gamification): add 'Almost There' badge widget to student dashboard"
```

---

### Task 9: Badge Management — List View

**Files:**
- Modify: `gamification/views.py`
- Modify: `gamification/urls.py`
- Create: `gamification/templates/gamification/badge_management.html`
- Test: `gamification/tests/test_badge_management.py`

- [ ] **Step 1: Write failing tests for badge management**

Create `gamification/tests/test_badge_management.py`:

```python
from django.test import TestCase, Client
from ai_content.tests.test_models import _create_test_user
from gamification.models import BadgeDefinition, StudentBadge


class BadgeManagementTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = _create_test_user(username="bm_teach", role_name="teacher")
        self.student = _create_test_user(username="bm_stu", role_name="student")
        self.admin = _create_test_user(username="bm_admin", role_name="admin")

    def test_teacher_sees_badge_list(self):
        self.client.login(username="bm_teach", password="testpass")
        resp = self.client.get("/gamification/badges/manage/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("badges", resp.context)

    def test_admin_sees_badge_list(self):
        self.client.login(username="bm_admin", password="testpass")
        resp = self.client.get("/gamification/badges/manage/")
        self.assertEqual(resp.status_code, 200)

    def test_student_cannot_access_badge_management(self):
        self.client.login(username="bm_stu", password="testpass")
        resp = self.client.get("/gamification/badges/manage/")
        self.assertEqual(resp.status_code, 403)

    def test_toggle_badge_active(self):
        badge = BadgeDefinition.objects.create(
            code="toggle_test", name="Toggle", description="d",
            tier="bronze", icon="x", criteria_json={}, is_active=True,
        )
        self.client.login(username="bm_teach", password="testpass")
        resp = self.client.post(f"/gamification/badges/{badge.pk}/toggle/")
        self.assertEqual(resp.status_code, 302)
        badge.refresh_from_db()
        self.assertFalse(badge.is_active)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `~/classedge/env/bin/python manage.py test gamification.tests.test_badge_management --keepdb -v2`
Expected: 404 — URL not found

- [ ] **Step 3: Add badge_list view**

In `gamification/views.py`, add imports at top:

```python
from django.db.models import Count
from roles.decorators import teacher_or_admin_required
```

Add at the end of the file:

```python
@login_required
@teacher_or_admin_required
def badge_list(request):
    badges = BadgeDefinition.objects.annotate(
        earned_count=Count("studentbadge"),
    ).order_by("tier", "name")

    def _category(badge):
        ctype = (badge.criteria_json or {}).get("type", "")
        if ctype.startswith("coding_"):
            return "Coding"
        if ctype.startswith("side_activity"):
            return "Side Activity"
        return "General"

    badge_data = []
    for b in badges:
        badge_data.append({"badge": b, "category": _category(b), "earned_count": b.earned_count})

    return render(request, "gamification/badge_management.html", {
        "badges": badge_data,
    })


@login_required
@teacher_or_admin_required
def badge_toggle_active(request, badge_id):
    badge = get_object_or_404(BadgeDefinition, pk=badge_id)
    if request.method == "POST":
        badge.is_active = not badge.is_active
        badge.save(update_fields=["is_active"])
    return redirect("badge_management")
```

- [ ] **Step 4: Add URL patterns**

In `gamification/urls.py`, add:

```python
    path("gamification/badges/manage/", views.badge_list, name="badge_management"),
    path("gamification/badges/<int:badge_id>/toggle/", views.badge_toggle_active, name="badge_toggle_active"),
```

- [ ] **Step 5: Create badge_management.html template**

Create `gamification/templates/gamification/badge_management.html`:

```html
{% extends "base.html" %}
{% block title %}Badge Management{% endblock %}
{% block content %}
<div class="container-fluid py-4" style="max-width:1200px;">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h3 style="font-weight:700;">Badge Management</h3>
    </div>

    <div class="table-responsive">
        <table class="table table-hover align-middle">
            <thead>
                <tr>
                    <th style="width:40px;"></th>
                    <th>Name</th>
                    <th>Category</th>
                    <th>Tier</th>
                    <th>Earned</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for item in badges %}
                <tr{% if not item.badge.is_active %} style="opacity:0.5;"{% endif %}>
                    <td style="font-size:24px;">{{ item.badge.icon }}</td>
                    <td>
                        <strong>{{ item.badge.name }}</strong>
                        <div style="font-size:12px;color:#888;">{{ item.badge.description|truncatechars:60 }}</div>
                    </td>
                    <td><span class="badge bg-secondary">{{ item.category }}</span></td>
                    <td><span class="badge bg-{{ item.badge.tier }}">{{ item.badge.tier|upper }}</span></td>
                    <td>{{ item.earned_count }}</td>
                    <td>
                        {% if item.badge.is_active %}
                        <span class="badge bg-success">Active</span>
                        {% else %}
                        <span class="badge bg-danger">Inactive</span>
                        {% endif %}
                    </td>
                    <td>
                        <form method="post" action="{% url 'badge_toggle_active' item.badge.pk %}" style="display:inline;">
                            {% csrf_token %}
                            <button type="submit" class="btn btn-sm btn-outline-secondary">
                                {% if item.badge.is_active %}Deactivate{% else %}Activate{% endif %}
                            </button>
                        </form>
                        <a href="{% url 'badge_edit' item.badge.pk %}" class="btn btn-sm btn-outline-primary">Edit</a>
                        {% if not item.badge.criteria_json or not item.badge.criteria_json.type %}
                        <a href="{% url 'badge_manual_award' item.badge.pk %}" class="btn btn-sm btn-outline-warning">Award</a>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `~/classedge/env/bin/python manage.py test gamification.tests.test_badge_management --keepdb -v2`
Expected: All 4 tests PASS

- [ ] **Step 7: Commit**

```bash
git add gamification/views.py gamification/urls.py gamification/templates/gamification/badge_management.html gamification/tests/test_badge_management.py
git commit -m "feat(gamification): add teacher badge management list with active toggle"
```

---

### Task 10: Badge Management — Edit & Manual Award Views

**Files:**
- Modify: `gamification/views.py`
- Modify: `gamification/urls.py`
- Create: `gamification/templates/gamification/badge_edit.html`
- Create: `gamification/templates/gamification/badge_award.html`
- Modify: `gamification/tests/test_badge_management.py`

- [ ] **Step 1: Write failing tests for edit and manual award**

Append to `gamification/tests/test_badge_management.py`:

```python
    def test_badge_edit_renders(self):
        badge = BadgeDefinition.objects.create(
            code="edit_test", name="Edit Me", description="d",
            tier="bronze", icon="x", criteria_json={"type": "xp_total", "threshold": 100},
        )
        self.client.login(username="bm_teach", password="testpass")
        resp = self.client.get(f"/gamification/badges/{badge.pk}/edit/")
        self.assertEqual(resp.status_code, 200)

    def test_badge_edit_saves(self):
        badge = BadgeDefinition.objects.create(
            code="edit_save", name="Old Name", description="old desc",
            tier="bronze", icon="x", criteria_json={},
        )
        self.client.login(username="bm_teach", password="testpass")
        resp = self.client.post(f"/gamification/badges/{badge.pk}/edit/", {
            "name": "New Name",
            "description": "new desc",
            "icon": "y",
            "tier": "silver",
        })
        self.assertEqual(resp.status_code, 302)
        badge.refresh_from_db()
        self.assertEqual(badge.name, "New Name")
        self.assertEqual(badge.tier, "silver")

    def test_manual_award_creates_student_badge(self):
        badge = BadgeDefinition.objects.create(
            code="manual_test", name="Manual", description="d",
            tier="platinum", icon="x", criteria_json={},
        )
        self.client.login(username="bm_teach", password="testpass")
        resp = self.client.post(f"/gamification/badges/{badge.pk}/award/", {
            "student": self.student.pk,
            "reason": "Great work!",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(StudentBadge.objects.filter(
            student=self.student, badge=badge, awarded_by=self.teacher,
        ).exists())

    def test_manual_award_prevents_duplicate(self):
        badge = BadgeDefinition.objects.create(
            code="dup_test", name="Dup", description="d",
            tier="platinum", icon="x", criteria_json={},
        )
        StudentBadge.objects.create(student=self.student, badge=badge)
        self.client.login(username="bm_teach", password="testpass")
        resp = self.client.post(f"/gamification/badges/{badge.pk}/award/", {
            "student": self.student.pk,
            "reason": "Again",
        })
        self.assertEqual(resp.status_code, 200)  # re-renders form with error
        self.assertEqual(StudentBadge.objects.filter(student=self.student, badge=badge).count(), 1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `~/classedge/env/bin/python manage.py test gamification.tests.test_badge_management --keepdb -v2`
Expected: 404 for edit/award URLs

- [ ] **Step 3: Implement badge_edit and badge_manual_award views**

Append to `gamification/views.py`:

```python
@login_required
@teacher_or_admin_required
def badge_edit(request, badge_id):
    badge = get_object_or_404(BadgeDefinition, pk=badge_id)
    import json as _json

    if request.method == "POST":
        badge.name = request.POST.get("name", badge.name)
        badge.description = request.POST.get("description", badge.description)
        badge.icon = request.POST.get("icon", badge.icon)
        badge.tier = request.POST.get("tier", badge.tier)
        badge.save(update_fields=["name", "description", "icon", "tier"])
        return redirect("badge_management")

    return render(request, "gamification/badge_edit.html", {
        "badge": badge,
        "criteria_display": _json.dumps(badge.criteria_json, indent=2),
        "tier_choices": BadgeDefinition.TIER_CHOICES,
    })


@login_required
@teacher_or_admin_required
def badge_manual_award(request, badge_id):
    badge = get_object_or_404(BadgeDefinition, pk=badge_id)
    from accounts.models import CustomUser

    error = None
    if request.method == "POST":
        student_id = request.POST.get("student")
        reason = request.POST.get("reason", "")
        student = CustomUser.objects.filter(pk=student_id).first()
        if student:
            if StudentBadge.objects.filter(student=student, badge=badge).exists():
                error = "This student already has this badge."
            else:
                StudentBadge.objects.create(
                    student=student, badge=badge,
                    awarded_by=request.user, award_reason=reason,
                )
                return redirect("badge_management")

    students = CustomUser.objects.filter(
        profile__role__name__iexact="student",
    ).order_by("first_name", "last_name")

    return render(request, "gamification/badge_award.html", {
        "badge": badge,
        "students": students,
        "error": error,
    })
```

- [ ] **Step 4: Add URL patterns**

In `gamification/urls.py`, add:

```python
    path("gamification/badges/<int:badge_id>/edit/", views.badge_edit, name="badge_edit"),
    path("gamification/badges/<int:badge_id>/award/", views.badge_manual_award, name="badge_manual_award"),
```

- [ ] **Step 5: Create badge_edit.html**

Create `gamification/templates/gamification/badge_edit.html`:

```html
{% extends "base.html" %}
{% block title %}Edit Badge — {{ badge.name }}{% endblock %}
{% block content %}
<div class="container-fluid py-4" style="max-width:700px;">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h3 style="font-weight:700;">Edit Badge</h3>
        <a href="{% url 'badge_management' %}" class="btn btn-outline-secondary btn-sm">&larr; Back</a>
    </div>

    <form method="post">
        {% csrf_token %}
        <div class="mb-3">
            <label class="form-label">Code</label>
            <input type="text" class="form-control" value="{{ badge.code }}" disabled>
        </div>
        <div class="mb-3">
            <label class="form-label">Name</label>
            <input type="text" name="name" class="form-control" value="{{ badge.name }}" required>
        </div>
        <div class="mb-3">
            <label class="form-label">Description</label>
            <textarea name="description" class="form-control" rows="2" required>{{ badge.description }}</textarea>
        </div>
        <div class="mb-3">
            <label class="form-label">Icon (emoji)</label>
            <input type="text" name="icon" class="form-control" value="{{ badge.icon }}" required>
        </div>
        <div class="mb-3">
            <label class="form-label">Tier</label>
            <select name="tier" class="form-select">
                {% for val, label in tier_choices %}
                <option value="{{ val }}"{% if val == badge.tier %} selected{% endif %}>{{ label }}</option>
                {% endfor %}
            </select>
        </div>
        <div class="mb-3">
            <label class="form-label">Criteria (read-only)</label>
            <pre style="background:var(--surface-2,#f5f5f5);padding:12px;border-radius:6px;font-size:13px;">{{ criteria_display }}</pre>
        </div>
        <button type="submit" class="btn btn-primary">Save Changes</button>
    </form>
</div>
{% endblock %}
```

- [ ] **Step 6: Create badge_award.html**

Create `gamification/templates/gamification/badge_award.html`:

```html
{% extends "base.html" %}
{% block title %}Award Badge — {{ badge.name }}{% endblock %}
{% block content %}
<div class="container-fluid py-4" style="max-width:700px;">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h3 style="font-weight:700;">Award: {{ badge.icon }} {{ badge.name }}</h3>
        <a href="{% url 'badge_management' %}" class="btn btn-outline-secondary btn-sm">&larr; Back</a>
    </div>

    {% if error %}
    <div class="alert alert-danger">{{ error }}</div>
    {% endif %}

    <form method="post">
        {% csrf_token %}
        <div class="mb-3">
            <label class="form-label">Student</label>
            <select name="student" class="form-select" required>
                <option value="">Select student...</option>
                {% for s in students %}
                <option value="{{ s.pk }}">{{ s.get_full_name|default:s.username }}</option>
                {% endfor %}
            </select>
        </div>
        <div class="mb-3">
            <label class="form-label">Reason</label>
            <textarea name="reason" class="form-control" rows="2" placeholder="Why is this badge being awarded?"></textarea>
        </div>
        <button type="submit" class="btn btn-primary">Award Badge</button>
    </form>
</div>
{% endblock %}
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `~/classedge/env/bin/python manage.py test gamification.tests.test_badge_management --keepdb -v2`
Expected: All 8 tests PASS

- [ ] **Step 8: Commit**

```bash
git add gamification/views.py gamification/urls.py gamification/templates/gamification/badge_edit.html gamification/templates/gamification/badge_award.html gamification/tests/test_badge_management.py
git commit -m "feat(gamification): add badge edit and manual award views"
```

---

### Task 11: Teacher Auto-Checker — Bulk Overview

**Files:**
- Modify: `ide/views.py`
- Modify: `ide/urls.py`
- Create: `ide/templates/ide/coding_overview.html`
- Create: `ide/tests/test_auto_checker.py`

- [ ] **Step 1: Write failing tests**

Create `ide/tests/test_auto_checker.py`:

```python
from datetime import date
from django.test import TestCase, Client, override_settings
from ai_content.tests.test_models import _create_test_user, _create_subject
from activity.models.activity_model import Activity, ActivityType
from course.models.semester_model import Semester
from course.models.term_model import Term
from ide.models import CodingExercise, CodeSubmission
from subject.models.subject_model import Subject

_GAM_SETTINGS = {
    "GAMIFICATION_XP_RATES": {
        "submission": 50, "early_submission": 75, "score_90": 30,
        "score_75": 15, "daily_login": 5, "perfect_attendance_week": 50,
    },
    "GAMIFICATION_STREAK_FREEZE_MONTHLY": 1,
}


@override_settings(**_GAM_SETTINGS)
class CodingOverviewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = _create_test_user(username="ac_teach", role_name="teacher")
        self.student = _create_test_user(username="ac_stu", role_name="student")
        self.subject = _create_subject()
        Subject.objects.filter(pk=self.subject.pk).update(assign_teacher=self.teacher)
        self.semester = Semester.objects.create(
            semester_name="Sem", start_date=date(2026, 1, 1), end_date=date(2027, 12, 31),
        )
        self.term = Term.objects.create(
            term_name="Prelim", semester=self.semester,
            start_date=date(2026, 8, 15), end_date=date(2026, 10, 15),
        )
        self.activity_type, _ = ActivityType.objects.get_or_create(name="Coding")
        self.activity = Activity.objects.create(
            activity_name="Sum", activity_type=self.activity_type,
            subject=self.subject, term=self.term, max_score=100,
        )
        self.exercise = CodingExercise.objects.create(
            activity=self.activity, language="python",
            starter_code="", solution_code="",
            test_cases=[{"input": "1 2", "expected_output": "3"}],
        )

    def test_teacher_sees_overview(self):
        self.client.login(username="ac_teach", password="testpass")
        resp = self.client.get("/ide/overview/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("exercises", resp.context)

    def test_student_cannot_access_overview(self):
        self.client.login(username="ac_stu", password="testpass")
        resp = self.client.get("/ide/overview/")
        self.assertEqual(resp.status_code, 403)

    def test_overview_shows_exercise_stats(self):
        CodeSubmission.objects.create(
            student=self.student, exercise=self.exercise,
            code="print(3)", language="python",
            status="completed", score=1.0,
        )
        self.client.login(username="ac_teach", password="testpass")
        resp = self.client.get("/ide/overview/")
        exercises = resp.context["exercises"]
        self.assertEqual(len(exercises), 1)
        self.assertEqual(exercises[0]["attempted_count"], 1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `~/classedge/env/bin/python manage.py test ide.tests.test_auto_checker --keepdb -v2`
Expected: 404 — URL not found

- [ ] **Step 3: Implement coding_overview view**

In `ide/views.py`, add imports at top:

```python
from django.db.models import Avg, Count, Q
from roles.decorators import teacher_or_admin_required
```

Add at the end of the file:

```python
@login_required
@teacher_or_admin_required
def coding_overview(request):
    exercises = CodingExercise.objects.select_related(
        "activity", "activity__subject",
    ).order_by("-created_at")

    exercise_data = []
    for ex in exercises:
        subs = CodeSubmission.objects.filter(exercise=ex, status="completed")
        student_ids = subs.values_list("student_id", flat=True).distinct()
        attempted = student_ids.count()

        # Best score per student, then average
        best_scores = []
        for sid in student_ids:
            best = subs.filter(student_id=sid).order_by("-score").first()
            if best:
                best_scores.append(best.score)

        avg_score = sum(best_scores) / len(best_scores) if best_scores else 0
        perfect_count = sum(1 for s in best_scores if s == 1.0)

        exercise_data.append({
            "exercise": ex,
            "activity_name": ex.activity.activity_name,
            "subject_name": ex.activity.subject.subject_name if ex.activity.subject else "",
            "language": ex.get_language_display(),
            "attempted_count": attempted,
            "avg_score": round(avg_score * 100, 1),
            "perfect_count": perfect_count,
        })

    return render(request, "ide/coding_overview.html", {
        "exercises": exercise_data,
    })
```

- [ ] **Step 4: Add URL pattern**

In `ide/urls.py`, add:

```python
    path("ide/overview/", views.coding_overview, name="coding_overview"),
```

- [ ] **Step 5: Create coding_overview.html template**

Create `ide/templates/ide/coding_overview.html`:

```html
{% extends "base.html" %}
{% block title %}Coding Exercise Overview{% endblock %}
{% block content %}
<div class="container-fluid py-4" style="max-width:1200px;">
    <h3 style="font-weight:700;margin-bottom:1.5rem;">Coding Exercise Overview</h3>

    <div class="table-responsive">
        <table class="table table-hover align-middle">
            <thead>
                <tr>
                    <th>Exercise</th>
                    <th>Subject</th>
                    <th>Language</th>
                    <th>Attempted</th>
                    <th>Avg Score</th>
                    <th>Perfect</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                {% for ex in exercises %}
                <tr>
                    <td><strong>{{ ex.activity_name }}</strong></td>
                    <td>{{ ex.subject_name }}</td>
                    <td><span class="badge bg-info">{{ ex.language }}</span></td>
                    <td>{{ ex.attempted_count }}</td>
                    <td>
                        <div style="display:flex;align-items:center;gap:8px;">
                            <div style="background:#e9ecef;border-radius:4px;height:8px;width:80px;overflow:hidden;">
                                <div style="background:{% if ex.avg_score >= 90 %}#198754{% elif ex.avg_score >= 50 %}#ffc107{% else %}#dc3545{% endif %};height:100%;width:{{ ex.avg_score }}%;"></div>
                            </div>
                            <span style="font-size:13px;">{{ ex.avg_score }}%</span>
                        </div>
                    </td>
                    <td>{{ ex.perfect_count }}</td>
                    <td>
                        <a href="{% url 'coding_exercise_results' ex.exercise.pk %}" class="btn btn-sm btn-outline-primary">View Results</a>
                    </td>
                </tr>
                {% empty %}
                <tr><td colspan="7" style="text-align:center;color:#888;padding:2rem;">No coding exercises yet.</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `~/classedge/env/bin/python manage.py test ide.tests.test_auto_checker --keepdb -v2`
Expected: All 3 tests PASS

- [ ] **Step 7: Commit**

```bash
git add ide/views.py ide/urls.py ide/templates/ide/coding_overview.html ide/tests/test_auto_checker.py
git commit -m "feat(ide): add teacher coding overview dashboard"
```

---

### Task 12: Teacher Auto-Checker — Exercise Results & Score Override

**Files:**
- Modify: `ide/views.py`
- Modify: `ide/urls.py`
- Create: `ide/templates/ide/coding_exercise_results.html`
- Modify: `ide/tests/test_auto_checker.py`

- [ ] **Step 1: Write failing tests**

Append to `ide/tests/test_auto_checker.py`:

```python
@override_settings(**_GAM_SETTINGS)
class CodingExerciseResultsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = _create_test_user(username="res_teach", role_name="teacher")
        self.student = _create_test_user(username="res_stu", role_name="student")
        self.subject = _create_subject()
        Subject.objects.filter(pk=self.subject.pk).update(assign_teacher=self.teacher)
        self.semester = Semester.objects.create(
            semester_name="Sem2", start_date=date(2026, 1, 1), end_date=date(2027, 12, 31),
        )
        self.term = Term.objects.create(
            term_name="Prelim2", semester=self.semester,
            start_date=date(2026, 8, 15), end_date=date(2026, 10, 15),
        )
        self.activity_type, _ = ActivityType.objects.get_or_create(name="Coding")
        self.activity = Activity.objects.create(
            activity_name="Multiply", activity_type=self.activity_type,
            subject=self.subject, term=self.term, max_score=100,
        )
        self.exercise = CodingExercise.objects.create(
            activity=self.activity, language="python",
            starter_code="", solution_code="",
            test_cases=[{"input": "2 3", "expected_output": "6"}],
        )
        self.submission = CodeSubmission.objects.create(
            student=self.student, exercise=self.exercise,
            code="print(6)", language="python",
            status="completed", score=1.0,
            result_json={"tests": [{"test": 1, "passed": True, "stdout": "6", "expected": "6"}]},
            execution_time_ms=42,
        )

    def test_results_page_shows_submissions(self):
        self.client.login(username="res_teach", password="testpass")
        resp = self.client.get(f"/ide/exercise/{self.exercise.pk}/results/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("students", resp.context)
        self.assertEqual(len(resp.context["students"]), 1)

    def test_score_override_updates_submission(self):
        self.client.login(username="res_teach", password="testpass")
        resp = self.client.post(f"/ide/submission/{self.submission.pk}/override/", {
            "new_score": "0.8",
            "override_note": "Accepted alternative approach",
        })
        self.assertEqual(resp.status_code, 302)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.score, 0.8)
        self.assertIn("override", self.submission.result_json)
        self.assertEqual(self.submission.result_json["override"]["note"], "Accepted alternative approach")

    def test_student_cannot_override(self):
        self.client.login(username="res_stu", password="testpass")
        resp = self.client.post(f"/ide/submission/{self.submission.pk}/override/", {
            "new_score": "1.0",
            "override_note": "hack",
        })
        self.assertEqual(resp.status_code, 403)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `~/classedge/env/bin/python manage.py test ide.tests.test_auto_checker.CodingExerciseResultsTests --keepdb -v2`
Expected: 404 — URL not found

- [ ] **Step 3: Implement views**

Append to `ide/views.py`:

```python
@login_required
@teacher_or_admin_required
def coding_exercise_results(request, exercise_id):
    exercise = get_object_or_404(CodingExercise, pk=exercise_id)
    submissions = (
        CodeSubmission.objects.filter(exercise=exercise, status="completed")
        .select_related("student")
        .order_by("student__last_name", "student__first_name", "-score")
    )

    # Group by student — best submission first
    student_map = {}
    for sub in submissions:
        if sub.student_id not in student_map:
            student_map[sub.student_id] = {
                "student": sub.student,
                "best": sub,
                "attempts": 0,
            }
        student_map[sub.student_id]["attempts"] += 1

    students = sorted(student_map.values(), key=lambda x: x["student"].last_name)

    return render(request, "ide/coding_exercise_results.html", {
        "exercise": exercise,
        "students": students,
        "test_labels": [
            tc.get("label", f"Test {i + 1}")
            for i, tc in enumerate(exercise.test_cases)
        ],
    })


@login_required
@teacher_or_admin_required
def coding_score_override(request, submission_id):
    from django.utils import timezone as tz

    submission = get_object_or_404(CodeSubmission, pk=submission_id)

    if request.method == "POST":
        new_score_str = request.POST.get("new_score", "")
        note = request.POST.get("override_note", "")
        try:
            new_score = float(new_score_str)
            new_score = max(0.0, min(1.0, new_score))
        except (ValueError, TypeError):
            return redirect("coding_exercise_results", exercise_id=submission.exercise_id)

        old_score = submission.score
        submission.score = new_score
        result = submission.result_json or {}
        result["override"] = {
            "by": request.user.pk,
            "original_score": old_score,
            "new_score": new_score,
            "note": note,
            "at": tz.now().isoformat(),
        }
        submission.result_json = result
        submission.save(update_fields=["score", "result_json"])

        # Update StudentActivity if exists
        from activity.models.student_activity_model import StudentActivity
        sa = StudentActivity.objects.filter(
            student=submission.student, activity=submission.exercise.activity,
        ).first()
        if sa:
            max_score = submission.exercise.activity.max_score or 100
            sa.total_score = new_score * max_score
            sa.save(update_fields=["total_score"])

        return redirect("coding_exercise_results", exercise_id=submission.exercise_id)

    return redirect("coding_exercise_results", exercise_id=submission.exercise_id)
```

- [ ] **Step 4: Add URL patterns**

In `ide/urls.py`, add:

```python
    path("ide/exercise/<int:exercise_id>/results/", views.coding_exercise_results, name="coding_exercise_results"),
    path("ide/submission/<int:submission_id>/override/", views.coding_score_override, name="coding_score_override"),
```

- [ ] **Step 5: Create coding_exercise_results.html template**

Create `ide/templates/ide/coding_exercise_results.html`:

```html
{% extends "base.html" %}
{% block title %}Results — {{ exercise.activity.activity_name }}{% endblock %}
{% block content %}
<div class="container-fluid py-4" style="max-width:1200px;">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <div>
            <h3 style="font-weight:700;">{{ exercise.activity.activity_name }}</h3>
            <p style="color:#888;font-size:14px;">{{ exercise.get_language_display }} &mdash; {{ test_labels|length }} test case{{ test_labels|length|pluralize }}</p>
        </div>
        <a href="{% url 'coding_overview' %}" class="btn btn-outline-secondary btn-sm">&larr; Overview</a>
    </div>

    <div class="table-responsive">
        <table class="table table-hover align-middle">
            <thead>
                <tr>
                    <th>Student</th>
                    <th>Best Score</th>
                    {% for label in test_labels %}
                    <th style="text-align:center;font-size:12px;">{{ label }}</th>
                    {% endfor %}
                    <th>Time</th>
                    <th>Attempts</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for row in students %}
                <tr>
                    <td>{{ row.student.get_full_name|default:row.student.username }}</td>
                    <td>
                        {% with score_pct=row.best.score|floatformat:0 %}
                        <span style="font-weight:600;color:{% if row.best.score >= 0.9 %}#198754{% elif row.best.score >= 0.5 %}#856404{% else %}#dc3545{% endif %};">
                            {{ row.best.score|floatformat:2 }}
                        </span>
                        {% endwith %}
                        {% if row.best.result_json.override %}
                        <span style="font-size:11px;color:#6c757d;" title="Overridden by teacher">(overridden)</span>
                        {% endif %}
                    </td>
                    {% for t in row.best.result_json.tests %}
                    <td style="text-align:center;">
                        {% if t.passed %}<span style="color:#198754;font-size:18px;">&#x2713;</span>{% else %}<span style="color:#dc3545;font-size:18px;">&#x2717;</span>{% endif %}
                    </td>
                    {% endfor %}
                    <td style="font-size:13px;">{% if row.best.execution_time_ms %}{{ row.best.execution_time_ms }}ms{% else %}&mdash;{% endif %}</td>
                    <td>{{ row.attempts }}</td>
                    <td>
                        <button type="button" class="btn btn-sm btn-outline-warning"
                                onclick="document.getElementById('override-{{ row.best.pk }}').style.display='block'">
                            Override
                        </button>
                        <div id="override-{{ row.best.pk }}" style="display:none;margin-top:8px;">
                            <form method="post" action="{% url 'coding_score_override' row.best.pk %}">
                                {% csrf_token %}
                                <div style="display:flex;gap:6px;align-items:center;">
                                    <input type="number" name="new_score" step="0.01" min="0" max="1"
                                           value="{{ row.best.score|floatformat:2 }}"
                                           style="width:80px;" class="form-control form-control-sm">
                                    <input type="text" name="override_note" placeholder="Reason"
                                           class="form-control form-control-sm" required>
                                    <button type="submit" class="btn btn-sm btn-warning">Save</button>
                                </div>
                            </form>
                        </div>
                    </td>
                </tr>
                {% empty %}
                <tr><td colspan="{{ test_labels|length|add:5 }}" style="text-align:center;color:#888;padding:2rem;">No submissions yet.</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `~/classedge/env/bin/python manage.py test ide.tests.test_auto_checker --keepdb -v2`
Expected: All 6 tests PASS

- [ ] **Step 7: Commit**

```bash
git add ide/views.py ide/urls.py ide/templates/ide/coding_exercise_results.html ide/tests/test_auto_checker.py
git commit -m "feat(ide): add exercise results view with score override for teachers"
```

---

### Task 13: Full Integration Test & Final Commit

**Files:**
- All modified files

- [ ] **Step 1: Run the full test suite**

```bash
cd ~/classedge && ./env/bin/python manage.py test gamification.tests ide.tests --keepdb -v2
```

Expected: All tests PASS. Count should include:
- `gamification/tests/test_badges.py` — existing 10 + 13 coding evaluator + 7 progress = 30
- `gamification/tests/test_coding_stats.py` — 2 model + 7 service = 9
- `gamification/tests/test_badge_management.py` — 8
- `ide/tests/test_tasks.py` — 5 (existing)
- `ide/tests/test_views.py` — 5 (existing)
- `ide/tests/test_auto_checker.py` — 6
- Plus existing gamification tests (services, signals, side activities)

- [ ] **Step 2: Run migrations check**

```bash
cd ~/classedge && ./env/bin/python manage.py makemigrations --check --dry-run
```

Expected: No new migrations needed

- [ ] **Step 3: Push to personal remote**

```bash
cd ~/classedge && git push personal main
```
