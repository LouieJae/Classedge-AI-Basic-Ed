# Teacher Dashboard SP2: Teacher Gamification Engine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Impact Points, tiered ranks, teacher badges, challenges, recognition shoutouts, and star ratings to the teacher dashboard.

**Architecture:** 8 new models in `gamification/teacher_models.py`, parallel service/badge layers (`teacher_services.py`, `teacher_badges.py`), signals for auto-awarding IP, management commands for seeding and challenge assignment, AJAX endpoints for recognition/ratings, and template fragments included in the existing teacher dashboard.

**Tech Stack:** Django 5.0.7, PostgreSQL, DRF patterns (but plain Django views), existing test helpers from `ai_content/tests/test_models.py`.

**Test DB:** Always use `--keepdb` flag. Test database is `test_neondb`.

**Test helpers:** `_create_test_user(username, role_name)` and `_create_subject()` from `ai_content.tests.test_models`.

---

## File Structure

### New Files

| File | Responsibility |
|------|---------------|
| `gamification/teacher_models.py` | 8 models: TeacherGamification, IPTransaction, TeacherBadgeDefinition, TeacherBadge, TeacherChallenge, TeacherChallengeProgress, TeacherRecognition, TeacherRating |
| `gamification/teacher_services.py` | `award_ip()`, `recalculate_rank()`, `evaluate_teacher_challenges()` |
| `gamification/teacher_badges.py` | 8 evaluators, 8 progress computers, `evaluate_teacher_badges()`, `compute_teacher_badge_progress()` |
| `gamification/teacher_views.py` | AJAX endpoints: `send_recognition()`, `submit_rating()` |
| `gamification/management/commands/seed_teacher_badges.py` | Seed 8 teacher badge definitions |
| `gamification/management/commands/seed_teacher_challenges.py` | Seed 10 challenge definitions |
| `gamification/management/commands/assign_weekly_challenges.py` | Auto-assign 2 weekly challenges per teacher |
| `gamification/management/commands/assign_monthly_challenges.py` | Auto-assign 1 monthly challenge per teacher |
| `gamification/tests/test_teacher_gamification.py` | 18 tests covering all SP2 features |
| `gamification/templates/gamification/teacher_challenges.html` | Challenges section fragment |
| `gamification/templates/gamification/teacher_badges_shelf.html` | Badge shelf fragment |
| `gamification/templates/gamification/teacher_recognition_modal.html` | Recognition modal fragment |

### Modified Files

| File | Changes |
|------|---------|
| `gamification/models.py` | Add import line for teacher_models |
| `gamification/signals.py` | Add 2 signal handlers for IP awards |
| `gamification/urls.py` | Add 2 URL patterns for recognition/rating |
| `gamification/teacher_dashboard.py` | Add rank, challenges, badges, rating data to context |
| `gamification/templates/gamification/teacher_dashboard.html` | Add 3 include blocks + update growth/spotlight sections |
| `templates/teacher_base.html` | Add "My Progress" sidebar nav item |
| `gamification/templates/gamification/student_dashboard.html` | Add recognition display + rating card sections |
| `gamification/views.py` | Import student dashboard recognition data |

---

### Task 1: Models + Migration

**Files:**
- Create: `gamification/teacher_models.py`
- Modify: `gamification/models.py`

- [ ] **Step 1: Create teacher_models.py with all 8 models**

```python
# gamification/teacher_models.py
from django.conf import settings
from django.db import models


class TeacherGamification(models.Model):
    teacher = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="teacher_gamification",
    )
    total_ip = models.PositiveIntegerField(default=0)
    current_rank = models.CharField(max_length=30, default="bronze_mentor")
    rank_tier = models.CharField(max_length=20, default="bronze")
    rank_title = models.CharField(max_length=30, default="Mentor")

    class Meta:
        indexes = [
            models.Index(fields=["-total_ip"], name="gam_teacher_ip_idx"),
        ]

    def __str__(self):
        return f"{self.teacher} — {self.rank_tier} {self.rank_title} ({self.total_ip} IP)"


class IPTransaction(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ip_transactions",
    )
    amount = models.IntegerField()
    reason = models.CharField(max_length=100)
    source_type = models.CharField(max_length=50)
    source_id = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["teacher", "created_at"], name="gam_ip_teacher_date_idx"),
            models.Index(fields=["source_type", "source_id"], name="gam_ip_src_idx"),
        ]

    def __str__(self):
        return f"{self.teacher} {self.amount:+d} IP — {self.reason}"


class TeacherBadgeDefinition(models.Model):
    TIER_CHOICES = [
        ("bronze", "Bronze"),
        ("silver", "Silver"),
        ("gold", "Gold"),
        ("platinum", "Platinum"),
    ]

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    tier = models.CharField(max_length=20, choices=TIER_CHOICES)
    icon = models.CharField(max_length=50)
    criteria_json = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"[{self.tier}] {self.name}"


class TeacherBadge(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="earned_teacher_badges",
    )
    badge = models.ForeignKey(
        TeacherBadgeDefinition,
        on_delete=models.CASCADE,
    )
    earned_at = models.DateTimeField(auto_now_add=True)
    progress_percent = models.PositiveSmallIntegerField(default=100)

    class Meta:
        unique_together = [("teacher", "badge")]

    def __str__(self):
        return f"{self.teacher} earned {self.badge.name}"


class TeacherChallenge(models.Model):
    CHALLENGE_TYPE_CHOICES = [
        ("rotating", "Rotating"),
        ("milestone", "Milestone"),
    ]

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    challenge_type = models.CharField(max_length=20, choices=CHALLENGE_TYPE_CHOICES)
    criteria_json = models.JSONField(default=dict)
    ip_reward = models.PositiveIntegerField()
    duration_days = models.PositiveSmallIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"[{self.challenge_type}] {self.name} ({self.ip_reward} IP)"


class TeacherChallengeProgress(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="challenge_progress",
    )
    challenge = models.ForeignKey(
        TeacherChallenge,
        on_delete=models.CASCADE,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    current_value = models.PositiveIntegerField(default=0)
    target_value = models.PositiveIntegerField()
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("teacher", "challenge", "started_at")]

    def __str__(self):
        status = "done" if self.completed_at else f"{self.current_value}/{self.target_value}"
        return f"{self.teacher} — {self.challenge.name} ({status})"


class TeacherRecognition(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recognitions_given",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recognitions_received",
    )
    message = models.CharField(max_length=300)
    xp_awarded = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.teacher} → {self.student}: {self.message[:50]}"


class TeacherRating(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ratings_received",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ratings_given",
    )
    stars = models.PositiveSmallIntegerField()
    semester = models.ForeignKey(
        "course.Semester",
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("teacher", "student", "semester")]

    def __str__(self):
        return f"{self.student} rated {self.teacher} {self.stars}★"
```

- [ ] **Step 2: Add import to models.py**

Add this line at the bottom of `gamification/models.py` (after the existing `from gamification.side_activity_models import ...` line):

```python
from gamification.teacher_models import (  # noqa: E402, F401
    TeacherGamification, IPTransaction, TeacherBadgeDefinition, TeacherBadge,
    TeacherChallenge, TeacherChallengeProgress, TeacherRecognition, TeacherRating,
)
```

- [ ] **Step 3: Generate and apply migration**

Run:
```bash
cd ~/classedge && ./env/bin/python manage.py makemigrations gamification --name teacher_gamification_models
```
Expected: Migration file created with 8 new models.

Run:
```bash
cd ~/classedge && ./env/bin/python manage.py migrate
```
Expected: Migration applied successfully.

- [ ] **Step 4: Commit**

```bash
cd ~/classedge
git add gamification/teacher_models.py gamification/models.py gamification/migrations/
git commit -m "feat(gamification): add 8 teacher gamification models

TeacherGamification, IPTransaction, TeacherBadgeDefinition, TeacherBadge,
TeacherChallenge, TeacherChallengeProgress, TeacherRecognition, TeacherRating."
```

---

### Task 2: Teacher Services (award_ip, recalculate_rank, evaluate_challenges)

**Files:**
- Create: `gamification/teacher_services.py`
- Test: `gamification/tests/test_teacher_gamification.py`

- [ ] **Step 1: Write failing tests for award_ip and rank**

Create `gamification/tests/test_teacher_gamification.py`:

```python
from datetime import date, timedelta
from django.test import TestCase, Client, override_settings
from django.utils import timezone

from ai_content.tests.test_models import _create_test_user, _create_subject
from gamification.teacher_models import (
    TeacherGamification, IPTransaction, TeacherBadgeDefinition, TeacherBadge,
    TeacherChallenge, TeacherChallengeProgress, TeacherRecognition, TeacherRating,
)

_GAM_SETTINGS = {
    "GAMIFICATION_XP_RATES": {
        "submission": 50, "early_submission": 75, "score_90": 30,
        "score_75": 15, "daily_login": 5, "perfect_attendance_week": 50,
    },
    "GAMIFICATION_STREAK_FREEZE_MONTHLY": 1,
    "AT_RISK_WEIGHTS": {"grade": 0.5, "completion": 0.3, "attendance": 0.2},
    "AT_RISK_HIGH_THRESHOLD": 40,
    "AT_RISK_MEDIUM_THRESHOLD": 65,
}


@override_settings(**_GAM_SETTINGS)
class AwardIPTests(TestCase):
    def setUp(self):
        self.teacher = _create_test_user(username="ip_teach", role_name="teacher")

    def test_award_ip_creates_transaction(self):
        from gamification.teacher_services import award_ip
        tx = award_ip(self.teacher, 10, "Test award", "test", source_id=1)
        self.assertIsNotNone(tx)
        self.assertEqual(tx.amount, 10)
        gam = TeacherGamification.objects.get(teacher=self.teacher)
        self.assertEqual(gam.total_ip, 10)

    def test_award_ip_dedup(self):
        from gamification.teacher_services import award_ip
        tx1 = award_ip(self.teacher, 10, "First", "test", source_id=99)
        tx2 = award_ip(self.teacher, 10, "Duplicate", "test", source_id=99)
        self.assertIsNotNone(tx1)
        self.assertIsNone(tx2)
        gam = TeacherGamification.objects.get(teacher=self.teacher)
        self.assertEqual(gam.total_ip, 10)

    def test_rank_progression(self):
        from gamification.teacher_services import award_ip
        # Start at bronze_mentor (0 IP)
        award_ip(self.teacher, 100, "Rank up", "test", source_id=1)
        gam = TeacherGamification.objects.get(teacher=self.teacher)
        self.assertEqual(gam.rank_tier, "bronze")
        self.assertEqual(gam.rank_title, "Guide")
        self.assertEqual(gam.current_rank, "bronze_guide")

        # Jump to silver_catalyst (300 IP)
        award_ip(self.teacher, 200, "Rank up", "test", source_id=2)
        gam.refresh_from_db()
        self.assertEqual(gam.rank_tier, "silver")
        self.assertEqual(gam.rank_title, "Catalyst")

        # Jump to gold_luminary (1200 IP)
        award_ip(self.teacher, 900, "Rank up", "test", source_id=3)
        gam.refresh_from_db()
        self.assertEqual(gam.rank_tier, "gold")
        self.assertEqual(gam.rank_title, "Luminary")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/classedge && ./env/bin/python manage.py test gamification.tests.test_teacher_gamification.AwardIPTests --keepdb -v2`
