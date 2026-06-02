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
    family = models.CharField(max_length=50, blank=True, default="", db_index=True)
    family_rank = models.PositiveSmallIntegerField(default=0)

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
    award_type = models.CharField(max_length=50, blank=True, default="")
    icon = models.CharField(max_length=80, blank=True, default="")
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
