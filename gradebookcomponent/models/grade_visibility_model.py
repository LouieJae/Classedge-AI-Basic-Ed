from django.db import models


class GradeVisibilitySettings(models.Model):
    teacher = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name='grade_visibility_settings')
    subject = models.ForeignKey('subject.Subject', on_delete=models.CASCADE, related_name='grade_visibility_settings')
    term = models.ForeignKey('course.Term', on_delete=models.CASCADE, related_name='grade_visibility_settings', null=True, blank=True)
    is_visible = models.BooleanField(default=False, help_text="If checked, students can view their grades for this subject/term")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Grade Visibility Setting"
        verbose_name_plural = "Grade Visibility Settings"
        unique_together = ('teacher', 'subject', 'term')

    def __str__(self):
        term_str = f" - {self.term}" if self.term else ""
        visibility = "Visible" if self.is_visible else "Hidden"
        return f"{self.subject}{term_str}: {visibility}"
