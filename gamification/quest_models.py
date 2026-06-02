from django.conf import settings
from django.db import models


class Quest(models.Model):
    KIND_CHOICES = [("quiz", "Quiz"), ("reading_check", "Reading Check"), ("task", "Task")]
    STATUS_CHOICES = [("draft", "Draft"), ("published", "Published")]

    module = models.ForeignKey("module.Module", on_delete=models.CASCADE, related_name="quests")
    order = models.PositiveIntegerField(default=1)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    title = models.CharField(max_length=200)
    body = models.TextField()
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    counts_toward_grade = models.BooleanField(default=True)
    ai_provider = models.CharField(max_length=20, blank=True)
    source_chunk = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["module", "order"]

    def __str__(self):
        return f"{self.module_id}#{self.order} {self.title[:30]}"


class QuestAttempt(models.Model):
    quest = models.ForeignKey(Quest, on_delete=models.CASCADE, related_name="attempts")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    submitted_answer = models.JSONField(default=dict)
    is_correct = models.BooleanField(default=False)
    score = models.FloatField(default=0.0)
    completed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("quest", "student")


class QuestGenerationJob(models.Model):
    STATUS_CHOICES = [
        ("queued", "Queued"), ("running", "Running"),
        ("complete", "Complete"), ("failed", "Failed"),
    ]
    module = models.ForeignKey("module.Module", on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="queued")
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["module", "status"])]
