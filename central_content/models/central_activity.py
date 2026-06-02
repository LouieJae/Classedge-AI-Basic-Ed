# central_content/models/central_activity.py
from django.db import models


class CentralActivity(models.Model):
    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_REVIEW = "in_review", "In Review"
        APPROVED = "approved", "Approved"

    class PassingScoreType(models.TextChoices):
        NUMBER = "number", "Number"
        PERCENTAGE = "percentage", "Percentage"

    class RetakeMethod(models.TextChoices):
        HIGHEST = "highest", "Highest Score"
        LATEST = "latest", "Latest Take"
        AVERAGE = "average", "Average"
        FIRST = "first", "First Attempt"

    central_subject = models.ForeignKey(
        "central_content.CentralSubject",
        on_delete=models.CASCADE,
        related_name="activities",
    )
    related_modules = models.ManyToManyField(
        "central_content.CentralModule",
        blank=True,
        related_name="related_activities",
    )

    activity_name = models.CharField(max_length=100)
    activity_instruction = models.TextField(blank=True)
    activity_type = models.ForeignKey(
        "activity.ActivityType", on_delete=models.PROTECT,
    )

    max_score = models.PositiveIntegerField(default=100)
    time_duration = models.PositiveIntegerField(default=0)
    passing_score = models.FloatField(default=0)
    passing_score_type = models.CharField(
        max_length=10, choices=PassingScoreType.choices, default=PassingScoreType.PERCENTAGE,
    )
    max_retake = models.PositiveIntegerField(default=0)
    retake_method = models.CharField(
        max_length=15, choices=RetakeMethod.choices, default=RetakeMethod.HIGHEST,
    )
    shuffle_questions = models.BooleanField(default=False)
    is_graded = models.BooleanField(default=True)

    state = models.CharField(max_length=20, choices=State.choices, default=State.DRAFT)
    created_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.PROTECT,
        related_name="activities_created",
    )
    reviewed_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="activities_reviewed",
    )
    review_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "central_content"
        db_table = "central_content_activity"
        ordering = ["-updated_at"]

    def __str__(self):
        return self.activity_name
