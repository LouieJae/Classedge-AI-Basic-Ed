from django.db import models

class StudentParticipationScore(models.Model):
    student = models.ForeignKey('accounts.CustomUser', on_delete=models.PROTECT)
    subject = models.ForeignKey('subject.Subject', on_delete=models.PROTECT)
    term = models.ForeignKey('Term', on_delete=models.PROTECT)
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=100)

    class Meta:
        unique_together = ('student', 'subject', 'term')

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.subject.subject_name} - {self.term.term_name} - {self.score}/{self.max_score}"
    