Expected: FAIL — `No module named 'gamification.teacher_services'`

- [ ] **Step 3: Implement teacher_services.py**

Create `gamification/teacher_services.py`:

```python
from django.db.models import F

from gamification.teacher_models import IPTransaction, TeacherGamification

RANK_THRESHOLDS = [
    (3500, "platinum", "Legend", "platinum_legend"),
    (2000, "gold", "Visionary", "gold_visionary"),
    (1200, "gold", "Luminary", "gold_luminary"),
    (600, "silver", "Architect", "silver_architect"),
    (300, "silver", "Catalyst", "silver_catalyst"),
    (100, "bronze", "Guide", "bronze_guide"),
    (0, "bronze", "Mentor", "bronze_mentor"),
]


def award_ip(teacher, amount, reason, source_type, source_id=None):
    """Award IP to a teacher. Returns IPTransaction or None if duplicate."""
    if source_id is not None:
        duplicate = IPTransaction.objects.filter(
            teacher=teacher, source_type=source_type, source_id=source_id,
        ).exists()
        if duplicate:
            return None

    tx = IPTransaction.objects.create(
        teacher=teacher, amount=amount, reason=reason,
        source_type=source_type, source_id=source_id,
    )

    gam, _ = TeacherGamification.objects.get_or_create(teacher=teacher)
    TeacherGamification.objects.filter(pk=gam.pk).update(total_ip=F("total_ip") + amount)
    gam.refresh_from_db()
    recalculate_rank(gam)

    from gamification.teacher_badges import evaluate_teacher_badges
    evaluate_teacher_badges(teacher)

    evaluate_teacher_challenges(teacher)

    return tx


def recalculate_rank(teacher_gam):
    """Map total_ip to rank tier + title using RANK_THRESHOLDS."""
    for threshold, tier, title, rank_code in RANK_THRESHOLDS:
        if teacher_gam.total_ip >= threshold:
            teacher_gam.current_rank = rank_code
            teacher_gam.rank_tier = tier
            teacher_gam.rank_title = title
            teacher_gam.save(update_fields=["current_rank", "rank_tier", "rank_title"])
            return


def next_rank_threshold(total_ip):
    """Return the IP needed for the next rank, or None if at max."""
    for threshold, _, _, _ in RANK_THRESHOLDS:
        if total_ip < threshold:
            return threshold
    return None


def evaluate_teacher_challenges(teacher):
    """Check all active challenges for the teacher. Complete any that hit target."""
    from gamification.teacher_models import TeacherChallengeProgress
    now = __import__("django.utils.timezone", fromlist=["now"]).now()

    active = TeacherChallengeProgress.objects.filter(
        teacher=teacher, completed_at__isnull=True,
    ).select_related("challenge")

    for progress in active:
        # Skip expired rotating challenges
        if progress.expires_at and progress.expires_at < now:
            continue
        if progress.current_value >= progress.target_value:
            progress.completed_at = now
            progress.save(update_fields=["completed_at"])
            # Award challenge bonus IP (avoid recursion by not calling award_ip)
            IPTransaction.objects.create(
                teacher=teacher, amount=progress.challenge.ip_reward,
                reason=f"Challenge complete: {progress.challenge.name}",
                source_type="challenge_reward",
                source_id=progress.pk,
            )
            gam = TeacherGamification.objects.get(teacher=teacher)
            TeacherGamification.objects.filter(pk=gam.pk).update(
                total_ip=F("total_ip") + progress.challenge.ip_reward,
            )
            gam.refresh_from_db()
            recalculate_rank(gam)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/classedge && ./env/bin/python manage.py test gamification.tests.test_teacher_gamification.AwardIPTests --keepdb -v2`
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/classedge
git add gamification/teacher_services.py gamification/tests/test_teacher_gamification.py
git commit -m "feat(gamification): add teacher IP award service with rank progression"
```

---

### Task 3: Teacher Badge Evaluators + Progress Computers

**Files:**
- Create: `gamification/teacher_badges.py`
- Modify: `gamification/tests/test_teacher_gamification.py`

- [ ] **Step 1: Add failing tests for badge evaluation and progress**

Append to `gamification/tests/test_teacher_gamification.py`:

```python
@override_settings(**_GAM_SETTINGS)
class TeacherBadgeTests(TestCase):
    def setUp(self):
        self.teacher = _create_test_user(username="tb_teach", role_name="teacher")
        TeacherGamification.objects.create(teacher=self.teacher, total_ip=15)

    def test_teacher_badge_evaluation(self):
        badge = TeacherBadgeDefinition.objects.create(
            code="first_impact", name="First Impact", description="Earn 10 IP",
            tier="bronze", icon="⚡", criteria_json={"type": "teacher_ip_total", "threshold": 10},
        )
        from gamification.teacher_badges import evaluate_teacher_badges
        evaluate_teacher_badges(self.teacher)
        self.assertTrue(TeacherBadge.objects.filter(teacher=self.teacher, badge=badge).exists())

    def test_teacher_badge_not_awarded_twice(self):
        badge = TeacherBadgeDefinition.objects.create(
            code="first_impact_2", name="First Impact", description="Earn 10 IP",
            tier="bronze", icon="⚡", criteria_json={"type": "teacher_ip_total", "threshold": 10},
        )
        from gamification.teacher_badges import evaluate_teacher_badges
        evaluate_teacher_badges(self.teacher)
        evaluate_teacher_badges(self.teacher)
        self.assertEqual(TeacherBadge.objects.filter(teacher=self.teacher, badge=badge).count(), 1)

    def test_teacher_badge_progress(self):
        badge = TeacherBadgeDefinition.objects.create(
            code="first_impact_3", name="First Impact", description="Earn 100 IP",
            tier="bronze", icon="⚡", criteria_json={"type": "teacher_ip_total", "threshold": 100},
        )
        from gamification.teacher_badges import compute_teacher_badge_progress
        progress = compute_teacher_badge_progress(self.teacher, badge)
        # 15 / 100 = 15%
        self.assertEqual(progress, 15)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/classedge && ./env/bin/python manage.py test gamification.tests.test_teacher_gamification.TeacherBadgeTests --keepdb -v2`
Expected: FAIL — `No module named 'gamification.teacher_badges'`

- [ ] **Step 3: Implement teacher_badges.py**

Create `gamification/teacher_badges.py`:

```python
from gamification.teacher_models import (
    IPTransaction, TeacherBadge, TeacherBadgeDefinition,
    TeacherGamification, TeacherRecognition,
)
from gamification.models import StudentBadge


def evaluate_teacher_badges(teacher):
    """Check all active teacher badges the teacher hasn't earned yet."""
    earned_badge_ids = set(
        TeacherBadge.objects.filter(teacher=teacher).values_list("badge_id", flat=True)
    )
    candidates = TeacherBadgeDefinition.objects.filter(
        is_active=True,
    ).exclude(pk__in=earned_badge_ids)

    gam = TeacherGamification.objects.filter(teacher=teacher).first()
    if not gam:
        return

    for badge in candidates:
        criteria = badge.criteria_json
        if not criteria or "type" not in criteria:
            continue
        evaluator = TEACHER_EVALUATORS.get(criteria["type"])
        if evaluator and evaluator(teacher, gam, criteria):
            TeacherBadge.objects.create(teacher=teacher, badge=badge)


def _eval_teacher_ip_total(teacher, gam, criteria):
    return gam.total_ip >= criteria["threshold"]


def _eval_teacher_grading_count(teacher, gam, criteria):
    count = IPTransaction.objects.filter(
        teacher=teacher, source_type__in=["grading_ontime", "grading_late"],
    ).count()
    return count >= criteria["threshold"]


def _eval_teacher_recognition_count(teacher, gam, criteria):
    count = TeacherRecognition.objects.filter(teacher=teacher).count()
    return count >= criteria["threshold"]


def _eval_teacher_at_risk_recovery(teacher, gam, criteria):
    count = IPTransaction.objects.filter(
        teacher=teacher, source_type="at_risk_recovery",
    ).count()
    return count >= criteria["threshold"]


def _eval_teacher_class_avg(teacher, gam, criteria):
    """Check if teacher has threshold+ subjects with class avg >= criteria avg."""
    from subject.models.subject_model import Subject
    from activity.models.student_activity_model import StudentActivity
    from course.models.term_model import Term
    from course.models.semester_model import Semester
    from django.db.models import Q
    from django.utils import timezone

    now = timezone.localtime(timezone.now())
    semester = Semester.objects.filter(
        start_date__lte=now.date(), end_date__gte=now.date(),
    ).first()
    if not semester:
        return False

    terms = Term.objects.filter(semester=semester)
    teacher_subjects = Subject.objects.filter(
        Q(assign_teacher=teacher) | Q(substitute_teacher=teacher) | Q(collaborators=teacher),
    ).distinct()

    count_above = 0
    for subj in teacher_subjects:
        scores = StudentActivity.objects.filter(
            subject=subj, term__in=terms,
            activity__is_graded=True, activity__max_score__gt=0,
        ).select_related("activity")
        if not scores.exists():
            continue
        total_earned = sum(sa.total_score for sa in scores)
        total_possible = sum(sa.activity.max_score for sa in scores)
        avg = (total_earned / total_possible * 100) if total_possible > 0 else 0
        if avg >= criteria["threshold"]:
            count_above += 1

    return count_above >= criteria["count"]


