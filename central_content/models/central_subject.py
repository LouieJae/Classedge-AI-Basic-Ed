# central_content/models/central_subject.py
import os
import uuid

from django.db import models


def _subject_photo_path(instance, filename):
    new_name = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
    return os.path.join("central", "subjectPhoto", new_name)


class CentralSubject(models.Model):
    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_REVIEW = "in_review", "In Review"
        APPROVED = "approved", "Approved"

    class SubjectType(models.TextChoices):
        LEC = "Lec", "Lec"
        LAB = "Lab", "Lab"

    # Content-bearing (will be copied to school tenant in Sub-project 2)
    subject_name = models.CharField(max_length=200)
    subject_descriptive_title = models.CharField(max_length=100, blank=True)
    subject_short_name = models.CharField(max_length=30, blank=True)
    subject_photo = models.ImageField(upload_to=_subject_photo_path, blank=True, null=True)
    subject_description = models.TextField(blank=True)
    subject_code = models.CharField(max_length=30, blank=True)
    subject_type = models.CharField(max_length=10, choices=SubjectType.choices, blank=True)
    unit = models.PositiveIntegerField(default=3)
    target_sdgs = models.ManyToManyField("subject.SDG", blank=True, related_name="central_subjects")

    # Central-only metadata
    target_grade_level = models.CharField(max_length=50, blank=True)
    target_curriculum = models.CharField(max_length=100, blank=True)
    version = models.PositiveIntegerField(default=1)
    state = models.CharField(max_length=20, choices=State.choices, default=State.DRAFT)

    created_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.PROTECT,
        related_name="subjects_created",
    )
    submitted_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="subjects_submitted",
    )
    reviewed_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="subjects_reviewed",
    )
    review_notes = models.TextField(blank=True)
    source_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "central_content"
        db_table = "central_content_subject"
        ordering = ["-updated_at"]

    def __str__(self):
        return self.subject_name
