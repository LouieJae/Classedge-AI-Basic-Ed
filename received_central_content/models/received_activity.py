from django.db import models


class ReceivedCentralActivity(models.Model):
    class PassingScoreType(models.TextChoices):
        NUMBER = "number", "Number"
        PERCENTAGE = "percentage", "Percentage"

    class RetakeMethod(models.TextChoices):
        HIGHEST = "highest", "Highest Score"
        LATEST = "latest", "Latest Take"
        AVERAGE = "average", "Average"
        FIRST = "first", "First Attempt"

    received_subject = models.ForeignKey(
        "received_central_content.ReceivedCentralSubject",
        on_delete=models.CASCADE,
        related_name="activities",
    )
    central_id = models.IntegerField(unique=True)

    activity_name = models.CharField(max_length=100)
    activity_instruction = models.TextField(blank=True)
    activity_type = models.ForeignKey(
        "activity.ActivityType", on_delete=models.PROTECT,
        related_name="received_central_activities",
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

    related_modules = models.ManyToManyField(
        "received_central_content.ReceivedCentralModule",
        blank=True,
        related_name="related_activities",
    )

    class Meta:
        app_label = "received_central_content"
        db_table = "received_central_activity"
        ordering = ["central_id"]

    def __str__(self):
        return self.activity_name
