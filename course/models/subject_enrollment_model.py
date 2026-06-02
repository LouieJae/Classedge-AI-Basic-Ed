from django.db import models
from django.db.models import Q

class SubjectEnrollment(models.Model):
    STATUS_CHOICES = [
        ('enrolled', 'Enrolled'),
        ('dropped', 'Dropped'),
        ('completed', 'Completed'),
        ('administrative_drop', 'Administrative Drop')
    ]

    student = models.ForeignKey('accounts.CustomUser', on_delete=models.PROTECT, null=True, blank=True)
    subject = models.ForeignKey('subject.Subject', on_delete=models.PROTECT, null=True, blank=True)
    enrollment_date = models.DateField(auto_now_add=True)
    semester = models.ForeignKey('Semester', on_delete=models.PROTECT, null=True, blank=True)
    can_view_grade = models.BooleanField(default=False)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='enrolled')
    drop_date = models.DateField(null=True, blank=True)
    administrative_drop_date = models.DateField(null=True, blank=True)
    is_active_semester = models.BooleanField(default=True)
    student_name = models.CharField(max_length=255,null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'subject', 'semester'],
                name='uniq_student_subject_semester_with_student',
                condition=Q(student__isnull=False),
            ),
            models.UniqueConstraint(
                fields=['subject', 'semester'],
                name='uniq_subject_semester_when_placeholder',
                condition=Q(student__isnull=True),
            ),
        ]

    def __str__(self):
        return f"{self.student} enrolled in {self.subject}"

    def save(self, *args, **kwargs):
        student_name = self.student.get_full_name() if self.student else None
        if student_name:
            self.student_name = student_name
        if self.semester.end_semester:
            self.is_active_semester = False
        super().save(*args, **kwargs)