def _eval_teacher_manual_awards(teacher, gam, criteria):
    count = StudentBadge.objects.filter(awarded_by=teacher).count()
    return count >= criteria["threshold"]


def _eval_teacher_star_avg(teacher, gam, criteria):
    from django.db.models import Avg, Count
    from gamification.teacher_models import TeacherRating

    stats = TeacherRating.objects.filter(teacher=teacher).aggregate(
        avg=Avg("stars"), count=Count("id"),
    )
    if not stats["count"] or stats["count"] < criteria["min_ratings"]:
        return False
    return stats["avg"] >= criteria["min_avg"]


def _eval_teacher_rank(teacher, gam, criteria):
    return gam.current_rank == criteria["rank"]


TEACHER_EVALUATORS = {
    "teacher_ip_total": _eval_teacher_ip_total,
    "teacher_grading_count": _eval_teacher_grading_count,
    "teacher_recognition_count": _eval_teacher_recognition_count,
    "teacher_at_risk_recovery": _eval_teacher_at_risk_recovery,
    "teacher_class_avg": _eval_teacher_class_avg,
    "teacher_manual_awards": _eval_teacher_manual_awards,
    "teacher_star_avg": _eval_teacher_star_avg,
    "teacher_rank": _eval_teacher_rank,
}


# --- Progress Computers (0-100) ---

def _progress_teacher_ip_total(teacher, gam, criteria):
    return min(100, int(gam.total_ip / criteria["threshold"] * 100))


def _progress_teacher_grading_count(teacher, gam, criteria):
    count = IPTransaction.objects.filter(
        teacher=teacher, source_type__in=["grading_ontime", "grading_late"],
    ).count()
    return min(100, int(count / criteria["threshold"] * 100))


def _progress_teacher_recognition_count(teacher, gam, criteria):
    count = TeacherRecognition.objects.filter(teacher=teacher).count()
    return min(100, int(count / criteria["threshold"] * 100))


def _progress_teacher_at_risk_recovery(teacher, gam, criteria):
    count = IPTransaction.objects.filter(
        teacher=teacher, source_type="at_risk_recovery",
    ).count()
    return min(100, int(count / criteria["threshold"] * 100))


def _progress_teacher_class_avg(teacher, gam, criteria):
    # Simplified: count subjects above threshold, compute pct toward count goal
    return 0  # Requires live data, return 0 when no semester


def _progress_teacher_manual_awards(teacher, gam, criteria):
    count = StudentBadge.objects.filter(awarded_by=teacher).count()
    return min(100, int(count / criteria["threshold"] * 100))


def _progress_teacher_star_avg(teacher, gam, criteria):
    from django.db.models import Count
    from gamification.teacher_models import TeacherRating

    count = TeacherRating.objects.filter(teacher=teacher).count()
    return min(100, int(count / criteria["min_ratings"] * 100))


def _progress_teacher_rank(teacher, gam, criteria):
    from gamification.teacher_services import RANK_THRESHOLDS
    target_ip = 0
    for threshold, _, _, rank_code in RANK_THRESHOLDS:
        if rank_code == criteria["rank"]:
            target_ip = threshold
            break
    if target_ip == 0:
        return 100 if gam.current_rank == criteria["rank"] else 0
    return min(100, int(gam.total_ip / target_ip * 100))


TEACHER_PROGRESS_COMPUTERS = {
    "teacher_ip_total": _progress_teacher_ip_total,
    "teacher_grading_count": _progress_teacher_grading_count,
    "teacher_recognition_count": _progress_teacher_recognition_count,
    "teacher_at_risk_recovery": _progress_teacher_at_risk_recovery,
    "teacher_class_avg": _progress_teacher_class_avg,
    "teacher_manual_awards": _progress_teacher_manual_awards,
    "teacher_star_avg": _progress_teacher_star_avg,
    "teacher_rank": _progress_teacher_rank,
}


def compute_teacher_badge_progress(teacher, badge):
    """Compute progress (0-100) for a badge the teacher hasn't earned yet."""
    criteria = badge.criteria_json
    if not criteria or "type" not in criteria:
        return 0
    computer = TEACHER_PROGRESS_COMPUTERS.get(criteria["type"])
    if not computer:
        return 0
    gam = TeacherGamification.objects.filter(teacher=teacher).first()
    if not gam:
        return 0
    return computer(teacher, gam, criteria)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/classedge && ./env/bin/python manage.py test gamification.tests.test_teacher_gamification.TeacherBadgeTests --keepdb -v2`
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/classedge
git add gamification/teacher_badges.py gamification/tests/test_teacher_gamification.py
git commit -m "feat(gamification): add teacher badge evaluators and progress computers"
```

---

### Task 4: Challenge Tests + Completion Logic

**Files:**
- Modify: `gamification/tests/test_teacher_gamification.py`

- [ ] **Step 1: Add failing tests for challenge completion and expiry**

Append to `gamification/tests/test_teacher_gamification.py`:

```python
@override_settings(**_GAM_SETTINGS)
class TeacherChallengeTests(TestCase):
    def setUp(self):
        self.teacher = _create_test_user(username="tc_teach", role_name="teacher")
        self.challenge = TeacherChallenge.objects.create(
            code="test_challenge", name="Test Challenge",
            description="Test", challenge_type="milestone",
            criteria_json={"type": "ip_milestone", "threshold": 50},
            ip_reward=15,
        )

    def test_challenge_completion(self):
        from gamification.teacher_services import award_ip, evaluate_teacher_challenges
        gam = TeacherGamification.objects.create(teacher=self.teacher, total_ip=0)
        progress = TeacherChallengeProgress.objects.create(
            teacher=self.teacher, challenge=self.challenge,
            current_value=50, target_value=50,
        )
        evaluate_teacher_challenges(self.teacher)
        progress.refresh_from_db()
        self.assertIsNotNone(progress.completed_at)
        # Bonus IP awarded
        gam.refresh_from_db()
        self.assertEqual(gam.total_ip, 15)

    def test_challenge_expiry(self):
        from gamification.teacher_services import evaluate_teacher_challenges
        TeacherGamification.objects.create(teacher=self.teacher, total_ip=0)
        progress = TeacherChallengeProgress.objects.create(
            teacher=self.teacher, challenge=self.challenge,
            current_value=50, target_value=50,
            expires_at=timezone.now() - timedelta(days=1),
        )
        evaluate_teacher_challenges(self.teacher)
        progress.refresh_from_db()
        self.assertIsNone(progress.completed_at)  # Expired, not completed
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd ~/classedge && ./env/bin/python manage.py test gamification.tests.test_teacher_gamification.TeacherChallengeTests --keepdb -v2`
Expected: 2 tests PASS (logic already implemented in Task 2)

- [ ] **Step 3: Commit**

```bash
cd ~/classedge
git add gamification/tests/test_teacher_gamification.py
git commit -m "test(gamification): add challenge completion and expiry tests"
```

---

### Task 5: Recognition + Rating Views and Tests

**Files:**
- Create: `gamification/teacher_views.py`
- Modify: `gamification/urls.py`
- Modify: `gamification/tests/test_teacher_gamification.py`

- [ ] **Step 1: Add failing tests for recognition and rating endpoints**

Append to `gamification/tests/test_teacher_gamification.py`:

```python
from course.models.semester_model import Semester
from course.models.subject_enrollment_model import SubjectEnrollment
from subject.models.subject_model import Subject


@override_settings(**_GAM_SETTINGS)
class RecognitionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = _create_test_user(username="rec_teach", role_name="teacher")
        self.student = _create_test_user(username="rec_stu", role_name="student")

    def test_recognition_creates_and_awards(self):
        self.client.login(username="rec_teach", password="testpass")
        resp = self.client.post("/gamification/recognition/send/", {
            "student_id": self.student.pk,
            "message": "Great work on the quiz!",
            "xp_amount": 25,
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(TeacherRecognition.objects.filter(
            teacher=self.teacher, student=self.student,
        ).exists())
        # Teacher earned 1 IP
        self.assertEqual(
            IPTransaction.objects.filter(teacher=self.teacher, source_type="recognition_sent").count(), 1,
        )
        # Student earned 25 XP
        from gamification.models import XPTransaction
        self.assertTrue(XPTransaction.objects.filter(
            student=self.student, source_type="recognition",
        ).exists())


@override_settings(**_GAM_SETTINGS)
class RatingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = _create_test_user(username="rat_teach", role_name="teacher")
        self.student = _create_test_user(username="rat_stu", role_name="student")
        self.semester = Semester.objects.create(
            semester_name="Rating Sem",
            start_date=date(2026, 1, 1), end_date=date(2027, 12, 31),
        )

    def test_rating_creates_and_awards_ip(self):
        self.client.login(username="rat_stu", password="testpass")
        resp = self.client.post("/gamification/rating/submit/", {
            "teacher_id": self.teacher.pk,
            "stars": 5,
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(TeacherRating.objects.filter(
            teacher=self.teacher, student=self.student,
        ).exists())
        # Teacher earned 3 IP for 5-star
        self.assertEqual(
            IPTransaction.objects.filter(teacher=self.teacher, source_type="star_rating_5").count(), 1,
        )

    def test_rating_unique_per_semester(self):
        self.client.login(username="rat_stu", password="testpass")
        self.client.post("/gamification/rating/submit/", {
            "teacher_id": self.teacher.pk, "stars": 4,
        }, content_type="application/json")
        # Update same teacher same semester
        self.client.post("/gamification/rating/submit/", {
            "teacher_id": self.teacher.pk, "stars": 5,
        }, content_type="application/json")
        self.assertEqual(
            TeacherRating.objects.filter(teacher=self.teacher, student=self.student).count(), 1,
        )
        rating = TeacherRating.objects.get(teacher=self.teacher, student=self.student)
        self.assertEqual(rating.stars, 5)  # Updated to 5

    def test_rating_aggregate(self):
        from django.db.models import Avg
        stu2 = _create_test_user(username="rat_stu2", role_name="student")
        TeacherRating.objects.create(
            teacher=self.teacher, student=self.student,
            stars=5, semester=self.semester,
        )
        TeacherRating.objects.create(
            teacher=self.teacher, student=stu2,
            stars=3, semester=self.semester,
        )
        avg = TeacherRating.objects.filter(teacher=self.teacher).aggregate(
            avg=Avg("stars"),
        )["avg"]
        self.assertAlmostEqual(avg, 4.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/classedge && ./env/bin/python manage.py test gamification.tests.test_teacher_gamification.RecognitionTests gamification.tests.test_teacher_gamification.RatingTests --keepdb -v2`
