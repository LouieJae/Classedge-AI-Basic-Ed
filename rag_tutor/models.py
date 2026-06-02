from django.db import models
from pgvector.django import VectorField


class ContentChunk(models.Model):
    class SourceType(models.TextChoices):
        MODULE = "module", "Module"
        ACTIVITY = "activity", "Activity"
        CHAPTER = "chapter", "Chapter"

    subject = models.ForeignKey(
        "subject.Subject", on_delete=models.CASCADE, related_name="content_chunks",
    )
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    source_id = models.PositiveIntegerField()
    source_title = models.CharField(max_length=200)
    chunk_index = models.PositiveIntegerField()
    text = models.TextField()
    embedding = VectorField(dimensions=1536)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("source_type", "source_id", "chunk_index")]
        ordering = ["source_type", "source_id", "chunk_index"]

    def __str__(self):
        return f"{self.source_title} chunk {self.chunk_index}"


class ChatMessage(models.Model):
    subject = models.ForeignKey(
        "subject.Subject", on_delete=models.CASCADE, related_name="chat_messages",
    )
    student = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.CASCADE, related_name="tutor_messages",
    )
    question = models.TextField()
    answer = models.TextField()
    sources = models.JSONField(default=list)
    had_relevant_chunks = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Q: {self.question[:50]}"
