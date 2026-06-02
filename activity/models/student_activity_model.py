
import os
import uuid
import cuid

from django.db import models


def get_upload_path_file(instance, filename):
    new_name = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
    return os.path.join('student_activity_files', new_name)


class StudentActivity(models.Model):
    student = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.PROTECT, null=True, blank=True
    )
    activity = models.ForeignKey(
        "Activity", on_delete=models.PROTECT, null=True, blank=True
    )
    term = models.ForeignKey(
        "course.Term", on_delete=models.PROTECT, null=True, blank=True
    )
    subject = models.ForeignKey(
        "subject.Subject", on_delete=models.PROTECT, null=True, blank=True
    )
    retake_count = models.PositiveIntegerField(default=0)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    total_score = models.FloatField(default=0)
    file = models.FileField(upload_to=get_upload_path_file, null=True, blank=True)
    is_editable = models.BooleanField(
        default=False,
        help_text=(
            "If enabled, teachers can edit this score. If disabled, only registrars can modify it."
        ),
    )
    attendance_mode = models.CharField(
        max_length=15,
        choices=[
            ("Present_Online", "Present_Online"),
            ("present", "Present"),
            ("late", "Late"),
            ("excused", "Excused"),
            ("Absent", "Absent"),
        ],
        null=True,
        blank=True,
    )
    # [Classedge LMS] Teacher-entered feedback shown to the student alongside their score.
    feedback = models.TextField(blank=True, default="")
    local_id = models.CharField(
        max_length=36,
        primary_key=True,
        default=cuid.cuid,
        editable=False,
    )
    activity_local_id = models.CharField(max_length=36, null=True, blank=True)

    @property
    def id(self):
        return self.local_id

    def save(self, *args, **kwargs):
        if not self.local_id:
            self.local_id = cuid.cuid()
        if not self.activity_local_id and self.activity_id:
            activity_local = self.activity.local_id if self.activity else None
            if activity_local:
                self.activity_local_id = activity_local
        super().save(*args, **kwargs)
        if self.file and self.student:
            from mobile.models import Attachment
            Attachment.objects.update_or_create(
                student_activity=self,
                defaults={'file': self.file},
            )

    def __str__(self):
        activity_name = self.activity.activity_name if self.activity else "No Activity"
        subject_name = self.subject.subject_name if self.subject else "No Subject"
        return f"{activity_name} - {subject_name}"