Expected: FAIL — 404 on endpoints (not wired up yet)

- [ ] **Step 3: Implement teacher_views.py**

Create `gamification/teacher_views.py`:

```python
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from course.models.semester_model import Semester
from gamification.services import award_xp
from gamification.teacher_models import TeacherRecognition, TeacherRating
from gamification.teacher_services import award_ip
from roles.decorators import teacher_or_admin_required

VALID_XP_AMOUNTS = {10, 25, 50}


@require_POST
@login_required
@teacher_or_admin_required
def send_recognition(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    student_id = data.get("student_id")
    message = data.get("message", "").strip()
    xp_amount = data.get("xp_amount", 0)

    if not student_id or not message:
        return JsonResponse({"ok": False, "error": "Missing student_id or message"}, status=400)

    if xp_amount not in VALID_XP_AMOUNTS:
        return JsonResponse({"ok": False, "error": "xp_amount must be 10, 25, or 50"}, status=400)

    if len(message) > 300:
        return JsonResponse({"ok": False, "error": "Message too long"}, status=400)

    from accounts.models import CustomUser
    student = CustomUser.objects.filter(pk=student_id).first()
    if not student:
        return JsonResponse({"ok": False, "error": "Student not found"}, status=404)

    recognition = TeacherRecognition.objects.create(
        teacher=request.user, student=student,
        message=message, xp_awarded=xp_amount,
    )

    award_xp(student, xp_amount, "Teacher recognition", "recognition", source_id=recognition.pk)
    award_ip(request.user, 1, "Sent recognition", "recognition_sent", source_id=recognition.pk)

    return JsonResponse({"ok": True})


@require_POST
@login_required
def submit_rating(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    teacher_id = data.get("teacher_id")
    stars = data.get("stars")

    if not teacher_id or not stars or stars not in range(1, 6):
        return JsonResponse({"ok": False, "error": "Invalid teacher_id or stars (1-5)"}, status=400)

    now = timezone.localtime(timezone.now())
    semester = Semester.objects.filter(
        start_date__lte=now.date(), end_date__gte=now.date(),
    ).first()
    if not semester:
        return JsonResponse({"ok": False, "error": "No active semester"}, status=400)

    from accounts.models import CustomUser
    teacher = CustomUser.objects.filter(pk=teacher_id).first()
    if not teacher:
        return JsonResponse({"ok": False, "error": "Teacher not found"}, status=404)

    rating, created = TeacherRating.objects.update_or_create(
        teacher=teacher, student=request.user, semester=semester,
        defaults={"stars": stars},
    )

    # Award IP based on stars (only on creation to avoid gaming)
    if created:
        if stars == 5:
            award_ip(teacher, 3, "5-star rating", "star_rating_5", source_id=rating.pk)
        elif stars == 4:
            award_ip(teacher, 1, "4-star rating", "star_rating_4", source_id=rating.pk)

    return JsonResponse({"ok": True})
```

- [ ] **Step 4: Add URL patterns**

Add these two imports and paths to `gamification/urls.py`:

```python
from gamification import side_activity_views, views, teacher_views
```

Add to `urlpatterns`:
```python
    path("gamification/recognition/send/", teacher_views.send_recognition, name="send_recognition"),
    path("gamification/rating/submit/", teacher_views.submit_rating, name="submit_rating"),
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd ~/classedge && ./env/bin/python manage.py test gamification.tests.test_teacher_gamification.RecognitionTests gamification.tests.test_teacher_gamification.RatingTests --keepdb -v2`
Expected: 4 tests PASS

- [ ] **Step 6: Commit**

```bash
cd ~/classedge
git add gamification/teacher_views.py gamification/urls.py gamification/tests/test_teacher_gamification.py
git commit -m "feat(gamification): add recognition and rating AJAX endpoints"
```

---

### Task 6: Signal Handlers for Auto-Awarding IP

**Files:**
- Modify: `gamification/signals.py`
- Modify: `gamification/tests/test_teacher_gamification.py`

- [ ] **Step 1: Add failing test for student badge → teacher IP signal**

Append to `gamification/tests/test_teacher_gamification.py`:

```python
from gamification.models import BadgeDefinition, StudentBadge


@override_settings(**_GAM_SETTINGS)
class SignalTests(TestCase):
    def setUp(self):
        self.teacher = _create_test_user(username="sig_teach", role_name="teacher")
        self.student = _create_test_user(username="sig_stu", role_name="student")
        self.subject = _create_subject()
        Subject.objects.filter(pk=self.subject.pk).update(assign_teacher=self.teacher)
        self.semester = Semester.objects.create(
            semester_name="Sig Sem",
            start_date=date(2026, 1, 1), end_date=date(2027, 12, 31),
        )
        SubjectEnrollment.objects.create(
            student=self.student, subject=self.subject,
            semester=self.semester, status="enrolled",
        )

    def test_signal_student_badge_awards_ip(self):
        badge = BadgeDefinition.objects.create(
            code="sig_test", name="Test Badge", description="Test",
            tier="bronze", icon="🏅", target_role="student",
        )
        StudentBadge.objects.create(student=self.student, badge=badge)
        # Teacher should have earned 3 IP from the signal
        self.assertTrue(
            IPTransaction.objects.filter(
                teacher=self.teacher, source_type="student_badge_earned",
            ).exists(),
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/classedge && ./env/bin/python manage.py test gamification.tests.test_teacher_gamification.SignalTests --keepdb -v2`
Expected: FAIL — no IPTransaction created (signal not wired yet)

- [ ] **Step 3: Add signal handlers to signals.py**

Add these imports at the top of `gamification/signals.py`:

```python
from gamification.models import StudentBadge
from gamification.teacher_models import TeacherRating
```

Add these two signal handlers at the bottom of `gamification/signals.py`:

```python
@receiver(post_save, sender=StudentBadge)
def on_student_badge_earned(sender, instance, created, **kwargs):
    """When a student earns a badge, award 3 IP to their teachers."""
    if not created:
        return

    student = instance.student
    if not student:
        return

    # Find the student's teachers via subject enrollments
    now = __import__("django.utils.timezone", fromlist=["timezone"]).now()
    from course.models.semester_model import Semester
    from course.models.subject_enrollment_model import SubjectEnrollment
    from subject.models.subject_model import Subject
    from django.db.models import Q

    semester = Semester.objects.filter(
        start_date__lte=now.date(), end_date__gte=now.date(),
    ).first()
    if not semester:
        return

    enrolled_subject_ids = SubjectEnrollment.objects.filter(
        student=student, semester=semester, status="enrolled",
    ).values_list("subject_id", flat=True)

    teacher_ids = set()
    for subj in Subject.objects.filter(pk__in=enrolled_subject_ids):
        if subj.assign_teacher_id:
            teacher_ids.add(subj.assign_teacher_id)
        if subj.substitute_teacher_id:
            teacher_ids.add(subj.substitute_teacher_id)

    from gamification.teacher_services import award_ip
    for teacher_id in teacher_ids:
        from accounts.models import CustomUser
        teacher = CustomUser.objects.filter(pk=teacher_id).first()
        if teacher:
            award_ip(teacher, 3, "Student earned badge", "student_badge_earned", source_id=instance.pk)


@receiver(post_save, sender=TeacherRating)
def on_teacher_rating_created(sender, instance, created, **kwargs):
    """When a student rates a teacher, award IP based on stars."""
    if not created:
        return

    from gamification.teacher_services import award_ip
    if instance.stars == 5:
        award_ip(instance.teacher, 3, "5-star rating", "star_rating_5", source_id=instance.pk)
    elif instance.stars == 4:
        award_ip(instance.teacher, 1, "4-star rating", "star_rating_4", source_id=instance.pk)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/classedge && ./env/bin/python manage.py test gamification.tests.test_teacher_gamification.SignalTests --keepdb -v2`
Expected: 1 test PASS

- [ ] **Step 5: Commit**

```bash
cd ~/classedge
git add gamification/signals.py gamification/tests/test_teacher_gamification.py
git commit -m "feat(gamification): add signals for auto-awarding teacher IP"
```

---

### Task 7: Seed Management Commands + Tests

**Files:**
- Create: `gamification/management/commands/seed_teacher_badges.py`
- Create: `gamification/management/commands/seed_teacher_challenges.py`
- Create: `gamification/management/commands/assign_weekly_challenges.py`
- Create: `gamification/management/commands/assign_monthly_challenges.py`
- Modify: `gamification/tests/test_teacher_gamification.py`

- [ ] **Step 1: Add failing tests for seed commands**

Append to `gamification/tests/test_teacher_gamification.py`:

```python
from django.core.management import call_command


@override_settings(**_GAM_SETTINGS)
class ManagementCommandTests(TestCase):
    def test_seed_teacher_badges_command(self):
        call_command("seed_teacher_badges")
        self.assertEqual(TeacherBadgeDefinition.objects.count(), 8)
        # Idempotent
        call_command("seed_teacher_badges")
        self.assertEqual(TeacherBadgeDefinition.objects.count(), 8)

    def test_seed_teacher_challenges_command(self):
        call_command("seed_teacher_challenges")
        self.assertEqual(TeacherChallenge.objects.count(), 10)
        # Idempotent
        call_command("seed_teacher_challenges")
        self.assertEqual(TeacherChallenge.objects.count(), 10)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/classedge && ./env/bin/python manage.py test gamification.tests.test_teacher_gamification.ManagementCommandTests --keepdb -v2`
Expected: FAIL — `Unknown command: 'seed_teacher_badges'`

