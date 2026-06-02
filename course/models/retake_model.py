

from django.db import models

class Retake(models.Model):
    subject_enrollment = models.ForeignKey('SubjectEnrollment', on_delete=models.CASCADE, related_name='retakes')
    retake_date = models.DateField(auto_now_add=True)
    reason = models.TextField()


    def __str__(self):
        return f"Retake of {self.subject_enrollment.subject} by {self.subject_enrollment.student} on {self.retake_date}"
