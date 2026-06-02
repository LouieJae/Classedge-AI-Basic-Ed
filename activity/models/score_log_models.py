from django.db import models

class ScoreChangeLog(models.Model):
    student_activity = models.ForeignKey(
        "StudentActivity", on_delete=models.CASCADE, related_name="score_logs"
    )
    changed_by = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.PROTECT, related_name="score_changes"
    )
    previous_score = models.FloatField()
    new_score = models.FloatField()
    change_date = models.DateTimeField(auto_now_add=True)
    # [Classedge LMS] Teacher's justification for a manual score override.
    reason = models.TextField(blank=True, default="")

    def __str__(self):
        return (
            f"{self.student_activity} - Changed by {self.changed_by.username} on {self.change_date}"
        )
