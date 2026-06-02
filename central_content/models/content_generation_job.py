from django.db import models


class ContentGenerationJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Failed"

    curriculum_plan = models.ForeignKey(
        "central_content.CurriculumPlan",
        on_delete=models.CASCADE,
        related_name="generation_jobs",
    )
    model_key = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING,
    )
    total_weeks = models.PositiveIntegerField()
    completed_weeks = models.PositiveIntegerField(default=0)
    failed_weeks = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    week_results = models.JSONField(default=list)
    triggered_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.PROTECT,
        related_name="content_generation_jobs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "central_content"
        db_table = "central_content_generation_job"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Generation job for {self.curriculum_plan} ({self.status})"
