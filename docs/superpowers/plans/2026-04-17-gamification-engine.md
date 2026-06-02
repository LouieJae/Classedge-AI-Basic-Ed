# Gamification Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a gamification backend that awards XP, tracks streaks, calculates levels, and evaluates badge criteria based on student actions in existing ClassEdge models.

**Architecture:** New `gamification/` Django app with 4 models (`StudentGamification`, `XPTransaction`, `BadgeDefinition`, `StudentBadge`). Central `award_xp` service wired to existing `StudentActivity`, `Attendance`, and login signals. Declarative badge criteria evaluated after every XP award. Replaces the legacy `accounts.Badge` model.

**Tech Stack:** Django 5, PostgreSQL, existing test helpers (`_create_test_user`, `_create_subject`)

---

## File Structure

### New files

| File | Responsibility |
|------|---------------|
| `gamification/__init__.py` | App package |
| `gamification/apps.py` | App config, signal registration |
| `gamification/models.py` | StudentGamification, XPTransaction, BadgeDefinition, StudentBadge |
| `gamification/services.py` | `award_xp()` — central XP award function |
| `gamification/streaks.py` | Streak update functions (login, submission, accuracy) |
| `gamification/badges.py` | Badge evaluation engine + evaluator registry |
| `gamification/signals.py` | Signal handlers wired to existing models |
| `gamification/management/commands/reset_streak_freezes.py` | Monthly freeze reset command |
| `gamification/tests/__init__.py` | Test package |
| `gamification/tests/test_models.py` | Model creation, constraints |
| `gamification/tests/test_services.py` | award_xp atomicity, level calc, dedup |
| `gamification/tests/test_streaks.py` | Streak increment, reset, freeze |
| `gamification/tests/test_badges.py` | Each evaluator type, teacher award, seed |
| `gamification/tests/test_signals.py` | XP awarded on StudentActivity/login/attendance |
| `gamification/migrations/0001_initial.py` | Auto-generated model migration |
| `gamification/migrations/0002_seed_badges.py` | Data migration: seed 15 starter badges |
| `gamification/migrations/0003_migrate_legacy_badges.py` | Data migration: old Badge → new system |

### Modified files

| File | Change |
|------|--------|
| `lms/settings.py` | Add `'gamification'` to INSTALLED_APPS, add XP rate settings |
| `accounts/models/__init__.py` | Remove `Badge` import (after legacy migration) |
| `accounts/models/badge_models.py` | Delete file |
| `accounts/views/__init__.py` | Remove badge view imports |
| `accounts/views/badge_views.py` | Delete file |
| `accounts/forms/__init__.py` | Remove BadgeForm import (if present) |
| `accounts/forms/badge_forms.py` | Delete file |
| `accounts/templates/accounts/badge/` | Delete directory |
| `accounts/urls.py` | Remove badge URL patterns (lines 90-93) |

---

## Task 1: App Scaffold + Models

**Files:**
- Create: `gamification/__init__.py`, `gamification/apps.py`, `gamification/models.py`
- Create: `gamification/tests/__init__.py`, `gamification/tests/test_models.py`
- Modify: `lms/settings.py`

- [ ] **Step 1: Create app package**

Create `gamification/__init__.py` (empty).

Create `gamification/apps.py`:
```python
from django.apps import AppConfig


class GamificationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gamification"

    def ready(self):
        import gamification.signals  # noqa: F401
```

Create `gamification/tests/__init__.py` (empty).

- [ ] **Step 2: Register app in settings**

In `lms/settings.py`, add `'gamification'` to INSTALLED_APPS after `'at_risk'`.

Add at the end of the file:
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

- [ ] **Step 3: Create the models**

Create `gamification/models.py`:
```python
from django.conf import settings
from django.db import models


class StudentGamification(models.Model):
    student = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
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

    def __str__(self):
        return f"{self.student.username} — Level {self.current_level} ({self.total_xp} XP)"


class XPTransaction(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="xp_transactions",
    )
    amount = models.IntegerField()
    reason = models.CharField(max_length=100)
    source_type = models.CharField(max_length=50)
    source_id = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["student", "created_at"]),
            models.Index(fields=["source_type", "source_id"]),
        ]

    def __str__(self):
        return f"{self.student.username} +{self.amount} XP ({self.reason})"


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
    icon = models.CharField(max_length=50)
    target_role = models.CharField(max_length=20, default="student")
    criteria_json = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.icon} {self.name} ({self.tier})"


class StudentBadge(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="earned_badges",
    )
    badge = models.ForeignKey(BadgeDefinition, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)
    progress_percent = models.PositiveSmallIntegerField(default=100)
    awarded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manually_awarded_badges",
    )
    award_reason = models.CharField(max_length=300, blank=True, default="")

    class Meta:
        unique_together = [("student", "badge")]

    def __str__(self):
        return f"{self.student.username} — {self.badge.name}"
```

- [ ] **Step 4: Create a stub signals module**

