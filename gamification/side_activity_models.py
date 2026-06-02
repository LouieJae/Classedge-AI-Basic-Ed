from django.conf import settings
from django.db import models


class SideActivity(models.Model):
    SUB_TYPE_CHOICES = [
        ("daily_challenge", "Daily Challenge"),
        ("flashcard", "Flashcard Review"),
        ("speed_round", "Speed Round"),
        ("match_pair", "Match Pair"),
        ("fill_blank", "Fill in the Blank"),
        ("drag_order", "Drag to Order"),
        ("word_scramble", "Word Scramble"),
        ("equation_balance", "Equation Balancer"),
        ("math_drill", "Math Drill"),
        ("geo_map", "Geography Map"),
        ("timeline_sort", "Timeline Sort"),
        ("code_kata", "Code Kata"),
        ("typing_drill", "Typing Drill"),
        ("reading_mini", "Reading Comprehension Mini"),
        ("practice_quiz", "Practice Quiz"),
    ]
    subject = models.ForeignKey(
        "subject.Subject", on_delete=models.CASCADE, related_name="side_activities",
    )
    sub_type = models.CharField(max_length=30, choices=SUB_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    content_json = models.JSONField()
    estimated_minutes = models.PositiveSmallIntegerField(default=3)
    xp_reward = models.PositiveSmallIntegerField(default=10)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["subject", "sub_type"])]

    def __str__(self):
        return f"{self.title} ({self.get_sub_type_display()})"


class SideActivityAttempt(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="side_activity_attempts",
    )
    side_activity = models.ForeignKey(SideActivity, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(null=True)
    time_taken_seconds = models.PositiveIntegerField(null=True)
    xp_awarded = models.PositiveSmallIntegerField(default=0)
    details_json = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=["student", "completed_at"]),
            models.Index(fields=["side_activity"]),
        ]

    def __str__(self):
        return f"{self.student.username} — {self.side_activity.title}"
