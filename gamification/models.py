import secrets

from django.conf import settings
from django.db import models


def _generate_share_token():
    return secrets.token_urlsafe(16)


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
            models.Index(fields=["-total_xp"], name="gam_total_xp_idx"),
        ]

    def __str__(self):
        try:
            student = str(self.student)
        except Exception:
            student = f"user#{self.student_id}"
        return f"{student} — Lv{self.current_level} ({self.total_xp} XP)"


class XPTransaction(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="xp_transactions",
    )
    amount = models.IntegerField()
    reason = models.CharField(max_length=100)
    source_type = models.CharField(max_length=50)
    # CharField (not int) to hold both legacy integer PKs and CUID-style
    # primary keys (e.g. StudentActivity.local_id) emitted by source models.
    source_id = models.CharField(max_length=36, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["student", "created_at"], name="gam_xp_stu_date_idx"),
            models.Index(fields=["source_type", "source_id"], name="gam_xp_src_idx"),
        ]

    def __str__(self):
        try:
            student = str(self.student)
        except Exception:
            student = f"user#{self.student_id}"
        return f"{student} {self.amount:+d} XP — {self.reason}"


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
    family = models.CharField(max_length=50, blank=True, default="", db_index=True)
    family_rank = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return f"[{self.tier}] {self.name}"


class StudentBadge(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="earned_badges",
    )
    badge = models.ForeignKey(
        BadgeDefinition,
        on_delete=models.CASCADE,
    )
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
    is_featured = models.BooleanField(default=False, db_index=True)
    share_token = models.CharField(
        max_length=32,
        unique=True,
        null=True,
        blank=True,
        default=_generate_share_token,
    )

    class Meta:
        unique_together = [("student", "badge")]

    def __str__(self):
        return f"{self.student} earned {self.badge.name}"


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


from gamification.side_activity_models import SideActivity, SideActivityAttempt  # noqa: E402, F401
from gamification.teacher_models import (  # noqa: E402, F401
    TeacherGamification, IPTransaction, TeacherBadgeDefinition, TeacherBadge,
    TeacherChallenge, TeacherChallengeProgress, TeacherRecognition, TeacherRating,
)
from gamification.quest_settings_models import OrganizationQuestSettings  # noqa: F401
from gamification.quest_models import Quest, QuestAttempt, QuestGenerationJob  # noqa: F401
