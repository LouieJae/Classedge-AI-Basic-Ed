# central_content/models/central_module.py
import os
import uuid

from django.db import models


def _module_file_path(instance, filename):
    new_name = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
    return os.path.join("central", "module", new_name)


class CentralModule(models.Model):
    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_REVIEW = "in_review", "In Review"
        APPROVED = "approved", "Approved"

    central_subject = models.ForeignKey(
        "central_content.CentralSubject",
        on_delete=models.CASCADE,
        related_name="modules",
    )

    file_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to=_module_file_path, blank=True, null=True)
    url = models.URLField(max_length=1500, blank=True)
    iframe_code = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    state = models.CharField(max_length=20, choices=State.choices, default=State.DRAFT)
    created_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.PROTECT,
        related_name="modules_created",
    )
    reviewed_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="modules_reviewed",
    )
    review_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "central_content"
        db_table = "central_content_module"
        ordering = ["order"]

    def __str__(self):
        return self.file_name