- [ ] **Step 3: Create seed_teacher_badges.py**

Create `gamification/management/commands/seed_teacher_badges.py`:

```python
from django.core.management.base import BaseCommand

from gamification.teacher_models import TeacherBadgeDefinition

BADGES = [
    {
        "code": "first_impact",
        "name": "First Impact",
        "description": "Earn your first 10 Impact Points",
        "tier": "bronze",
        "icon": "⚡",
        "criteria_json": {"type": "teacher_ip_total", "threshold": 10},
    },
    {
        "code": "grading_machine",
        "name": "Grading Machine",
        "description": "Grade 50 activities on time",
        "tier": "bronze",
        "icon": "📝",
        "criteria_json": {"type": "teacher_grading_count", "threshold": 50},
    },
    {
        "code": "mentors_touch",
        "name": "Mentor's Touch",
        "description": "Send 20 recognition shoutouts to students",
        "tier": "silver",
        "icon": "🤝",
        "criteria_json": {"type": "teacher_recognition_count", "threshold": 20},
    },
    {
        "code": "risk_responder",
        "name": "Risk Responder",
        "description": "Help 5 at-risk students recover",
        "tier": "silver",
        "icon": "🛟",
        "criteria_json": {"type": "teacher_at_risk_recovery", "threshold": 5},
    },
    {
        "code": "class_champion",
        "name": "Class Champion",
        "description": "Achieve 85%+ class average in 3 subjects",
        "tier": "gold",
        "icon": "🏆",
        "criteria_json": {"type": "teacher_class_avg", "threshold": 85, "count": 3},
    },
    {
        "code": "badge_bestower",
        "name": "Badge Bestower",
        "description": "Manually award 25 badges to students",
        "tier": "gold",
        "icon": "🎖️",
        "criteria_json": {"type": "teacher_manual_awards", "threshold": 25},
    },
    {
        "code": "student_favorite",
        "name": "Student Favorite",
        "description": "Maintain a 4.5+ star average with at least 10 ratings",
        "tier": "gold",
        "icon": "⭐",
        "criteria_json": {"type": "teacher_star_avg", "min_avg": 4.5, "min_ratings": 10},
    },
    {
        "code": "legendary_educator",
        "name": "Legendary Educator",
        "description": "Reach the Platinum Legend rank",
        "tier": "platinum",
        "icon": "👑",
        "criteria_json": {"type": "teacher_rank", "rank": "platinum_legend"},
    },
]


class Command(BaseCommand):
    help = "Seed the 8 teacher badge definitions"

    def handle(self, *args, **options):
        created_count = 0
        for badge_data in BADGES:
            _, created = TeacherBadgeDefinition.objects.get_or_create(
                code=badge_data["code"],
                defaults=badge_data,
            )
            if created:
                created_count += 1
        self.stdout.write(f"Teacher badges: {created_count} created, {len(BADGES) - created_count} already existed.")
```

- [ ] **Step 4: Create seed_teacher_challenges.py**

Create `gamification/management/commands/seed_teacher_challenges.py`:

```python
from django.core.management.base import BaseCommand

from gamification.teacher_models import TeacherChallenge

CHALLENGES = [
    # Rotating — weekly
    {
        "code": "quick_grader",
        "name": "Quick Grader",
        "description": "Grade all pending activities this week",
        "challenge_type": "rotating",
        "criteria_json": {"type": "grade_all_pending"},
        "ip_reward": 10,
        "duration_days": 7,
    },
    {
        "code": "streak_builder",
        "name": "Streak Builder",
        "description": "Get 5 students to start a login streak this week",
        "challenge_type": "rotating",
        "criteria_json": {"type": "student_streaks_started", "count": 5},
        "ip_reward": 8,
        "duration_days": 7,
    },
    {
        "code": "recognition_week",
        "name": "Recognition Week",
        "description": "Send 5 recognition shoutouts this week",
        "challenge_type": "rotating",
        "criteria_json": {"type": "recognitions_sent", "count": 5},
        "ip_reward": 6,
        "duration_days": 7,
    },
    # Rotating — monthly
    {
        "code": "full_house",
        "name": "Full House",
        "description": "Reach 90%+ completion rate across all your subjects this month",
        "challenge_type": "rotating",
        "criteria_json": {"type": "completion_rate", "threshold": 90},
        "ip_reward": 20,
        "duration_days": 30,
    },
    {
        "code": "risk_rescue",
        "name": "Risk Rescue",
        "description": "Move 3 at-risk students down a risk level this month",
        "challenge_type": "rotating",
        "criteria_json": {"type": "at_risk_recoveries", "count": 3},
        "ip_reward": 25,
        "duration_days": 30,
    },
    # Milestones
    {
        "code": "first_steps",
        "name": "First Steps",
        "description": "Earn your first 50 Impact Points",
        "challenge_type": "milestone",
        "criteria_json": {"type": "ip_milestone", "threshold": 50},
        "ip_reward": 15,
        "duration_days": None,
    },
    {
        "code": "badge_collector",
        "name": "Badge Collector",
        "description": "Earn 5 teacher badges",
        "challenge_type": "milestone",
        "criteria_json": {"type": "teacher_badges_earned", "count": 5},
        "ip_reward": 20,
        "duration_days": None,
    },
    {
        "code": "perfect_term",
        "name": "Perfect Term",
        "description": "Achieve 100% activity completion rate for a full term",
        "challenge_type": "milestone",
        "criteria_json": {"type": "perfect_term_completion"},
        "ip_reward": 30,
        "duration_days": None,
    },
    {
        "code": "honor_roll",
        "name": "Honor Roll",
        "description": "All your subjects above 80% class average simultaneously",
        "challenge_type": "milestone",
        "criteria_json": {"type": "all_subjects_above", "threshold": 80},
        "ip_reward": 40,
        "duration_days": None,
    },
    {
        "code": "century_club",
        "name": "Century Club",
        "description": "Send 100 recognitions to students",
        "challenge_type": "milestone",
        "criteria_json": {"type": "recognitions_sent", "count": 100},
        "ip_reward": 50,
        "duration_days": None,
    },
]


class Command(BaseCommand):
    help = "Seed the 10 teacher challenge definitions"

    def handle(self, *args, **options):
        created_count = 0
        for ch_data in CHALLENGES:
            _, created = TeacherChallenge.objects.get_or_create(
                code=ch_data["code"],
                defaults=ch_data,
            )
            if created:
                created_count += 1
        self.stdout.write(f"Teacher challenges: {created_count} created, {len(CHALLENGES) - created_count} already existed.")
```

- [ ] **Step 5: Create assign_weekly_challenges.py**

Create `gamification/management/commands/assign_weekly_challenges.py`:

```python
import random

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import CustomUser, Profile
from gamification.teacher_models import TeacherChallenge, TeacherChallengeProgress
from roles.models import Role


class Command(BaseCommand):
    help = "Assign 2 random weekly challenges to each teacher"

    def handle(self, *args, **options):
        now = timezone.now()
        weekly = list(TeacherChallenge.objects.filter(
            is_active=True, challenge_type="rotating", duration_days=7,
        ))
        if not weekly:
            self.stdout.write("No active weekly challenges found.")
            return

        teacher_role = Role.objects.filter(name__iexact="teacher").first()
        if not teacher_role:
            self.stdout.write("No teacher role found.")
            return

        teacher_ids = Profile.objects.filter(role=teacher_role).values_list("user_id", flat=True)
        assigned_count = 0

        for teacher_id in teacher_ids:
            # Skip challenges this teacher already has active (unexpired)
            active_challenge_ids = set(
                TeacherChallengeProgress.objects.filter(
                    teacher_id=teacher_id,
                    completed_at__isnull=True,
                    expires_at__gt=now,
                ).values_list("challenge_id", flat=True)
            )
            available = [c for c in weekly if c.pk not in active_challenge_ids]
            picks = random.sample(available, min(2, len(available)))

            for challenge in picks:
                target = challenge.criteria_json.get("count", 1)
                TeacherChallengeProgress.objects.create(
                    teacher_id=teacher_id,
                    challenge=challenge,
                    expires_at=now + timezone.timedelta(days=7),
                    current_value=0,
                    target_value=target,
                )
                assigned_count += 1

        self.stdout.write(f"Assigned {assigned_count} weekly challenges.")
```

- [ ] **Step 6: Create assign_monthly_challenges.py**

Create `gamification/management/commands/assign_monthly_challenges.py`:

```python
import random

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Profile
from gamification.teacher_models import TeacherChallenge, TeacherChallengeProgress
from roles.models import Role


class Command(BaseCommand):
    help = "Assign 1 random monthly challenge to each teacher"

    def handle(self, *args, **options):
        now = timezone.now()
        monthly = list(TeacherChallenge.objects.filter(
            is_active=True, challenge_type="rotating", duration_days=30,
        ))
        if not monthly:
            self.stdout.write("No active monthly challenges found.")
            return

        teacher_role = Role.objects.filter(name__iexact="teacher").first()
        if not teacher_role:
            self.stdout.write("No teacher role found.")
            return

        teacher_ids = Profile.objects.filter(role=teacher_role).values_list("user_id", flat=True)
        assigned_count = 0

        for teacher_id in teacher_ids:
            active_challenge_ids = set(
                TeacherChallengeProgress.objects.filter(
                    teacher_id=teacher_id,
                    completed_at__isnull=True,
                    expires_at__gt=now,
                ).values_list("challenge_id", flat=True)
            )
            available = [c for c in monthly if c.pk not in active_challenge_ids]
            if not available:
                continue

            challenge = random.choice(available)
            target = challenge.criteria_json.get("count", 1)
            TeacherChallengeProgress.objects.create(
                teacher_id=teacher_id,
                challenge=challenge,
                expires_at=now + timezone.timedelta(days=30),
                current_value=0,
                target_value=target,
            )
            assigned_count += 1

        self.stdout.write(f"Assigned {assigned_count} monthly challenges.")
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd ~/classedge && ./env/bin/python manage.py test gamification.tests.test_teacher_gamification.ManagementCommandTests --keepdb -v2`
Expected: 2 tests PASS

- [ ] **Step 8: Commit**

