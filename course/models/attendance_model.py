from django.db import models
from django.conf import settings

class Attendance(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    subject = models.ForeignKey('subject.Subject', on_delete=models.PROTECT)
    date = models.DateField(null=True, blank=True)
    status = models.ForeignKey('AttendanceStatus', on_delete=models.PROTECT, null=True, blank=True) 
    remark = models.TextField(null=True, blank=True)  # Additional remarks for the attendance (optional)
    graded = models.BooleanField(default=True)  # Whether the attendance has been graded or not
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='attendances', null=True, blank=True)
    schedule = models.ForeignKey('subject.Schedule', on_delete=models.PROTECT, null=True, blank=True)
    marked_at = models.DateTimeField(null=True, blank=True)
    self_marked = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.subject.subject_name} ({self.status})"

    def get_status_points(self):
        points = TeacherAttendancePoints.objects.filter(teacher=self.teacher, status=self.status).first()
        return points.points if points else 0
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['student', 'subject', 'date'], name='unique_attendance_per_day')
        ]

class AttendanceStatus(models.Model):
    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Present_Online', 'Present_Online'),
        ('Late', 'Late'),
        ('Absent', 'Absent'),
        ('Excused', 'Excused'),
    ]
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, null=True, blank=True)

    def __str__(self):
        return self.status

class TeacherAttendancePoints(models.Model):
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='attendance_points')
    status = models.ForeignKey('AttendanceStatus', on_delete=models.PROTECT)
    points = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)

    class Meta:
        unique_together = ('teacher', 'status')  # Ensure each teacher can set points for each status only once

    def __str__(self):
        return f"{self.teacher.get_full_name()} - {self.status.status}: {self.points} points"

