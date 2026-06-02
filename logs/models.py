from django.db import models


class SubjectLog(models.Model):
    subject = models.ForeignKey('subject.Subject', on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    activity = models.BooleanField(default=False)

    def __str__(self):
        return f"Log for {self.subject.subject_name} at {self.created_at}"

class UserSubjectLog(models.Model):
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE)
    subject_log = models.ForeignKey('SubjectLog', on_delete=models.CASCADE)
    read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.subject_log.message} - Read: {self.read}"
    
class StudentActivityLog(models.Model):
    student = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE)
    activity = models.ForeignKey('activity.Activity', on_delete=models.CASCADE, blank=True, null=True)
    subject = models.ForeignKey('subject.Subject', on_delete=models.CASCADE)
    submission_time = models.DateTimeField(auto_now_add=True)
    total_score = models.FloatField(default=0)
    retake_number = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.student.first_name} {self.student.last_name} submitted an activity in {self.subject.subject_name} at {self.submission_time}"


class Notification(models.Model):
    user_id = models.ForeignKey('accounts.CustomUser', on_delete=models.PROTECT, related_name='notifications')
    name = models.CharField(max_length=255,null=True,blank=True)
    entity_id = models.CharField(max_length=64)
    entity_type = models.CharField(max_length=50, null=True)
    path = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField()
    due_at = models.DateTimeField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.PROTECT, related_name='created_notifications', null=True)
    
    def __str__(self):
        return self.name