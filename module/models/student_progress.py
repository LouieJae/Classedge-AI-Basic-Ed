from django.db import models
from django.conf import settings
from django.utils import timezone


class StudentProgress(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    module = models.ForeignKey('module.Module', on_delete=models.PROTECT, null=True, blank=True)
    activity = models.ForeignKey('activity.Activity', on_delete=models.PROTECT, null=True, blank=True)
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    completed = models.BooleanField(default=False)
    first_accessed = models.DateTimeField(null=True, blank=True)
    last_accessed = models.DateTimeField(auto_now=True)
    time_spent = models.IntegerField(default=0)
    last_page = models.IntegerField(default=1)

    def __str__(self):
        if self.module and self.module.file_name:
            return f"{self.student.username} - {self.module.file_name} - {self.progress}%"
        elif self.activity:
            return f"{self.student.username} - {self.activity.activity_name} - {self.progress}%"
        else:
            return f"{self.student.username} - No Module or Activity - {self.progress}%"

    def save(self, *args, **kwargs):
        now = timezone.now()

        if not self.first_accessed:
            self.first_accessed = now

        if self.last_accessed:
            time_delta = now - self.last_accessed
            self.time_spent += int(time_delta.total_seconds())

        self.last_accessed = now
        super(StudentProgress, self).save(*args, **kwargs)
