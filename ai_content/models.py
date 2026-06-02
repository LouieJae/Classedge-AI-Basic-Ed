import os
import uuid

from django.db import models


def _reference_file_path(instance, filename):
    new_name = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
    return os.path.join("ai_content", "references", new_name)


class GenerationRequest(models.Model):
    class ContentType(models.TextChoices):
        MODULE = "module", "Module"
        QUIZ = "quiz", "Quiz"
        BOTH = "both", "Both"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Failed"

    subject = models.ForeignKey(
        "subject.Subject", on_delete=models.CASCADE, related_name="generation_requests",
    )
    term = models.ForeignKey(
        "course.Term", on_delete=models.CASCADE, related_name="generation_requests",
    )
    requested_by = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.CASCADE, related_name="generation_requests",
    )
    topic = models.CharField(max_length=200)
    objectives = models.TextField()
    content_type = models.CharField(
        max_length=10, choices=ContentType.choices, default=ContentType.BOTH,
    )
    reference_file = models.FileField(
        upload_to=_reference_file_path, blank=True, null=True,
    )
    reference_text = models.TextField(blank=True)
    model_key = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING,
    )
    error_message = models.TextField(blank=True)
    generated_module_id = models.PositiveIntegerField(null=True, blank=True)
    generated_activity_id = models.CharField(max_length=36, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.topic} ({self.status})"