```bash
cd ~/classedge
git add gamification/management/commands/seed_teacher_badges.py gamification/management/commands/seed_teacher_challenges.py gamification/management/commands/assign_weekly_challenges.py gamification/management/commands/assign_monthly_challenges.py gamification/tests/test_teacher_gamification.py
git commit -m "feat(gamification): add seed and assignment management commands"
```

---

### Task 8: Dashboard View Integration

**Files:**
- Modify: `gamification/teacher_dashboard.py`
- Modify: `gamification/tests/test_teacher_gamification.py`

- [ ] **Step 1: Add failing tests for dashboard context**

Append to `gamification/tests/test_teacher_gamification.py`:

```python
@override_settings(**_GAM_SETTINGS)
class DashboardIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = _create_test_user(username="di_teach", role_name="teacher")
        self.subject = _create_subject()
        Subject.objects.filter(pk=self.subject.pk).update(assign_teacher=self.teacher)
        self.semester = Semester.objects.create(
            semester_name="DI Sem",
            start_date=date(2026, 1, 1), end_date=date(2027, 12, 31),
        )

    def test_dashboard_shows_rank(self):
        TeacherGamification.objects.create(
            teacher=self.teacher, total_ip=150,
            current_rank="bronze_guide", rank_tier="bronze", rank_title="Guide",
        )
        self.client.login(username="di_teach", password="testpass")
        resp = self.client.get("/dashboard/")
        self.assertEqual(resp.context["rank_tier"], "bronze")
        self.assertEqual(resp.context["rank_title"], "Guide")
        self.assertEqual(resp.context["total_ip"], 150)

    def test_dashboard_shows_challenges(self):
        TeacherGamification.objects.create(teacher=self.teacher)
        challenge = TeacherChallenge.objects.create(
            code="di_test", name="Test", description="Test",
            challenge_type="milestone", criteria_json={},
            ip_reward=10,
        )
        TeacherChallengeProgress.objects.create(
            teacher=self.teacher, challenge=challenge,
            current_value=3, target_value=5,
        )
        self.client.login(username="di_teach", password="testpass")
        resp = self.client.get("/dashboard/")
        self.assertIn("challenges", resp.context)
        self.assertEqual(len(resp.context["challenges"]), 1)

    def test_dashboard_shows_badges(self):
        TeacherGamification.objects.create(teacher=self.teacher)
        badge_def = TeacherBadgeDefinition.objects.create(
            code="di_badge", name="Test Badge", description="Test",
            tier="bronze", icon="⚡",
        )
        TeacherBadge.objects.create(teacher=self.teacher, badge=badge_def)
        self.client.login(username="di_teach", password="testpass")
        resp = self.client.get("/dashboard/")
        self.assertIn("teacher_badges", resp.context)
        self.assertEqual(len(resp.context["teacher_badges"]), 1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/classedge && ./env/bin/python manage.py test gamification.tests.test_teacher_gamification.DashboardIntegrationTests --keepdb -v2`
Expected: FAIL — context keys not present

- [ ] **Step 3: Update teacher_dashboard.py to add gamification context**

Add these imports at the top of `gamification/teacher_dashboard.py`:

```python
from gamification.teacher_models import (
    TeacherBadge, TeacherBadgeDefinition, TeacherChallengeProgress,
    TeacherGamification, TeacherRating,
)
from gamification.teacher_services import RANK_THRESHOLDS, next_rank_threshold
```

Add this block inside `teacher_dashboard()`, after the `spotlight = _calc_spotlight(...)` line and before the `return render(...)`:

```python
    # ── Teacher Gamification ──────────────────────────────────
    teacher_gam = TeacherGamification.objects.filter(teacher=user).first()
    total_ip = teacher_gam.total_ip if teacher_gam else 0
    rank_tier = teacher_gam.rank_tier if teacher_gam else "bronze"
    rank_title = teacher_gam.rank_title if teacher_gam else "Mentor"
    current_rank = teacher_gam.current_rank if teacher_gam else "bronze_mentor"
    next_threshold = next_rank_threshold(total_ip)
    ip_progress_pct = 0
    if next_threshold:
        # Find current threshold
        current_threshold = 0
        for t, _, _, rc in RANK_THRESHOLDS:
            if rc == current_rank:
                current_threshold = t
                break
        range_size = next_threshold - current_threshold
        ip_progress_pct = int((total_ip - current_threshold) / range_size * 100) if range_size > 0 else 100
    else:
        ip_progress_pct = 100

    # Star rating aggregate
    from django.db.models import Avg as AvgAgg
    rating_stats = TeacherRating.objects.filter(teacher=user).aggregate(
        avg=AvgAgg("stars"), count=Count("id"),
    )
    star_avg = round(rating_stats["avg"], 1) if rating_stats["avg"] else 0
    star_count = rating_stats["count"] or 0

    # Active challenges (max 3, non-expired, non-completed first)
    challenges_qs = TeacherChallengeProgress.objects.filter(
        teacher=user, completed_at__isnull=True,
    ).select_related("challenge").order_by("expires_at")[:3]
    challenges = []
    for cp in challenges_qs:
        days_left = None
        if cp.expires_at:
            delta = cp.expires_at - timezone.now()
            days_left = max(0, delta.days)
        progress_pct = int(cp.current_value / cp.target_value * 100) if cp.target_value > 0 else 0
        challenges.append({
            "name": cp.challenge.name,
            "description": cp.challenge.description,
            "current": cp.current_value,
            "target": cp.target_value,
            "progress_pct": min(100, progress_pct),
            "days_left": days_left,
            "ip_reward": cp.challenge.ip_reward,
            "challenge_type": cp.challenge.challenge_type,
        })

    # Earned teacher badges
    teacher_badges = list(
        TeacherBadge.objects.filter(teacher=user)
        .select_related("badge").order_by("-earned_at")
    )
    teacher_badges_total = TeacherBadgeDefinition.objects.filter(is_active=True).count()

    # Auto-assign milestone challenges on first load
    from gamification.teacher_models import TeacherChallenge
    milestones = TeacherChallenge.objects.filter(
        is_active=True, challenge_type="milestone",
    )
    for ms in milestones:
        if not TeacherChallengeProgress.objects.filter(teacher=user, challenge=ms).exists():
            target = ms.criteria_json.get("threshold", ms.criteria_json.get("count", 1))
            TeacherChallengeProgress.objects.create(
                teacher=user, challenge=ms,
                current_value=0, target_value=target,
            )
```

Update the `return render(...)` context dict to add these keys:

```python
        "total_ip": total_ip,
        "rank_tier": rank_tier,
        "rank_title": rank_title,
        "current_rank": current_rank,
        "next_threshold": next_threshold,
        "ip_progress_pct": ip_progress_pct,
        "star_avg": star_avg,
        "star_count": star_count,
        "challenges": challenges,
        "teacher_badges": teacher_badges,
        "teacher_badges_total": teacher_badges_total,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/classedge && ./env/bin/python manage.py test gamification.tests.test_teacher_gamification.DashboardIntegrationTests --keepdb -v2`
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/classedge
git add gamification/teacher_dashboard.py gamification/tests/test_teacher_gamification.py
git commit -m "feat(gamification): integrate teacher gamification data into dashboard view"
```

---

### Task 9: Dashboard Template — Growth Section + Challenges + Badges

**Files:**
- Modify: `gamification/templates/gamification/teacher_dashboard.html`
- Create: `gamification/templates/gamification/teacher_challenges.html`
- Create: `gamification/templates/gamification/teacher_badges_shelf.html`

- [ ] **Step 1: Create teacher_challenges.html fragment**

Create `gamification/templates/gamification/teacher_challenges.html`:

```html
<section class="challenges">
  <div class="section-header">
    <h2 style="font-family:var(--display);font-size:22px;font-weight:500;color:var(--forest);letter-spacing:-0.015em;">Active <em style="font-style:italic;color:var(--gold);font-weight:400;">Challenges</em></h2>
  </div>

  <div class="challenges-grid">
    {% for c in challenges %}
    <div class="challenge-card{% if c.days_left is not None and c.days_left <= 2 %} urgent{% endif %}">
      <div class="challenge-header">
        <span class="challenge-name">{{ c.name }}</span>
        <span class="challenge-reward">+{{ c.ip_reward }} IP</span>
      </div>
      <div class="challenge-desc">{{ c.description }}</div>
      <div class="challenge-progress">
        <div class="challenge-progress-track">
          <div class="challenge-progress-fill" style="width: {{ c.progress_pct }}%;"></div>
        </div>
        <div class="challenge-meta">
          <span>{{ c.current }}/{{ c.target }}</span>
          <span>{% if c.days_left is not None %}{{ c.days_left }}d left{% else %}Ongoing{% endif %}</span>
        </div>
      </div>
    </div>
    {% empty %}
    <div style="padding:20px;text-align:center;color:var(--ink-dim);font-family:var(--display);font-style:italic;">
      No active challenges yet.
    </div>
    {% endfor %}
  </div>
</section>
```

- [ ] **Step 2: Create teacher_badges_shelf.html fragment**

Create `gamification/templates/gamification/teacher_badges_shelf.html`:

```html
<section class="badge-shelf">
  <div class="section-header">
    <h2 style="font-family:var(--display);font-size:22px;font-weight:500;color:var(--forest);letter-spacing:-0.015em;">My <em style="font-style:italic;color:var(--gold);font-weight:400;">Badges</em></h2>
    <span class="badge-count">{{ teacher_badges|length }} / {{ teacher_badges_total }}</span>
  </div>

  <div class="badges-row">
    {% for tb in teacher_badges %}
    <div class="badge-item {{ tb.badge.tier }}" title="{{ tb.badge.name }} — earned {{ tb.earned_at|date:'M j, Y' }}">
      <span class="badge-icon">{{ tb.badge.icon }}</span>
    </div>
    {% empty %}
    <div style="padding:20px;text-align:center;color:var(--ink-dim);font-family:var(--display);font-style:italic;width:100%;">
      No badges earned yet. Complete challenges to earn your first!
    </div>
    {% endfor %}
  </div>