Create `gamification/signals.py` (stub so `apps.py` import doesn't fail):
```python
# Signal handlers — implemented in Task 5.
```

- [ ] **Step 5: Generate and run migration**

Run:
```bash
cd ~/classedge && env/bin/python manage.py makemigrations gamification
env/bin/python manage.py migrate --run-syncdb 2>&1 | tail -5
```
Expected: migration `0001_initial` created and applied.

- [ ] **Step 6: Write model tests**

Create `gamification/tests/test_models.py`:
```python
from django.test import TestCase
from django.db import IntegrityError

from ai_content.tests.test_models import _create_test_user
from gamification.models import (
    BadgeDefinition,
    StudentBadge,
    StudentGamification,
    XPTransaction,
)


class StudentGamificationTests(TestCase):
    def test_create_defaults(self):
        user = _create_test_user(username="gam_student", role_name="student")
        gam = StudentGamification.objects.create(student=user)
        self.assertEqual(gam.total_xp, 0)
        self.assertEqual(gam.current_level, 1)
        self.assertEqual(gam.login_streak, 0)
        self.assertEqual(gam.streak_freezes_available, 1)

    def test_one_to_one_enforced(self):
        user = _create_test_user(username="gam_dup", role_name="student")
        StudentGamification.objects.create(student=user)
        with self.assertRaises(IntegrityError):
            StudentGamification.objects.create(student=user)


class XPTransactionTests(TestCase):
    def test_create_transaction(self):
        user = _create_test_user(username="xp_student", role_name="student")
        tx = XPTransaction.objects.create(
            student=user,
            amount=50,
            reason="test",
            source_type="activity",
            source_id=1,
        )
        self.assertEqual(tx.amount, 50)
        self.assertIsNotNone(tx.created_at)


class BadgeDefinitionTests(TestCase):
    def test_create_badge(self):
        badge = BadgeDefinition.objects.create(
            code="test_badge",
            name="Test Badge",
            description="A test badge",
            tier="bronze",
            icon="🏅",
            criteria_json={"type": "xp_total", "threshold": 100},
        )
        self.assertEqual(badge.code, "test_badge")
        self.assertTrue(badge.is_active)

    def test_code_unique(self):
        BadgeDefinition.objects.create(
            code="unique_test",
            name="Badge 1",
            description="desc",
            tier="bronze",
            icon="🏅",
        )
        with self.assertRaises(IntegrityError):
            BadgeDefinition.objects.create(
                code="unique_test",
                name="Badge 2",
                description="desc",
                tier="silver",
                icon="🏅",
            )


class StudentBadgeTests(TestCase):
    def test_create_earned_badge(self):
        user = _create_test_user(username="badge_student", role_name="student")
        badge_def = BadgeDefinition.objects.create(
            code="sb_test",
            name="Test",
            description="desc",
            tier="bronze",
            icon="🏅",
        )
        sb = StudentBadge.objects.create(student=user, badge=badge_def)
        self.assertEqual(sb.progress_percent, 100)
        self.assertIsNone(sb.awarded_by)

    def test_unique_together(self):
        user = _create_test_user(username="badge_dup", role_name="student")
        badge_def = BadgeDefinition.objects.create(
            code="sb_dup",
            name="Dup",
            description="desc",
            tier="bronze",
            icon="🏅",
        )
        StudentBadge.objects.create(student=user, badge=badge_def)
        with self.assertRaises(IntegrityError):
            StudentBadge.objects.create(student=user, badge=badge_def)

    def test_teacher_awarded(self):
        student = _create_test_user(username="badge_stu2", role_name="student")
        teacher = _create_test_user(username="badge_teach", role_name="teacher")
        badge_def = BadgeDefinition.objects.create(
            code="sb_award",
            name="Award",
            description="desc",
            tier="platinum",
            icon="🏆",
        )
        sb = StudentBadge.objects.create(
            student=student,
            badge=badge_def,
            awarded_by=teacher,
            award_reason="Great effort",
        )
        self.assertEqual(sb.awarded_by, teacher)
        self.assertEqual(sb.award_reason, "Great effort")
```

- [ ] **Step 7: Run model tests**

Run: `cd ~/classedge && env/bin/python manage.py test gamification.tests.test_models --keepdb -v2`
Expected: All 7 tests PASS

- [ ] **Step 8: Commit**

```bash
cd ~/classedge && git add gamification/ && git add -f lms/settings.py
git commit -m "feat(gamification): add app scaffold with 4 models"
```

---

## Task 2: XP Award Service + Level Calculation

**Files:**
- Create: `gamification/services.py`
- Create: `gamification/tests/test_services.py`

- [ ] **Step 1: Write service tests**

Create `gamification/tests/test_services.py`:
```python
import math

from django.test import TestCase

from ai_content.tests.test_models import _create_test_user
from gamification.models import StudentGamification, XPTransaction
from gamification.services import award_xp


class AwardXPTests(TestCase):
    def setUp(self):
        self.student = _create_test_user(username="xp_svc_stu", role_name="student")

    def test_award_xp_creates_transaction(self):
        tx = award_xp(self.student, 50, "test award", "test", source_id=1)
        self.assertIsNotNone(tx)
        self.assertEqual(tx.amount, 50)
        self.assertEqual(XPTransaction.objects.count(), 1)

    def test_award_xp_updates_total(self):
        award_xp(self.student, 50, "first", "test", source_id=1)
        award_xp(self.student, 30, "second", "test", source_id=2)
        gam = StudentGamification.objects.get(student=self.student)
        self.assertEqual(gam.total_xp, 80)

    def test_award_xp_auto_creates_gamification(self):
        self.assertFalse(
            StudentGamification.objects.filter(student=self.student).exists()
        )
        award_xp(self.student, 10, "auto create", "test", source_id=1)
        self.assertTrue(
            StudentGamification.objects.filter(student=self.student).exists()
        )

    def test_duplicate_source_returns_none(self):
        award_xp(self.student, 50, "first", "activity", source_id=99)
        result = award_xp(self.student, 50, "duplicate", "activity", source_id=99)
        self.assertIsNone(result)
        self.assertEqual(XPTransaction.objects.count(), 1)

    def test_level_calculation(self):
        # level = floor(sqrt(xp / 100))
        # 10000 XP → level 10
        award_xp(self.student, 10000, "big award", "test", source_id=1)
        gam = StudentGamification.objects.get(student=self.student)
        self.assertEqual(gam.current_level, 10)

    def test_level_stays_1_for_small_xp(self):
        award_xp(self.student, 50, "small", "test", source_id=1)
        gam = StudentGamification.objects.get(student=self.student)
        # floor(sqrt(50/100)) = floor(0.707) = 0, but min level is 1
        self.assertEqual(gam.current_level, 1)

    def test_level_20_at_40000_xp(self):
        award_xp(self.student, 40000, "massive", "test", source_id=1)
        gam = StudentGamification.objects.get(student=self.student)
        self.assertEqual(gam.current_level, 20)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/classedge && env/bin/python manage.py test gamification.tests.test_services --keepdb -v2 2>&1 | tail -10`
Expected: ImportError (services module doesn't exist yet)

- [ ] **Step 3: Write the service**

Create `gamification/services.py`:
```python
import math

from django.db.models import F

from gamification.models import StudentGamification, XPTransaction


def award_xp(student, amount, reason, source_type, source_id=None):
    """Award XP to a student. Returns the XPTransaction or None if duplicate."""
    if source_id is not None:
        duplicate = XPTransaction.objects.filter(
            student=student,
            source_type=source_type,
            source_id=source_id,
        ).exists()
        if duplicate:
            return None

    tx = XPTransaction.objects.create(
        student=student,
        amount=amount,
        reason=reason,
        source_type=source_type,
        source_id=source_id,
    )

    gam, _ = StudentGamification.objects.get_or_create(student=student)
    StudentGamification.objects.filter(pk=gam.pk).update(
        total_xp=F("total_xp") + amount,
    )
    gam.refresh_from_db()
    gam.current_level = max(1, math.floor(math.sqrt(gam.total_xp / 100)))
    gam.save(update_fields=["current_level"])

    return tx
```

- [ ] **Step 4: Run tests**

Run: `cd ~/classedge && env/bin/python manage.py test gamification.tests.test_services --keepdb -v2`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/classedge && git add gamification/services.py gamification/tests/test_services.py
git commit -m "feat(gamification): add XP award service with level calculation"
```

---

## Task 3: Streak Engine

**Files:**
- Create: `gamification/streaks.py`
- Create: `gamification/tests/test_streaks.py`

- [ ] **Step 1: Write streak tests**

Create `gamification/tests/test_streaks.py`:
```python
from datetime import date, timedelta

from django.test import TestCase

from ai_content.tests.test_models import _create_test_user
from gamification.models import StudentGamification
from gamification.streaks import (
    update_accuracy_streak,
    update_login_streak,
    update_submission_streak,
)


class LoginStreakTests(TestCase):
    def setUp(self):
        self.student = _create_test_user(username="streak_stu", role_name="student")
        self.gam = StudentGamification.objects.create(student=self.student)

    def test_first_login_sets_streak_to_1(self):
        update_login_streak(self.student)
        self.gam.refresh_from_db()
        self.assertEqual(self.gam.login_streak, 1)
        self.assertEqual(self.gam.last_active_date, date.today())

    def test_consecutive_day_increments(self):
        yesterday = date.today() - timedelta(days=1)
        self.gam.login_streak = 5
        self.gam.last_active_date = yesterday
        self.gam.save()

        update_login_streak(self.student)
        self.gam.refresh_from_db()
        self.assertEqual(self.gam.login_streak, 6)

    def test_same_day_no_op(self):
        self.gam.login_streak = 5
        self.gam.last_active_date = date.today()
        self.gam.save()

        update_login_streak(self.student)
        self.gam.refresh_from_db()
        self.assertEqual(self.gam.login_streak, 5)

    def test_gap_resets_streak(self):
        two_days_ago = date.today() - timedelta(days=2)
        self.gam.login_streak = 10
        self.gam.last_active_date = two_days_ago
        self.gam.streak_freezes_available = 0
        self.gam.save()

        update_login_streak(self.student)
        self.gam.refresh_from_db()
        self.assertEqual(self.gam.login_streak, 1)

    def test_freeze_preserves_streak_on_one_day_gap(self):
        two_days_ago = date.today() - timedelta(days=2)
        self.gam.login_streak = 10
        self.gam.last_active_date = two_days_ago
        self.gam.streak_freezes_available = 1
        self.gam.save()

        update_login_streak(self.student)
        self.gam.refresh_from_db()
        self.assertEqual(self.gam.login_streak, 11)
        self.assertEqual(self.gam.streak_freezes_available, 0)


class SubmissionStreakTests(TestCase):
    def setUp(self):
        self.student = _create_test_user(username="sub_streak", role_name="student")
        self.gam = StudentGamification.objects.create(
            student=self.student, submission_streak=5,
        )

    def test_on_time_increments(self):
        update_submission_streak(self.student, is_on_time=True)
        self.gam.refresh_from_db()
        self.assertEqual(self.gam.submission_streak, 6)

    def test_late_resets(self):
        update_submission_streak(self.student, is_on_time=False)
        self.gam.refresh_from_db()
        self.assertEqual(self.gam.submission_streak, 0)


class AccuracyStreakTests(TestCase):
    def setUp(self):
        self.student = _create_test_user(username="acc_streak", role_name="student")
        self.gam = StudentGamification.objects.create(
            student=self.student, accuracy_streak=3,
        )

    def test_high_score_increments(self):
        update_accuracy_streak(self.student, score_pct=85.0)
        self.gam.refresh_from_db()
        self.assertEqual(self.gam.accuracy_streak, 4)

    def test_low_score_resets(self):
        update_accuracy_streak(self.student, score_pct=70.0)
        self.gam.refresh_from_db()
        self.assertEqual(self.gam.accuracy_streak, 0)

    def test_exactly_80_increments(self):
        update_accuracy_streak(self.student, score_pct=80.0)
        self.gam.refresh_from_db()
        self.assertEqual(self.gam.accuracy_streak, 4)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/classedge && env/bin/python manage.py test gamification.tests.test_streaks --keepdb -v2 2>&1 | tail -10`
Expected: ImportError

- [ ] **Step 3: Write the streak engine**

Create `gamification/streaks.py`:
```python
from datetime import date, timedelta

from gamification.models import StudentGamification


def update_login_streak(student):
    """Update login streak for the student. Call on each login."""
    gam = StudentGamification.objects.select_for_update().get(student=student)
    today = date.today()

    if gam.last_active_date == today:
        return  # already logged in today

    if gam.last_active_date == today - timedelta(days=1):
        gam.login_streak += 1
    elif (
        gam.last_active_date == today - timedelta(days=2)
        and gam.streak_freezes_available > 0
    ):
        gam.login_streak += 1
        gam.streak_freezes_available -= 1
    else:
        gam.login_streak = 1

    gam.last_active_date = today
    gam.save(update_fields=[
        "login_streak", "last_active_date", "streak_freezes_available",
    ])


def update_submission_streak(student, is_on_time):
    """Update submission streak. Call on each activity submission."""
    gam, _ = StudentGamification.objects.get_or_create(student=student)
    if is_on_time:
        gam.submission_streak += 1
    else:
        gam.submission_streak = 0
    gam.save(update_fields=["submission_streak"])


def update_accuracy_streak(student, score_pct):
    """Update accuracy streak. Call after each graded activity score."""
    gam, _ = StudentGamification.objects.get_or_create(student=student)
    if score_pct >= 80:
        gam.accuracy_streak += 1
    else:
        gam.accuracy_streak = 0
    gam.save(update_fields=["accuracy_streak"])
```

- [ ] **Step 4: Run tests**

Run: `cd ~/classedge && env/bin/python manage.py test gamification.tests.test_streaks --keepdb -v2`
Expected: All 10 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/classedge && git add gamification/streaks.py gamification/tests/test_streaks.py
git commit -m "feat(gamification): add streak engine (login, submission, accuracy)"
```

---

## Task 4: Badge Evaluation Engine + Seed Data

**Files:**
- Create: `gamification/badges.py`
- Create: `gamification/tests/test_badges.py`
- Create: `gamification/migrations/0002_seed_badges.py`

- [ ] **Step 1: Write badge tests**

Create `gamification/tests/test_badges.py`:
```python
from django.test import TestCase

from ai_content.tests.test_models import _create_test_user
from gamification.badges import evaluate_badges
from gamification.models import (
    BadgeDefinition,
    StudentBadge,
    StudentGamification,
    XPTransaction,
)


class BadgeEvaluatorTests(TestCase):
    def setUp(self):
        self.student = _create_test_user(username="badge_eval", role_name="student")
        self.gam = StudentGamification.objects.create(
            student=self.student, total_xp=0, current_level=1,
        )

    def test_xp_total_awards_badge(self):
        badge = BadgeDefinition.objects.create(
            code="xp_test",
            name="XP Test",
            description="desc",
            tier="bronze",
            icon="🏅",
            criteria_json={"type": "xp_total", "threshold": 100},
        )
        self.gam.total_xp = 150
        self.gam.save()

        evaluate_badges(self.student)
        self.assertTrue(
            StudentBadge.objects.filter(student=self.student, badge=badge).exists()
        )

    def test_xp_total_not_met(self):
        BadgeDefinition.objects.create(
            code="xp_not_met",
            name="Not Met",
            description="desc",
            tier="bronze",
            icon="🏅",
            criteria_json={"type": "xp_total", "threshold": 1000},
        )
        self.gam.total_xp = 50
        self.gam.save()

        evaluate_badges(self.student)
        self.assertEqual(StudentBadge.objects.count(), 0)

    def test_streak_evaluator(self):
        badge = BadgeDefinition.objects.create(
            code="streak_test",
            name="Streak Test",
            description="desc",
            tier="silver",
            icon="🔥",
            criteria_json={"type": "streak", "streak": "login", "threshold": 7},
        )
        self.gam.login_streak = 10
        self.gam.save()

        evaluate_badges(self.student)
        self.assertTrue(
            StudentBadge.objects.filter(student=self.student, badge=badge).exists()
        )

    def test_level_evaluator(self):
        badge = BadgeDefinition.objects.create(
            code="level_test",
            name="Level Test",
            description="desc",
            tier="gold",
            icon="⭐",
            criteria_json={"type": "level", "threshold": 5},
        )
        self.gam.current_level = 7
        self.gam.save()

        evaluate_badges(self.student)
        self.assertTrue(
            StudentBadge.objects.filter(student=self.student, badge=badge).exists()
        )

    def test_badges_earned_evaluator(self):
        # Give the student 3 badges first
        for i in range(3):
            b = BadgeDefinition.objects.create(
                code=f"filler_{i}",
                name=f"Filler {i}",
                description="desc",
                tier="bronze",
                icon="🏅",
                criteria_json={},
            )
            StudentBadge.objects.create(student=self.student, badge=b)

        collector = BadgeDefinition.objects.create(
            code="collector_test",
            name="Collector",
            description="desc",
            tier="silver",
            icon="💎",
            criteria_json={"type": "badges_earned", "threshold": 3},
        )

        evaluate_badges(self.student)
        self.assertTrue(
            StudentBadge.objects.filter(
                student=self.student, badge=collector,
            ).exists()
        )

    def test_activity_score_evaluator(self):
        from activity.models.activity_model import Activity, ActivityType
        from activity.models.student_activity_model import StudentActivity
        from course.models.semester_model import Semester
        from course.models.term_model import Term
        from ai_content.tests.test_models import _create_subject
        from datetime import date

        subject = _create_subject()
        semester = Semester.objects.create(
            semester_name="Sem",
            start_date=date(2026, 1, 1),
            end_date=date(2027, 12, 31),
        )
        term = Term.objects.create(
            term_name="Prelim",
            semester=semester,
            start_date=date(2026, 8, 15),
            end_date=date(2026, 10, 15),
        )
        quiz_type, _ = ActivityType.objects.get_or_create(name="Quiz")

        # Create 3 activities with 90%+ scores
        for i in range(3):
            act = Activity.objects.create(
                activity_name=f"Quiz {i}",
                activity_type=quiz_type,
                subject=subject,
                term=term,
                max_score=100,
                is_graded=True,
            )
            StudentActivity.objects.create(
                student=self.student,
                activity=act,
                subject=subject,
                term=term,
                total_score=95,
            )

        badge = BadgeDefinition.objects.create(
            code="score_test",
            name="Sharpshooter",
            description="desc",
            tier="silver",
            icon="🎯",
            criteria_json={"type": "activity_score", "min_pct": 90, "count": 3},
        )

        evaluate_badges(self.student)
        self.assertTrue(
            StudentBadge.objects.filter(student=self.student, badge=badge).exists()
        )

    def test_already_earned_not_re_evaluated(self):
        badge = BadgeDefinition.objects.create(
            code="already_earned",
            name="Already",
            description="desc",
            tier="bronze",
            icon="🏅",
            criteria_json={"type": "xp_total", "threshold": 10},
        )
        self.gam.total_xp = 100
        self.gam.save()
        StudentBadge.objects.create(student=self.student, badge=badge)

        # Should not raise or create duplicate
        evaluate_badges(self.student)
        self.assertEqual(
            StudentBadge.objects.filter(student=self.student, badge=badge).count(), 1,
        )

    def test_empty_criteria_not_auto_awarded(self):
        BadgeDefinition.objects.create(
            code="teacher_only",
            name="Honor Roll",
            description="desc",
            tier="platinum",
            icon="🏆",
            criteria_json={},
        )
        evaluate_badges(self.student)
        self.assertEqual(StudentBadge.objects.count(), 0)


class SeedBadgesTests(TestCase):
    def test_starter_badges_exist(self):
        from django.core.management import call_command
        # The seed migration runs during test DB setup.
        # Verify the 15 starter badges are present.
        self.assertEqual(BadgeDefinition.objects.count(), 15)

    def test_all_codes_unique(self):
        codes = list(BadgeDefinition.objects.values_list("code", flat=True))
        self.assertEqual(len(codes), len(set(codes)))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/classedge && env/bin/python manage.py test gamification.tests.test_badges --keepdb -v2 2>&1 | tail -10`
Expected: ImportError

- [ ] **Step 3: Write the badge evaluation engine**

Create `gamification/badges.py`:
```python
from activity.models.student_activity_model import StudentActivity
from gamification.models import BadgeDefinition, StudentBadge, StudentGamification


def evaluate_badges(student):
    """Check all active badges the student hasn't earned yet and award any whose criteria are met."""
    earned_badge_ids = set(
        StudentBadge.objects.filter(student=student).values_list("badge_id", flat=True)
    )
    candidates = BadgeDefinition.objects.filter(
        is_active=True, target_role="student",
    ).exclude(pk__in=earned_badge_ids)

    gam = StudentGamification.objects.filter(student=student).first()
    if not gam:
        return

    for badge in candidates:
        criteria = badge.criteria_json
        if not criteria or "type" not in criteria:
            continue

        evaluator = EVALUATORS.get(criteria["type"])
        if evaluator and evaluator(student, gam, criteria):
            StudentBadge.objects.create(student=student, badge=badge)


def _eval_xp_total(student, gam, criteria):
    return gam.total_xp >= criteria["threshold"]


def _eval_streak(student, gam, criteria):
    streak_field = criteria["streak"]  # "login", "submission", or "accuracy"
    current = getattr(gam, f"{streak_field}_streak", 0)
    return current >= criteria["threshold"]


def _eval_level(student, gam, criteria):
    return gam.current_level >= criteria["threshold"]


def _eval_badges_earned(student, gam, criteria):
    count = StudentBadge.objects.filter(student=student).count()
    return count >= criteria["threshold"]


def _eval_activity_score(student, gam, criteria):
    min_pct = criteria["min_pct"] / 100.0
    count_needed = criteria["count"]

    qualifying = 0
    for sa in StudentActivity.objects.filter(
        student=student,
        activity__is_graded=True,
        activity__max_score__gt=0,
    ).select_related("activity"):
        if sa.total_score / sa.activity.max_score >= min_pct:
            qualifying += 1
            if qualifying >= count_needed:
                return True
    return False


EVALUATORS = {
    "xp_total": _eval_xp_total,
    "streak": _eval_streak,
    "level": _eval_level,
    "badges_earned": _eval_badges_earned,
    "activity_score": _eval_activity_score,
}
```

- [ ] **Step 4: Create the seed migration**

Create `gamification/migrations/0002_seed_badges.py`:
```python
from django.db import migrations

STARTER_BADGES = [
    ("first_login", "First Login", "Earn your first XP", "bronze", "👋", {"type": "xp_total", "threshold": 5}),
    ("week_warrior", "Week Warrior", "7-day login streak", "silver", "🔥", {"type": "streak", "streak": "login", "threshold": 7}),
    ("month_master", "Month Master", "30-day login streak", "gold", "🌟", {"type": "streak", "streak": "login", "threshold": 30}),
    ("sharpshooter", "Sharpshooter", "Score 90%+ on 5 activities", "silver", "🎯", {"type": "activity_score", "min_pct": 90, "count": 5}),
    ("perfect_score", "Perfect Score", "Score 100% on any activity", "gold", "💯", {"type": "activity_score", "min_pct": 100, "count": 1}),
    ("bookworm", "Bookworm", "Earn 2,500 XP", "silver", "📚", {"type": "xp_total", "threshold": 2500}),
    ("scholar", "Scholar", "Earn 10,000 XP", "platinum", "🎓", {"type": "xp_total", "threshold": 10000}),
    ("on_fire", "On Fire", "10 on-time submissions in a row", "silver", "⚡", {"type": "streak", "streak": "submission", "threshold": 10}),
    ("consistent", "Consistent", "20 activities at 80%+ in a row", "gold", "🎯", {"type": "streak", "streak": "accuracy", "threshold": 20}),
    ("level_5", "Rising Star", "Reach level 5", "bronze", "🌱", {"type": "level", "threshold": 5}),
    ("level_10", "Veteran", "Reach level 10", "silver", "🛡️", {"type": "level", "threshold": 10}),
    ("level_20", "Legend", "Reach level 20", "gold", "👑", {"type": "level", "threshold": 20}),
    ("collector", "Collector", "Earn 10 badges", "silver", "💎", {"type": "badges_earned", "threshold": 10}),
    ("honor_roll", "Honor Roll", "Awarded by teacher for excellence", "platinum", "🏆", {}),
    ("early_bird", "Early Bird", "Earn 100 XP", "bronze", "🌅", {"type": "xp_total", "threshold": 100}),
]


def seed_badges(apps, schema_editor):
    BadgeDefinition = apps.get_model("gamification", "BadgeDefinition")
    for code, name, desc, tier, icon, criteria in STARTER_BADGES:
        BadgeDefinition.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "description": desc,
                "tier": tier,
                "icon": icon,
                "criteria_json": criteria,
            },
        )


def reverse_seed(apps, schema_editor):
    BadgeDefinition = apps.get_model("gamification", "BadgeDefinition")
    codes = [b[0] for b in STARTER_BADGES]
    BadgeDefinition.objects.filter(code__in=codes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("gamification", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_badges, reverse_seed),
    ]
```

- [ ] **Step 5: Apply migration**

Run:
```bash
cd ~/classedge && env/bin/python manage.py migrate gamification 2>&1 | tail -5
```
Expected: `0002_seed_badges` applied.

- [ ] **Step 6: Run badge tests**

Run: `cd ~/classedge && env/bin/python manage.py test gamification.tests.test_badges --keepdb -v2`
Expected: All 10 tests PASS

- [ ] **Step 7: Commit**

```bash
cd ~/classedge && git add gamification/badges.py gamification/tests/test_badges.py gamification/migrations/0002_seed_badges.py
git commit -m "feat(gamification): add badge evaluation engine with 15 starter badges"
```

---

## Task 5: Signal Handlers

**Files:**
- Modify: `gamification/signals.py`
- Create: `gamification/tests/test_signals.py`

- [ ] **Step 1: Write signal tests**

Create `gamification/tests/test_signals.py`:
```python
from datetime import date, timedelta

from django.contrib.auth.signals import user_logged_in
from django.test import TestCase, RequestFactory, override_settings

from ai_content.tests.test_models import _create_test_user, _create_subject
from activity.models.activity_model import Activity, ActivityType
from activity.models.student_activity_model import StudentActivity
from course.models.semester_model import Semester
from course.models.term_model import Term
from course.models.attendance_model import Attendance, AttendanceStatus
from course.models.subject_enrollment_model import SubjectEnrollment
from gamification.models import StudentGamification, XPTransaction

_GAM_SETTINGS = {
    "GAMIFICATION_XP_RATES": {
        "submission": 50,
        "early_submission": 75,
        "score_90": 30,
        "score_75": 15,
        "daily_login": 5,
        "perfect_attendance_week": 50,
    },
    "GAMIFICATION_STREAK_FREEZE_MONTHLY": 1,
}


@override_settings(**_GAM_SETTINGS)
class ActivitySignalTests(TestCase):
    def setUp(self):
        self.student = _create_test_user(username="sig_student", role_name="student")
        self.subject = _create_subject()
        self.semester = Semester.objects.create(
            semester_name="Sem",
            start_date=date(2026, 1, 1),
            end_date=date(2027, 12, 31),
        )
        self.term = Term.objects.create(
            term_name="Prelim",
            semester=self.semester,
            start_date=date(2026, 8, 15),
            end_date=date(2026, 10, 15),
        )
        self.quiz_type, _ = ActivityType.objects.get_or_create(name="Quiz")

    def test_submission_awards_xp(self):
        activity = Activity.objects.create(
            activity_name="Quiz 1",
            activity_type=self.quiz_type,
            subject=self.subject,
            term=self.term,
            max_score=100,
            is_graded=True,
        )
        StudentActivity.objects.create(
            student=self.student,
            activity=activity,
            subject=self.subject,
            term=self.term,
            total_score=60,
        )
        tx = XPTransaction.objects.filter(
            student=self.student, source_type="activity",
        )
        self.assertTrue(tx.exists())

    def test_high_score_awards_bonus(self):
        activity = Activity.objects.create(
            activity_name="Quiz 2",
            activity_type=self.quiz_type,
            subject=self.subject,
            term=self.term,
            max_score=100,
            is_graded=True,
        )
        StudentActivity.objects.create(
            student=self.student,
            activity=activity,
            subject=self.subject,
            term=self.term,
            total_score=95,
        )
        score_tx = XPTransaction.objects.filter(
            student=self.student, source_type="activity_score_90",
        )
        self.assertTrue(score_tx.exists())

    def test_no_double_award_on_update(self):
        activity = Activity.objects.create(
            activity_name="Quiz 3",
            activity_type=self.quiz_type,
            subject=self.subject,
            term=self.term,
            max_score=100,
            is_graded=True,
        )
        sa = StudentActivity.objects.create(
            student=self.student,
            activity=activity,
            subject=self.subject,
            term=self.term,
            total_score=50,
        )
        count_before = XPTransaction.objects.filter(
            student=self.student, source_type="activity",
        ).count()

        sa.total_score = 60
        sa.save()

        count_after = XPTransaction.objects.filter(
            student=self.student, source_type="activity",
        ).count()
        self.assertEqual(count_before, count_after)


@override_settings(**_GAM_SETTINGS)
class LoginSignalTests(TestCase):
    def setUp(self):
        self.student = _create_test_user(username="sig_login", role_name="student")
        self.factory = RequestFactory()

    def test_login_awards_xp(self):
        request = self.factory.get("/")
        request.session = {}
        user_logged_in.send(
            sender=self.student.__class__,
            request=request,
            user=self.student,
        )
        tx = XPTransaction.objects.filter(
            student=self.student, source_type="login",
        )
        self.assertTrue(tx.exists())

    def test_second_login_same_day_no_double(self):
        request = self.factory.get("/")
        request.session = {}
        user_logged_in.send(
            sender=self.student.__class__,
            request=request,
            user=self.student,
        )
        user_logged_in.send(
            sender=self.student.__class__,
            request=request,
            user=self.student,
        )
        count = XPTransaction.objects.filter(
            student=self.student, source_type="login",
        ).count()
        self.assertEqual(count, 1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/classedge && env/bin/python manage.py test gamification.tests.test_signals --keepdb -v2 2>&1 | tail -10`
Expected: Failures (signals not wired yet)

- [ ] **Step 3: Write the signal handlers**

Replace `gamification/signals.py` with:
```python
from datetime import date

from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver

from activity.models.student_activity_model import StudentActivity
from gamification.models import StudentGamification
from gamification.services import award_xp
from gamification.streaks import (
    update_accuracy_streak,
    update_login_streak,
    update_submission_streak,
)


@receiver(post_save, sender=StudentActivity)
def on_student_activity_save(sender, instance, created, **kwargs):
    if not created:
        return

    student = instance.student
    if not student:
        return

    rates = settings.GAMIFICATION_XP_RATES

    # Submission XP
    xp = rates["submission"]
    if instance.term and instance.term.end_date:
        days_early = (instance.term.end_date - date.today()).days
        if days_early > 1:
            xp = rates["early_submission"]

    award_xp(student, xp, "Assignment submitted", "activity", source_id=instance.pk)

    # Submission streak (consider all submissions on-time for now)
    is_on_time = True
    if instance.term and instance.term.end_date:
        is_on_time = date.today() <= instance.term.end_date
    update_submission_streak(student, is_on_time)

    # Score-based XP
    activity = instance.activity
    if activity and activity.max_score and activity.max_score > 0:
        score_pct = (instance.total_score / activity.max_score) * 100

        if score_pct >= 90:
            award_xp(
                student, rates["score_90"], "Score >=90%",
                "activity_score_90", source_id=instance.pk,
            )
        elif score_pct >= 75:
            award_xp(
                student, rates["score_75"], "Score >=75%",
                "activity_score_75", source_id=instance.pk,
            )

        # Accuracy streak
        update_accuracy_streak(student, score_pct)


@receiver(user_logged_in)
def on_user_login(sender, request, user, **kwargs):
    rates = settings.GAMIFICATION_XP_RATES

    gam, _ = StudentGamification.objects.get_or_create(student=user)

    if gam.last_active_date == date.today():
        return  # already awarded today

    award_xp(
        user, rates["daily_login"], "Daily login",
        "login", source_id=date.today().toordinal(),
    )
    update_login_streak(user)
```

- [ ] **Step 4: Run signal tests**

Run: `cd ~/classedge && env/bin/python manage.py test gamification.tests.test_signals --keepdb -v2`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/classedge && git add gamification/signals.py gamification/tests/test_signals.py
git commit -m "feat(gamification): wire XP signals to StudentActivity and login"
```

---

## Task 6: Streak Freeze Management Command

**Files:**
- Create: `gamification/management/__init__.py`
- Create: `gamification/management/commands/__init__.py`
- Create: `gamification/management/commands/reset_streak_freezes.py`

- [ ] **Step 1: Create the management command**

Create `gamification/management/__init__.py` (empty).
Create `gamification/management/commands/__init__.py` (empty).

Create `gamification/management/commands/reset_streak_freezes.py`:
```python
from django.conf import settings
from django.core.management.base import BaseCommand

from gamification.models import StudentGamification


class Command(BaseCommand):
    help = "Reset streak freezes to the monthly allowance for all students."

    def handle(self, *args, **options):
        monthly = getattr(settings, "GAMIFICATION_STREAK_FREEZE_MONTHLY", 1)
        updated = StudentGamification.objects.update(
            streak_freezes_available=monthly,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Reset streak freezes to {monthly} for {updated} students.",
            )
        )
```

- [ ] **Step 2: Test the command**

Run:
```bash
cd ~/classedge && env/bin/python manage.py reset_streak_freezes
```
Expected: `Reset streak freezes to 1 for N students.`

- [ ] **Step 3: Commit**

```bash
cd ~/classedge && git add gamification/management/
git commit -m "feat(gamification): add reset_streak_freezes management command"
```

---

## Task 7: Legacy Badge Migration + Cleanup

**Files:**
- Create: `gamification/migrations/0003_migrate_legacy_badges.py`
- Modify: `accounts/models/__init__.py`
- Modify: `accounts/views/__init__.py`
- Modify: `accounts/urls.py`
- Delete: `accounts/models/badge_models.py`
- Delete: `accounts/views/badge_views.py`
- Delete: `accounts/forms/badge_forms.py`
- Delete: `accounts/templates/accounts/badge/`

- [ ] **Step 1: Create the legacy migration**

Create `gamification/migrations/0003_migrate_legacy_badges.py`:
```python
from django.db import migrations


def migrate_legacy_badges(apps, schema_editor):
    OldBadge = apps.get_model("accounts", "Badge")
    BadgeDefinition = apps.get_model("gamification", "BadgeDefinition")
    StudentBadge = apps.get_model("gamification", "StudentBadge")
    Profile = apps.get_model("accounts", "Profile")

    for old_badge in OldBadge.objects.all():
        new_def, _ = BadgeDefinition.objects.get_or_create(
            code=f"legacy_{old_badge.pk}",
            defaults={
                "name": old_badge.name,
                "description": old_badge.description or "",
                "tier": "bronze",
                "icon": "🏅",
                "criteria_json": {},
                "is_active": True,
            },
        )
        for profile in old_badge.profiles.all():
            if profile.user_id:
                StudentBadge.objects.get_or_create(
                    student_id=profile.user_id,
                    badge=new_def,
                    defaults={
                        "award_reason": "Migrated from legacy badge system",
                    },
                )


def reverse_migration(apps, schema_editor):
    BadgeDefinition = apps.get_model("gamification", "BadgeDefinition")
    BadgeDefinition.objects.filter(code__startswith="legacy_").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("gamification", "0002_seed_badges"),
        ("accounts", "__latest__"),
    ]

    operations = [
        migrations.RunPython(migrate_legacy_badges, reverse_migration),
    ]
