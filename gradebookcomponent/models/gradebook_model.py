from django.db import models


class GradeBookComponents(models.Model):
    teacher = models.ForeignKey('accounts.CustomUser', on_delete=models.PROTECT, related_name='gradebook_components', null=True, blank=True)
    subject = models.ForeignKey('subject.Subject', on_delete=models.PROTECT, related_name='gradebook_components', null=True, blank=True)
    activity_type = models.ForeignKey('activity.ActivityType', on_delete=models.PROTECT, related_name='gradebook_components', null=True, blank=True)  # not use anymore but retain because of the database value
    term = models.ForeignKey('course.Term', on_delete=models.PROTECT, related_name='gradebook_components', null=True, blank=True)
    gradebook_name = models.CharField(max_length=100, null=True, blank=True)
    gradebook_category = models.CharField(max_length=100)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"({self.subject} - {self.gradebook_name} -  {self.percentage}%)"

    @property
    def percentage_display(self):
        try:
            return f"{float(self.percentage):.0f}%"
        except (TypeError, ValueError):
            return "—"

    @property
    def subject_label(self):
        if not self.subject_id:
            return "—"
        name = self.subject.subject_name or ""
        stype = getattr(self.subject, "subject_type", "") or ""
        return f"{name} · {stype}" if stype else name


class ActivityTypePercentage(models.Model):
    gradebook_component = models.ForeignKey('GradeBookComponents', on_delete=models.CASCADE, related_name='activity_type_percentages')
    activity_type = models.ForeignKey('activity.ActivityType', on_delete=models.PROTECT, related_name='activity_type_percentage')
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('gradebook_component', 'activity_type')

    def __str__(self):
        return f"({self.activity_type} - {self.percentage}%)"
