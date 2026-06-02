import os
import uuid

from django.db import models


def _received_subject_photo_path(instance, filename):
    new_name = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
    return os.path.join("received_central", "subjectPhoto", new_name)


class ReceivedCentralSubject(models.Model):
    central_id = models.IntegerField(unique=True)
    central_version = models.PositiveIntegerField()

    subject_name = models.CharField(max_length=200)
    subject_descriptive_title = models.CharField(max_length=100, blank=True)
    subject_short_name = models.CharField(max_length=30, blank=True)
    subject_photo = models.ImageField(
        upload_to=_received_subject_photo_path, blank=True, null=True,
    )
    subject_description = models.TextField(blank=True)
    subject_code = models.CharField(max_length=30, blank=True)
    subject_type = models.CharField(max_length=10, blank=True)
    unit = models.PositiveIntegerField(default=3)

    target_grade_level = models.CharField(max_length=50, blank=True)
    target_curriculum = models.CharField(max_length=100, blank=True)

    target_sdgs = models.ManyToManyField(
        "subject.SDG", blank=True, related_name="received_central_subjects",
    )

    received_at = models.DateTimeField(auto_now_add=True)
    last_received_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "received_central_content"
        db_table = "received_central_subject"
        ordering = ["-last_received_at"]

    def __str__(self):
        return f"{self.subject_name} (central #{self.central_id})"