```

- [ ] **Step 2: Apply migration**

Run:
```bash
cd ~/classedge && env/bin/python manage.py migrate gamification 2>&1 | tail -5
```
Expected: `0003_migrate_legacy_badges` applied.

- [ ] **Step 3: Remove old badge code from accounts**

Remove badge imports from `accounts/models/__init__.py` — change:
```python
from .badge_models import Badge, badge_upload_path
```
to nothing (delete the line).

Remove from `__all__`:
```python
    #Badge models
    "Badge", "badge_upload_path",
```

Remove from `accounts/views/__init__.py`:
```python
from .badge_views import *
```

And from the `__all__` list:
```python
    # Badge views
    "badge_list", "create_badge", "update_badge", "delete_badge",
```

Remove badge URL patterns from `accounts/urls.py` (lines 90-93):
```python
    path('badge_list/', badge_list, name='badge_list'),
    path('create_badge/', create_badge, name='create_badge'),
    path('update_badge/<int:id>/', update_badge, name='update_badge'),
    path('delete_badge/<int:id>/', delete_badge, name='delete_badge'),
```

Delete the files:
```bash
rm accounts/models/badge_models.py
rm accounts/views/badge_views.py
rm accounts/forms/badge_forms.py
rm -rf accounts/templates/accounts/badge/
```

- [ ] **Step 4: Run Django system check**

Run: `cd ~/classedge && env/bin/python manage.py check 2>&1`
Expected: `System check identified no issues.`

If there are import errors, fix any remaining references to the old Badge model.

- [ ] **Step 5: Commit**

```bash
cd ~/classedge && git add -A
git commit -m "feat(gamification): migrate legacy badges and remove old badge code"
```

---

## Task 8: Wire Badge Evaluation Into XP Service + Full Integration Test

**Files:**
- Modify: `gamification/services.py`

- [ ] **Step 1: Add badge evaluation call to award_xp**

In `gamification/services.py`, add the import at the top:
```python
from gamification.badges import evaluate_badges
```

Add at the end of `award_xp`, before `return tx`:
```python
    evaluate_badges(student)
