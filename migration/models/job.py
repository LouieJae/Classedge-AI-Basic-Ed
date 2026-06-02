from django.db import models


class MigrationJob(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("paused", "Paused"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    app_label = models.CharField(max_length=64)
    model_name = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending")
    last_cursor = models.CharField(max_length=128, blank=True, default="")
    total_estimated = models.IntegerField(default=0)
    rows_fetched = models.IntegerField(default=0)
    rows_written = models.IntegerField(default=0)
    rows_skipped = models.IntegerField(default=0)
    rows_errored = models.IntegerField(default=0)
    dry_run = models.BooleanField(default=False)
    started_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_verification = models.JSONField(default=dict, blank=True)
    # ID of the most recent Celery task driving this job (set by StartJobView,
    # cleared on natural completion). Lets the Stop action revoke the in-flight
    # task instead of waiting for it to notice the paused-status flag.
    current_task_id = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        unique_together = [("app_label", "model_name")]
        indexes = [models.Index(fields=["status"])]
        ordering = ["app_label", "model_name"]

    def __str__(self) -> str:
        return f"{self.app_label}.{self.model_name} [{self.status}]"
