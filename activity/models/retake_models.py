from django.db import models
import cuid
import uuid
import os

def get_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    new_name = f"{uuid.uuid4()}{ext}"
    return os.path.join('uploadDocuments', new_name)


class RetakeRecord(models.Model):
    
    STATUS_CHOICES = [
        ('ongoing', 'Ongoing'),
        ('submitted', 'Submitted'),
        ('expired', 'Expired'),
        ('in_progress', 'In_progress')
    ]
    
    student_activity = models.ForeignKey(
        "StudentActivity", on_delete=models.CASCADE, related_name="retake_records", null=True, blank=True
    )
    student = models.ForeignKey("accounts.CustomUser", on_delete=models.PROTECT, null=True, blank=True)
    retake_number = models.PositiveIntegerField(default=1)  # Track which retake this is (first, second, etc.)
    score = models.FloatField(default=0)  # Store the score for each retake
    retake_time = models.DateTimeField(auto_now_add=True)  # Timestamp of when the retake was done
    duration = models.PositiveIntegerField(default=0)
    question_order = models.JSONField(default=list, blank=True)  # Store ordered question IDs as array [1, 5, 3, 2, 4]
    choice_order = models.JSONField(default=dict, blank=True)    # Per-question choice order: {"<question_id>": [<choice_id>, ...]}
    last_index = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ongoing')  # Track attempt status
    started_at = models.DateTimeField(null=True, blank=True)  # When the attempt started
    will_end_at = models.DateTimeField(null=True, blank=True)  # When the attempt will end
    local_id = models.CharField(
        max_length=36, primary_key=True, default=cuid.cuid, editable=False
    )
    activity = models.ForeignKey('Activity', on_delete=models.PROTECT, null=True, blank=True)
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)
    total_elapsed_seconds = models.PositiveIntegerField(default=0)
    late_penalty_percent = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.local_id:
            self.local_id = cuid.cuid()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Retake {self.retake_number} for {self.student_activity.activity.activity_name} - {self.student.email}"


class RetakeRecordDetail(models.Model):
    retake_record = models.ForeignKey(
        "RetakeRecord", on_delete=models.CASCADE, related_name="retake_record_details", null=True, blank=True
    )
    student = models.ForeignKey("accounts.CustomUser", on_delete=models.PROTECT, null=True, blank=True)
    activity_question = models.ForeignKey(
        "ActivityQuestion", on_delete=models.CASCADE, null=True, blank=True
    )
    student_answer = models.TextField(null=True, blank=True)
    score = models.FloatField(default=0)
    submission_time = models.DateTimeField(null=True, blank=True)
    uploaded_file = models.FileField(upload_to=get_upload_path, null=True, blank=True)
    local_id = models.CharField(
        max_length=36, primary_key=True, default=cuid.cuid, editable=False
    )

    def save(self, *args, **kwargs):
        if not self.local_id:
            self.local_id = cuid.cuid()

        is_new = self.pk is None
        old_file = None

        if not is_new:
            try:
                old_detail = RetakeRecordDetail.objects.get(pk=self.pk)
                old_file = old_detail.uploaded_file
            except RetakeRecordDetail.DoesNotExist:
                old_file = None

        super().save(*args, **kwargs)

        if self.uploaded_file and (is_new or old_file != self.uploaded_file):
            from mobile.models import Attachment
            Attachment.objects.create(
                record_details=self,
                file=self.uploaded_file
            )

    def __str__(self):
        student_email = self.student.email if self.student_id else "unknown"
        activity_name = (
            self.activity_question.activity.activity_name
            if self.activity_question_id and self.activity_question.activity_id
            else "unknown activity"
        )
        return f"Retake Detail for {student_email} - {activity_name}"