```

- [ ] **Step 2: Run the full gamification test suite**

Run:
```bash
cd ~/classedge && env/bin/python manage.py test gamification --keepdb -v2 2>&1 | tail -20
```
Expected: All tests PASS (~32 tests)

- [ ] **Step 3: Run the broader test suite for regressions**

Run:
```bash
cd ~/classedge && env/bin/python manage.py test gamification at_risk rag_tutor ai_content accounts --keepdb 2>&1 | tail -10
```
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
cd ~/classedge && git add gamification/services.py
git commit -m "feat(gamification): wire badge evaluation into XP award pipeline"
```

---

## Summary

| Task | What it builds | Tests |
|------|---------------|-------|
| 1 | App scaffold + 4 models | 7 |
| 2 | XP award service + level calc | 7 |
| 3 | Streak engine (login, submission, accuracy) | 10 |
| 4 | Badge evaluation engine + 15 starter badges | 10 |
| 5 | Signal handlers (StudentActivity, login) | 5 |
| 6 | Streak freeze management command | — |
| 7 | Legacy badge migration + cleanup | — |
| 8 | Wire badge eval into XP + integration | — |

**Total new tests: ~39**

**Deferred from spec:** Perfect attendance week signal (`+50 XP`) requires
week-boundary logic against the Attendance model which varies by subject
schedule. This will be added as a follow-up once the core engine is proven.