</section>
```

- [ ] **Step 3: Update teacher_dashboard.html — growth section + includes**

Replace the entire growth section in `gamification/templates/gamification/teacher_dashboard.html` (the `<section class="growth">...</section>` block) with:

```html
<!-- Growth overview -->
<section class="growth">
  <div class="growth-header">
    <div>
      <div class="growth-stat-label">Overview</div>
      <div class="growth-stat-value" style="font-size:32px;">{{ total_students }} <span style="font-size:16px;color:var(--ink-dim);font-style:italic;">students</span></div>
      <div class="growth-stat-sub">across {{ active_subjects }} subject{{ active_subjects|pluralize }}</div>
    </div>
    <div style="display:flex;gap:12px;align-items:center;">
      {% if star_count > 0 %}
      <div style="font-size:13px;color:var(--gold);font-weight:600;padding:8px 14px;border:1px solid var(--gold);border-radius:100px;background:var(--gold-bg);">
        &#x2605; {{ star_avg }} ({{ star_count }} rating{{ star_count|pluralize }})
      </div>
      {% endif %}
      {% if semester %}
      <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.16em;color:var(--gold);font-weight:600;padding:10px 18px;border:1px solid var(--gold);border-radius:100px;background:var(--gold-bg);">
        {{ semester.semester_name }}
      </div>
      {% endif %}
    </div>
  </div>

  <div class="growth-stats">
    <div>
      <div class="growth-stat-label">Overall Class Average</div>
      <div class="growth-stat-value">{{ overall_avg }}%</div>
      <div class="growth-stat-sub">Across all graded activities</div>
    </div>
    <div>
      <div class="growth-stat-label">Impact Points</div>
      <div class="growth-stat-value">{{ total_ip }}</div>
      <div class="growth-stat-sub">
        <span class="rank-badge rank-{{ rank_tier }}">{{ rank_tier|title }} {{ rank_title }}</span>
      </div>
    </div>
  </div>

  <div class="progress-section">
    <div class="progress-labels">
      <span>Rank progress</span>
      <span class="target">{% if next_threshold %}{{ total_ip }}/{{ next_threshold }} IP{% else %}Max rank!{% endif %}</span>
    </div>
    <div class="progress-track"><div class="progress-fill" style="width: {{ ip_progress_pct }}%;"></div></div>
  </div>
</section>
```

After the `</section>` for metrics (`{% endfor %}</section>`), add:

```html
<!-- Challenges -->
{% include "gamification/teacher_challenges.html" %}

