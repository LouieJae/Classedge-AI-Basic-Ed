from django.db import models

class Rubrics(models.Model):
    teacher = models.ForeignKey("accounts.CustomUser", blank=True, null=True, on_delete=models.PROTECT)
    subject = models.ForeignKey("subject.Subject", blank=True, null=True, on_delete=models.PROTECT)
    rubric_name = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = ['subject', 'rubric_name']

    def __str__(self):
        return f"{self.rubric_name} - {self.subject.subject_name if self.subject else 'No Subject'}"

class RubricsItem(models.Model):
    activity_question = models.ForeignKey(
        "ActivityQuestion", on_delete=models.CASCADE, null=True, blank=True
    )
    rubric = models.ForeignKey("Rubrics", on_delete=models.CASCADE, null=True, blank=True)
    point = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"{self.rubric} - {self.point}"
