import os
import re
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models.deletion import ProtectedError
from logs.models import SubjectLog


def get_upload_file(instance, filename):
    filename = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
    return os.path.join('module', filename)


def get_scorm_upload_path(instance, filename):
    filename = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
    return os.path.join('scormPackages', filename)


class Module(models.Model):
    file_name = models.CharField(max_length=100)
    file = models.FileField(upload_to=get_upload_file, null=True, blank=True)
    subject = models.ForeignKey('subject.Subject', on_delete=models.CASCADE)
    iframe_code = models.TextField(null=True, blank=True)
    url = models.URLField(max_length=1500, null=True, blank=True)
    term = models.ForeignKey('course.Term', on_delete=models.SET_NULL, null=True, blank=True)
    display_lesson_for_selected_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='modules_visible')
    allow_download = models.BooleanField(default=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0, editable=False)
    central_source_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    onedrive_item_id = models.CharField(max_length=255, null=True, blank=True)
    onedrive_embed_url = models.URLField(max_length=2048, null=True, blank=True)

    def __str__(self):
        return f"{self.file_name}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_instance = None

        if not is_new:
            try:
                old_instance = Module.objects.get(pk=self.pk)
            except Module.DoesNotExist:
                old_instance = None

        # Automatically extract URL if an iframe is provided
        if self.url and "<iframe" in self.url:
            match = re.search(r'src="([^"]+)"', self.url)
            if match:
                self.url = match.group(1)

        super().save(*args, **kwargs)

        # Import here to avoid circular imports
        from logs.models import SubjectLog
        from logs.utils import create_notification_for_teacher, create_notifications_for_subject_students

        # ----- Logging & Notification -----
        should_notify = False
        message = None

        if is_new:
            message = f"A new lesson '{self.file_name}' has been created for {self.subject.subject_name}."
            should_notify = True
        elif old_instance:
            if old_instance.file_name != self.file_name:
                message = f"lesson name changed from '{old_instance.file_name}' to '{self.file_name}'."
                should_notify = True
            elif old_instance.start_date != self.start_date or old_instance.end_date != self.end_date:
                message = f"lesson '{self.file_name}' schedule has been updated."
                should_notify = True
            elif old_instance.description != self.description:
                message = f"lesson '{self.file_name}' description has been updated."
                should_notify = True

        # Save to SubjectLog and Notifications if needed
        if should_notify and message:
            # Save log
            SubjectLog.objects.create(
                subject=self.subject,
                message=message,
                activity=False
            )

            # Create notifications
            create_notification_for_teacher(
                subject=self.subject,
                entity_id=self.id,
                entity_type='lesson',
                path=f'/lesson/{self.id}',
                name=self.file_name,
                message_template=message
            )
            create_notifications_for_subject_students(
                subject=self.subject,
                entity_id=self.id,
                entity_type='lesson',
                path=f'/lesson/{self.id}',
                name=self.file_name,
                message_template=message,
                created_by=self.subject.assign_teacher
            )


    def delete(self, *args, **kwargs):
        if self.additional_activities.exists():
            raise ProtectedError(
                "Cannot delete this lesson because it is linked to one or more Activities.",
                list(self.additional_activities.all()[:3])
            )
        return super().delete(*args, **kwargs)

    class Meta:
        ordering = ['order']