<!-- Badge Shelf -->
{% include "gamification/teacher_badges_shelf.html" %}
```

- [ ] **Step 4: Add CSS for new sections to teacher_base.html**

Add these styles inside the `<style>` block of `templates/teacher_base.html`, before the closing `</style>` tag:

```css
  /* Rank badge */
  .rank-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 100px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }
  .rank-bronze { background: rgba(205, 127, 50, 0.12); color: #cd7f32; border: 1px solid rgba(205, 127, 50, 0.3); }
  .rank-silver { background: rgba(192, 192, 192, 0.12); color: #808080; border: 1px solid rgba(192, 192, 192, 0.3); }
  .rank-gold { background: var(--gold-bg); color: var(--gold); border: 1px solid rgba(183, 146, 90, 0.3); }
  .rank-platinum { background: rgba(229, 228, 226, 0.15); color: #6c6c6c; border: 1px solid rgba(229, 228, 226, 0.4); }

  /* Challenges */
  .challenges { margin-bottom: 32px; }
  .challenges-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
  .challenge-card {
    background: var(--paper);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 20px;
    box-shadow: var(--shadow);
  }
  .challenge-card.urgent { border-left: 3px solid var(--rose); }
  .challenge-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
  .challenge-name { font-weight: 600; color: var(--ink); font-size: 14px; }
  .challenge-reward { font-size: 12px; color: var(--gold); font-weight: 600; }
  .challenge-desc { font-size: 12px; color: var(--ink-dim); margin-bottom: 12px; }
  .challenge-progress-track { height: 6px; background: var(--cream-2); border-radius: 3px; overflow: hidden; }
  .challenge-progress-fill { height: 100%; background: var(--forest); border-radius: 3px; transition: width 0.3s; }
  .challenge-meta { display: flex; justify-content: space-between; font-size: 11px; color: var(--ink-muted); margin-top: 6px; }

  /* Badge shelf */
  .badge-shelf { margin-bottom: 32px; }
  .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
  .badge-count { font-size: 13px; color: var(--ink-dim); font-weight: 500; }
  .badges-row { display: flex; gap: 12px; flex-wrap: wrap; }
  .badge-item {
    width: 52px; height: 52px;
    display: flex; align-items: center; justify-content: center;
    border-radius: 50%; font-size: 24px;
    background: var(--paper); border: 2px solid var(--border);
    box-shadow: var(--shadow); cursor: default;
    transition: transform 0.2s;
  }
  .badge-item:hover { transform: scale(1.15); }
  .badge-item.bronze { border-color: #cd7f32; }
  .badge-item.silver { border-color: #c0c0c0; }
  .badge-item.gold { border-color: var(--gold); }
  .badge-item.platinum { border-color: #b0b0b0; background: linear-gradient(135deg, #f5f5f5, #e8e8e8); }
```

- [ ] **Step 5: Add "My Progress" to sidebar in teacher_base.html**

Find the Insight section in the sidebar of `templates/teacher_base.html` and add this nav item after the existing items (e.g. after "Coding Overview"):

```html
        <a href="#" class="nav-link" title="Coming soon">
          <span class="nav-icon">&#x1F4C8;</span> My Progress
        </a>
```

- [ ] **Step 6: Verify dashboard renders**

Run: `cd ~/classedge && ./env/bin/python manage.py test gamification.tests.test_teacher_gamification.DashboardIntegrationTests gamification.tests.test_teacher_dashboard --keepdb -v2`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
cd ~/classedge
git add gamification/templates/gamification/teacher_challenges.html gamification/templates/gamification/teacher_badges_shelf.html gamification/templates/gamification/teacher_dashboard.html templates/teacher_base.html
git commit -m "feat(gamification): add challenges, badges, and rank to teacher dashboard UI"
```

---

### Task 10: Recognition Modal + Spotlight Update

**Files:**
- Create: `gamification/templates/gamification/teacher_recognition_modal.html`
- Modify: `gamification/templates/gamification/teacher_dashboard.html`

- [ ] **Step 1: Create recognition modal fragment**

Create `gamification/templates/gamification/teacher_recognition_modal.html`:

```html
<!-- Recognition Modal -->
<div id="recognition-modal" class="modal-overlay" style="display:none;">
  <div class="modal-card">
    <div class="modal-header">
      <h3 style="font-family:var(--display);font-weight:500;color:var(--forest);">Send <em style="color:var(--gold);font-style:italic;">Recognition</em></h3>
      <button onclick="closeRecognitionModal()" class="modal-close">&times;</button>
    </div>
    <div class="modal-body">
      <div class="form-group">
        <label>Student</label>
        <div id="rec-student-name" style="font-weight:600;color:var(--ink);"></div>
      </div>
      <div class="form-group">
        <label for="rec-message">Message</label>
        <textarea id="rec-message" maxlength="300" rows="3" placeholder="Great work on..." style="width:100%;padding:10px;border:1px solid var(--border-strong);border-radius:var(--radius-sm);font-family:var(--body);font-size:14px;resize:vertical;"></textarea>
        <div style="text-align:right;font-size:11px;color:var(--ink-muted);"><span id="rec-charcount">0</span>/300</div>
      </div>
      <div class="form-group">
        <label for="rec-xp">XP Award</label>
        <select id="rec-xp" style="padding:8px 12px;border:1px solid var(--border-strong);border-radius:var(--radius-sm);font-family:var(--body);font-size:14px;">
          <option value="10">10 XP — Small encouragement</option>
          <option value="25" selected>25 XP — Great effort</option>
          <option value="50">50 XP — Outstanding work</option>
        </select>
      </div>
    </div>
    <div class="modal-footer">
      <button onclick="closeRecognitionModal()" style="padding:10px 20px;border:1px solid var(--border-strong);border-radius:var(--radius-sm);background:transparent;cursor:pointer;font-family:var(--body);">Cancel</button>
      <button onclick="sendRecognition()" style="padding:10px 24px;border:none;border-radius:var(--radius-sm);background:var(--forest);color:white;cursor:pointer;font-weight:600;font-family:var(--body);">Send Recognition</button>
    </div>
  </div>
</div>

<script>
let currentStudentId = null;

function openRecognitionModal(studentId, studentName) {
  currentStudentId = studentId;
  document.getElementById('rec-student-name').textContent = studentName;
  document.getElementById('rec-message').value = '';
  document.getElementById('rec-charcount').textContent = '0';
  document.getElementById('recognition-modal').style.display = 'flex';
}

function closeRecognitionModal() {
  document.getElementById('recognition-modal').style.display = 'none';
  currentStudentId = null;
}

document.getElementById('rec-message').addEventListener('input', function() {
  document.getElementById('rec-charcount').textContent = this.value.length;
});

function sendRecognition() {
  const message = document.getElementById('rec-message').value.trim();
  const xpAmount = parseInt(document.getElementById('rec-xp').value);
  if (!message) { alert('Please write a message.'); return; }

  fetch('/gamification/recognition/send/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content,
    },
    body: JSON.stringify({ student_id: currentStudentId, message: message, xp_amount: xpAmount }),
  })
  .then(r => r.json())
  .then(data => {
    if (data.ok) {
      closeRecognitionModal();
      // Mark the spotlight item as recognized
      const btn = document.querySelector(`[data-student-id="${currentStudentId}"]`);
      if (btn) {
        btn.textContent = 'Recognized ✓';
        btn.disabled = true;
        btn.style.opacity = '0.6';
      }
    } else {
      alert(data.error || 'Something went wrong.');
    }
  });
}
</script>
```

- [ ] **Step 2: Add modal CSS to teacher_base.html**

Add these styles inside the `<style>` block of `templates/teacher_base.html`:

```css
  /* Modal */
  .modal-overlay {
    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(45, 49, 66, 0.5);
    display: flex; align-items: center; justify-content: center;
    z-index: 1000;
  }
  .modal-card {
    background: var(--paper); border-radius: var(--radius);
    width: 480px; max-width: 90vw;
    box-shadow: 0 24px 64px -16px rgba(45, 49, 66, 0.2);
  }
  .modal-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 20px 24px; border-bottom: 1px solid var(--border);
  }
  .modal-close {
    background: none; border: none; font-size: 24px; cursor: pointer;
    color: var(--ink-muted); line-height: 1;
  }
  .modal-body { padding: 24px; }
  .modal-footer {
    padding: 16px 24px; border-top: 1px solid var(--border);
    display: flex; justify-content: flex-end; gap: 12px;
  }
  .form-group { margin-bottom: 16px; }
  .form-group label {
    display: block; font-size: 12px; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.1em;
    color: var(--ink-dim); margin-bottom: 6px;
  }
```

- [ ] **Step 3: Update spotlight section to use modal + include modal**

Replace the spotlight section in `gamification/templates/gamification/teacher_dashboard.html` with:

```html
<!-- Student Spotlight -->
{% if spotlight %}
<section class="spotlight">
  <div class="spotlight-label">Student Spotlight</div>
  <h2 class="spotlight-title">
    {% if spotlight|length == 1 %}A student improved this period{% else %}{{ spotlight|length }} students improved this period{% endif %} &mdash; <em>here's who</em>.
  </h2>

  <ul class="spotlight-list">
    {% for s in spotlight %}
    <li class="spotlight-item">
      <div class="spotlight-avatar">{{ s.initial }}</div>
      <div style="flex:1;">
        <strong>{{ s.name }}</strong> jumped from <em>{{ s.old_avg }}% to {{ s.new_avg }}%</em> on recent activities.
      </div>
      <button data-student-id="{{ s.student_id }}" onclick="openRecognitionModal({{ s.student_id }}, '{{ s.name|escapejs }}')" class="spotlight-cta-btn">Send recognition</button>
    </li>
    {% endfor %}
  </ul>
</section>
{% endif %}

{% include "gamification/teacher_recognition_modal.html" %}
```

- [ ] **Step 4: Update teacher_dashboard.py spotlight to include student_id**

In `gamification/teacher_dashboard.py`, find the `_calc_spotlight` function. In the block where `improvers.append({...})` is called, add `"student_id": student_id,` to the dict:

```python
                improvers.append({
                    "student_id": student_id,
                    "name": name,
                    "initial": initial,
                    "old_avg": round(older_avg),
                    "new_avg": round(recent_avg),
                    "delta": round(delta),
                })
```

- [ ] **Step 5: Add spotlight button CSS to teacher_base.html**

Add this style to `templates/teacher_base.html`:

```css
  .spotlight-cta-btn {
    padding: 8px 16px; border: 1px solid rgba(255,255,255,0.3);
    border-radius: var(--radius-sm); background: transparent;
    color: white; font-family: var(--body); font-size: 12px;
    font-weight: 600; cursor: pointer; white-space: nowrap;
    transition: background 0.2s;
  }
  .spotlight-cta-btn:hover { background: rgba(255,255,255,0.1); }
```

- [ ] **Step 6: Commit**

```bash
cd ~/classedge
git add gamification/templates/gamification/teacher_recognition_modal.html gamification/templates/gamification/teacher_dashboard.html gamification/teacher_dashboard.py templates/teacher_base.html
git commit -m "feat(gamification): add recognition modal and update spotlight section"
```

---

### Task 11: Student Dashboard — Recognition Display + Rating Card

**Files:**
- Modify: `gamification/templates/gamification/student_dashboard.html`
- Modify: `gamification/views.py` (student_dashboard view)

- [ ] **Step 1: Add recognition and rating data to student dashboard view**

In `gamification/views.py`, add this import at the top:

```python
from gamification.teacher_models import TeacherRecognition, TeacherRating
```

Inside the `student_dashboard` function, before the `return render(...)`, add:

```python
    # Recent recognitions from teachers
    recent_recognitions = TeacherRecognition.objects.filter(
        student=user,
    ).select_related("teacher").order_by("-created_at")[:3]

    # Teachers to rate this semester
    teachers_to_rate = []
    if semester and enrolled_subject_ids:
        from subject.models.subject_model import Subject as SubjModel
        from django.db.models import Q as QFilter
        teacher_subjects = SubjModel.objects.filter(pk__in=enrolled_subject_ids)
        teacher_ids_seen = set()
        for subj in teacher_subjects:
            if subj.assign_teacher_id and subj.assign_teacher_id not in teacher_ids_seen:
                teacher_ids_seen.add(subj.assign_teacher_id)
                existing_rating = TeacherRating.objects.filter(
                    teacher_id=subj.assign_teacher_id, student=user, semester=semester,
                ).first()
                teacher_user = subj.assign_teacher
                if teacher_user:
                    teachers_to_rate.append({
                        "id": teacher_user.pk,
                        "name": teacher_user.get_full_name() or teacher_user.username,
                        "current_stars": existing_rating.stars if existing_rating else 0,
                    })
```

Add to the render context dict:

```python
        "recent_recognitions": recent_recognitions,
        "teachers_to_rate": teachers_to_rate,
```

- [ ] **Step 2: Add recognition and rating sections to student_dashboard.html**

In `gamification/templates/gamification/student_dashboard.html`, before the final `{% endblock %}`, add:

```html
<!-- Recent Recognition -->
{% if recent_recognitions %}
<section class="recognition-section">
  <h2 class="section-title">&#x1F31F; Recognition</h2>
  <div class="recognition-cards">
    {% for rec in recent_recognitions %}
    <div class="recognition-card">
      <div class="recognition-from">From {{ rec.teacher.first_name|default:rec.teacher.username }}</div>
      <div class="recognition-message">{{ rec.message }}</div>
      <div class="recognition-xp">+{{ rec.xp_awarded }} XP</div>
    </div>
    {% endfor %}
  </div>
</section>
{% endif %}

<!-- Rate Your Teachers -->
{% if teachers_to_rate %}
<section class="rating-section">
  <h2 class="section-title">&#x2B50; Rate Your Teachers</h2>
  <div class="rating-cards">
    {% for t in teachers_to_rate %}
    <div class="rating-card">
      <div class="rating-teacher-name">{{ t.name }}</div>
      <div class="star-selector" data-teacher-id="{{ t.id }}">
        {% for i in "12345" %}
        <span class="star{% if forloop.counter <= t.current_stars %} active{% endif %}" data-value="{{ forloop.counter }}" onclick="submitRating({{ t.id }}, {{ forloop.counter }}, this)">&#x2605;</span>
        {% endfor %}
      </div>
    </div>
    {% endfor %}
  </div>
</section>

<script>
function submitRating(teacherId, stars, el) {
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content ||
                    document.querySelector('[name=csrfmiddlewaretoken]')?.value;
  fetch('/gamification/rating/submit/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
    body: JSON.stringify({ teacher_id: teacherId, stars: stars }),
  })
  .then(r => r.json())
  .then(data => {
    if (data.ok) {
      const container = el.closest('.star-selector');
      container.querySelectorAll('.star').forEach((s, i) => {
        s.classList.toggle('active', i < stars);
      });
    }
  });
}
</script>
{% endif %}
```

- [ ] **Step 3: Add recognition + rating CSS to student_base.html**

Find `templates/student_base.html` and add these styles (inside the `<style>` block, before closing `</style>`):

```css
  /* Recognition */
  .recognition-section { margin-top: 24px; }
  .recognition-cards { display: flex; gap: 12px; flex-wrap: wrap; }
  .recognition-card {
    background: var(--card-bg, rgba(255,255,255,0.06));
    border: 1px solid var(--border, rgba(255,255,255,0.08));
    border-radius: 12px; padding: 16px; flex: 1; min-width: 200px;
  }
  .recognition-from { font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted, #888); margin-bottom: 8px; }
  .recognition-message { font-size: 14px; margin-bottom: 8px; }
  .recognition-xp { font-size: 12px; color: #b7925a; font-weight: 600; }

  /* Rating */
  .rating-section { margin-top: 24px; }
  .rating-cards { display: flex; gap: 12px; flex-wrap: wrap; }
  .rating-card {
    background: var(--card-bg, rgba(255,255,255,0.06));
    border: 1px solid var(--border, rgba(255,255,255,0.08));
    border-radius: 12px; padding: 16px; min-width: 180px;
  }
  .rating-teacher-name { font-weight: 600; margin-bottom: 8px; }
  .star-selector { font-size: 24px; cursor: pointer; }
  .star { color: #555; transition: color 0.2s; }
  .star.active { color: #b7925a; }
  .star:hover { color: #d4a84b; }
```

- [ ] **Step 4: Run all tests to verify nothing broke**

Run: `cd ~/classedge && ./env/bin/python manage.py test gamification.tests --keepdb -v2`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/classedge
git add gamification/views.py gamification/templates/gamification/student_dashboard.html templates/student_base.html
git commit -m "feat(gamification): add recognition display and teacher rating to student dashboard"
```

---

### Task 12: Run Full Test Suite + Seed Data + Final Commit

**Files:** None (verification only)

- [ ] **Step 1: Run all gamification tests**

Run: `cd ~/classedge && ./env/bin/python manage.py test gamification.tests --keepdb -v2`
Expected: All tests PASS (existing tests + 18 new tests)

- [ ] **Step 2: Run seed commands**

Run:
```bash
cd ~/classedge && ./env/bin/python manage.py seed_teacher_badges && ./env/bin/python manage.py seed_teacher_challenges
```
Expected: "Teacher badges: 8 created, 0 already existed." and "Teacher challenges: 10 created, 0 already existed."

- [ ] **Step 3: Verify dashboard renders in browser**

Run: `cd ~/classedge && ./env/bin/python manage.py runserver`

Log in as a teacher account. Verify:
- Growth section shows IP counter + rank badge
- Active Challenges section appears (milestones auto-assigned)
- Badge shelf section appears (empty until badges earned)
- Spotlight "Send recognition" buttons open modal
- Sidebar has "My Progress" link

Log in as a student account. Verify:
- "Rate Your Teachers" card appears with star selectors
- Star selection auto-saves (check Network tab for 200 response)

- [ ] **Step 4: Push to personal fork**

```bash
cd ~/classedge && git push personal main
```
