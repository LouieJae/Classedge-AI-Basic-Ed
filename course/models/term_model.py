from django.core.exceptions import ValidationError
from django.db import models


class Term(models.Model):
    TERM_CHOICES = [
        ('Prelim', 'Prelim'),
        ('Midterm', 'Midterm'),
        ('Pre-Final', 'Pre-Final'),
        ('Final Term', 'Final Term'),
    ]

    term_name = models.CharField(max_length=50, choices=TERM_CHOICES)
    semester = models.ForeignKey('course.Semester', on_delete=models.PROTECT, null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, null=True, blank=True)

    def clean(self):
        """[Classedge LMS] Ensure Term dates fall within the Semester window when set."""
        if not self.semester_id:
            return
        sem = self.semester
        if self.start_date and sem.start_date and self.start_date < sem.start_date:
            raise ValidationError("The term's start date is earlier than the semester's start date.")
        if self.end_date and sem.end_date and self.end_date > sem.end_date:
            raise ValidationError("The term's end date is later than the semester's end date.")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError("The term's end date is earlier than its start date.")

    def __str__(self):
        return f"{self.term_name} - {self.start_date} - {self.end_date}"