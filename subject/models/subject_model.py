import os
import uuid
from django.db import models

def get_upload_path(instance, filename):
    filename = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
    return os.path.join('subjectPhoto', filename)


class Subject(models.Model):
    subject_name = models.CharField(max_length=200)
    subject_descriptive_title = models.CharField(max_length=100, null=True, blank=True)
    subject_short_name = models.CharField(max_length=30, null=True, blank=True)
    subject_photo = models.ImageField(upload_to=get_upload_path, null=True, blank=True)
    assign_teacher = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.PROTECT, related_name="primary_teacher", null=True, blank=True
    )
    substitute_teacher = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.PROTECT, related_name="substitute_teacher", null=True, blank=True
    )
    allow_substitute_teacher = models.BooleanField(default=False)
    subject_description = models.TextField(null=True, blank=True)
    subject_code = models.CharField(max_length=30, null=True, blank=True)
    room_number = models.CharField(max_length=30, null=True, blank=True)
    unit = models.PositiveIntegerField(default=3)
    is_coil = models.BooleanField(default=False)
    is_hali = models.BooleanField(default=False)
    is_cte = models.BooleanField(default=False)
    max_number_of_enrollees = models.BigIntegerField(null=True, blank=True)
    number_of_enrollees = models.BigIntegerField(default=0, null=True, blank=True)
    duration = models.CharField(max_length=200, null=True, blank=True)
    industry_partners = models.CharField(max_length=250, null=True, blank=True)
    highlight = models.TextField(null=True, blank=True)
    subject_sync_id = models.CharField(max_length=200, null=True, blank=True)
    SUBJECT_TYPE_CHOICES = [
        ('Lec', 'Lec'),
        ('Lab', 'Lab'),
    ]
    subject_type = models.CharField(max_length=200, null=True, blank=True, choices=SUBJECT_TYPE_CHOICES)
    STATUS_CHOICES = [
        ('Ongoing', 'Ongoing'),
        ('Available', 'Available'),
        ('Closed', 'Closed'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Available')
    collaborators = models.ManyToManyField(
        'accounts.CustomUser',
        blank=True,
        related_name='subject_collaborations',
        help_text="Other teachers who can help manage the subject."
    )
    target_sdgs = models.ManyToManyField('SDG', blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    issued_by = models.CharField(max_length=200, null=True, blank=True)
    issued_under = models.CharField(max_length=200, null=True, blank=True)
    issued_on = models.DateField(null=True, blank=True)
    self_attendance_enabled = models.BooleanField(
        default=False,
        help_text='Allow enrolled students to mark their own attendance during scheduled class time.',
    )
    quest_count_per_lesson = models.PositiveIntegerField(default=5)

    def __str__(self):
        return f"{self.subject_name}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_photo = None

        if not is_new:
            try:
                old_subject = Subject.objects.get(pk=self.pk)
                old_photo = old_subject.subject_photo
            except Subject.DoesNotExist:
                old_photo = None

        super().save(*args, **kwargs)

        if self.subject_photo and (is_new or old_photo != self.subject_photo):
            from mobile.models import Attachment
            Attachment.objects.create(
                subject=self,
                file=self.subject_photo,
            )

    @property
    def active_teacher(self):
        """
        Returns the substitute teacher if allowed; otherwise, the primary teacher.
        """
        if self.allow_substitute_teacher and self.substitute_teacher:
            return self.substitute_teacher
        return self.assign_teacher


class SubjectGradeFinalization(models.Model):
    """Tracks whether grades are finalized and visible for a subject-semester combination."""
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE)
    semester = models.ForeignKey('course.Semester', on_delete=models.CASCADE)
    is_finalized = models.BooleanField(default=False)
    finalized_at = models.DateTimeField(null=True, blank=True)
    finalized_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ('subject', 'semester')
        verbose_name = "Subject Grade Finalization"
        verbose_name_plural = "Subject Grade Finalizations"
    
    def __str__(self):
        return f"{self.subject.subject_name} - {self.semester.semester_name} ({'Finalized' if self.is_finalized else 'Not Finalized'})"
    
    @classmethod
    def get_finalized_subject_ids(cls, semester):
        """
        Returns a list of subject IDs that have finalized grades for the given semester.
        
        Args:
            semester: Semester instance
            
        Returns:
            List of subject IDs (integers)
        """
        return list(cls.objects.filter(
            semester=semester,
            is_finalized=True
        ).values_list('subject_id', flat=True))