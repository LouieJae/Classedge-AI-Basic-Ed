from django.db import models
from django.utils import timezone

class Semester(models.Model):
    SEMESTER_CHOICES = [
        ('First Semester', 'First Semester'),
        ('Second Semester', 'Second Semester'),
        ('Third Semester', 'Third Semester'),
        ('Fourth Semester', 'Fourth Semester'),
        ('Summer', 'Summer'),
    ]
    semester_name = models.CharField(max_length=50, choices=SEMESTER_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    end_semester = models.BooleanField(default=False)
    passing_grade = models.PositiveIntegerField(default=75) 
    grade_calculation_method = models.CharField(max_length=50,choices=[('Averaging', 'Averaging'), ('Term Percentage', 'Term Percentage')], default='averaging')
    create_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    department = models.ForeignKey(
        "accounts.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="semesters",
    )
    # [Classedge LMS] Department that owns this semester's dates. SET_NULL so deleting
    # the "General" department re-orphans semesters rather than blocking. Nullable to
    # tolerate legacy rows; backfilled via the Task 6 data migration and slated to be
    # tightened to null=False in a later release.

    @classmethod
    def current(cls):
        """Return the Semester whose date range contains today, or None.

        Replaces the three near-identical ``get_current_semester`` helpers
        that used to live in course/module/gradebookcomponent views.
        """
        today = timezone.now().date()
        return cls.objects.filter(start_date__lte=today, end_date__gte=today).first()

    def save(self, *args, **kwargs):
        if self.end_semester and not self.end_date == timezone.now().date():
            self.end_date = timezone.now().date()

        super(Semester, self).save(*args, **kwargs)

        from course.models import SubjectEnrollment
        if self.end_semester:
            SubjectEnrollment.objects.filter(
                semester=self, is_active_semester=True
            ).update(is_active_semester=False)
        else:
            SubjectEnrollment.objects.filter(
                semester=self, is_active_semester=False
            ).update(is_active_semester=True)

    def get_academic_year(self):
        """
        Returns the academic year as a string (e.g., '2024-2025').
        For 1st Semester: uses its own start year
        For 2nd Semester/Summer: finds the corresponding 1st Semester's start year
        """
        if self.semester_name == 'First Semester':
            start_year = self.start_date.year
        else:
            first_sem = Semester.objects.filter(
                semester_name='First Semester',
                start_date__lte=self.start_date
            ).order_by('-start_date').first()
            
            if first_sem:
                start_year = first_sem.start_date.year
            else:
                start_year = self.start_date.year - 1 if self.semester_name == 'Second Semester' else self.start_date.year
        
        return f"{start_year}-{start_year + 1}"
    
    def __str__(self):
        return f"{self.semester_name} ({self.start_date} - {self.end_date}) "
    