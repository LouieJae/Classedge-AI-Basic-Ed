from django.db import models
import cuid
import os

class Attachment(models.Model):
    id = models.CharField(primary_key=True, default=cuid.cuid, max_length=255)
    profile = models.ForeignKey('accounts.Profile', related_name='attachments', on_delete=models.PROTECT, null=True, blank=True)
    student_activity = models.ForeignKey('activity.StudentActivity', related_name='attachments', on_delete=models.PROTECT, null=True, blank=True)
    subject = models.ForeignKey('subject.Subject', related_name='attachments', on_delete=models.PROTECT, null=True, blank=True)
    lesson = models.ForeignKey('module.Module', related_name='attachments', on_delete=models.PROTECT, null=True, blank=True)
    record_details = models.ForeignKey('activity.RetakeRecordDetail', related_name='attachments', on_delete=models.PROTECT, null=True, blank=True)
    activity = models.ForeignKey('activity.Activity', related_name='attachments', on_delete=models.PROTECT, null=True, blank=True)
    question_choice = models.ForeignKey('activity.QuestionChoice', related_name='attachments', on_delete=models.PROTECT, null=True, blank=True)
    activity_question = models.ForeignKey('activity.ActivityQuestion', related_name='attachments', on_delete=models.PROTECT, null=True, blank=True)
    student_question = models.ForeignKey('activity.StudentQuestion', related_name='attachments', on_delete=models.PROTECT, null=True, blank=True)
    file = models.FileField(upload_to='uploads/')

    def __str__(self):
        return self.id
    
    @property
    def file_uuid(self):
        if self.file:
            return os.path.basename(self.file.name).split('.')[0]
        return None