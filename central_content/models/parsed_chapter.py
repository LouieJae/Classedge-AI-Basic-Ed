from django.db import models


class ParsedChapter(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PARSING = "parsing", "Parsing"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Failed"

    textbook = models.ForeignKey(
        "central_content.ParsedTextbook",
        on_delete=models.CASCADE,
        related_name="chapters",
    )
    chapter_number = models.PositiveIntegerField()
    title = models.CharField(max_length=200)
    start_page = models.PositiveIntegerField()
    end_page = models.PositiveIntegerField()
    parsed_data = models.JSONField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING,
    )
    error_message = models.TextField(blank=True)

    class Meta:
        app_label = "central_content"
        db_table = "central_content_parsed_chapter"
        ordering = ["chapter_number"]

    def __str__(self):
        return f"Ch.{self.chapter_number}: {self.title}"
