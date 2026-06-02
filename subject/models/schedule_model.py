from django.db import models
from multiselectfield import MultiSelectField


class Schedule(models.Model):
    DAYS_OF_WEEK = [
        ('Mon', 'Monday'),
        ('Tue', 'Tuesday'),
        ('Wed', 'Wednesday'),
        ('Thu', 'Thursday'),
        ('Fri', 'Friday'),
        ('Sat', 'Saturday'),
        ('Sun', 'Sunday'),
    ]
    SCHEDULE_TYPE_CHOICES = [
        ('Overload', 'Overload'),
        ('Build in', 'Build in'),
        ('Regular', 'Regular'),
    ]

    schedule_type = models.CharField(choices=SCHEDULE_TYPE_CHOICES, max_length=20, null=True, blank=True)
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE, related_name='schedules')
    sync_id = models.CharField(max_length=200, null=True, blank=True)
    schedule_start_time = models.TimeField()
    schedule_end_time = models.TimeField()
    days_of_week = MultiSelectField(choices=DAYS_OF_WEEK, max_choices=7, max_length=100)
    semester = models.ForeignKey('course.Semester', on_delete=models.CASCADE, related_name='schedules', null=True, blank=True)
    is_active_semester = models.BooleanField(default=True)

    
    def __str__(self):
        return f"{self.subject.subject_name} - {', '.join(self.days_of_week)} {self.schedule_start_time} to {self.schedule_end_time}"

    def save(self, *args, **kwargs):
        if self.semester:
            self.is_active_semester = not self.semester.end_semester
        super().save(*args, **kwargs)
