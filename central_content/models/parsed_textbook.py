import os
import uuid

from django.db import models


def _textbook_file_path(instance, filename):
    new_name = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
    return os.path.join("central", "textbooks", new_name)


class ParsedTextbook(models.Model):
    class Status(models.TextChoices):
        UPLOADING = "uploading", "Uploading"
        PARSING_TOC = "parsing_toc", "Parsing TOC"
        TOC_READY = "toc_ready", "TOC Ready"
        FAILED = "failed", "Failed"

    central_subject = models.ForeignKey(
        "central_content.CentralSubject",
        on_delete=models.CASCADE,
        related_name="textbooks",
    )
    title = models.CharField(max_length=200)
    original_file = models.FileField(upload_to=_textbook_file_path)
    file_hash = models.CharField(max_length=64, blank=True)
    toc_data = models.JSONField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.UPLOADING,
    )
    error_message = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.PROTECT,
        related_name="textbooks_uploaded",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "central_content"
        db_table = "central_content_parsed_textbook"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
