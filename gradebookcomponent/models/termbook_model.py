from django.db import models


class TermGradeBookComponents(models.Model):
    teacher = models.ForeignKey('accounts.CustomUser', on_delete=models.PROTECT, related_name='term_gradebook_components', null=True, blank=True)
    term = models.ForeignKey('course.Term', on_delete=models.PROTECT, related_name='term_gradebook_components')
    subjects = models.ManyToManyField('subject.Subject', related_name='term_gradebook_components')
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    base_grade = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.term.term_name} ({self.percentage}%)"
