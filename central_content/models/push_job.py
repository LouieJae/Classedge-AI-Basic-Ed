from django.db import models


class PushJob(models.Model):
    class Kind(models.TextChoices):
        PUSH = "push", "Push"
        DELETE = "delete", "Delete"

    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    central_subject = models.ForeignKey(
        "central_content.CentralSubject",
        on_delete=models.CASCADE,
        related_name="push_jobs",
    )
    target_school = models.ForeignKey(
        "central_content.School",
        on_delete=models.CASCADE,
        related_name="push_jobs",
    )
    kind = models.CharField(max_length=10, choices=Kind.choices)
    status = models.CharField(max_length=10, choices=Status.choices)
    subject_version = models.PositiveIntegerField()
    http_status = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField()
    triggered_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.PROTECT,
        related_name="push_jobs_triggered",
    )

    class Meta:
        app_label = "central_content"
        db_table = "central_content_push_job"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.kind}:{self.status}:{self.central_subject_id}->{self.target_school_id}"
