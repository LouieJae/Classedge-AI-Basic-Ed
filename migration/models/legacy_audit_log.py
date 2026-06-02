from django.db import models


class LegacyAuditLog(models.Model):
    """Archive table for source-side audit/log rows that have no destination
    table on the new LMS. Stores the raw payload as JSON plus a few indexed
    metadata fields for filtering.

    Currently used for `logs.UserActivityLog` (dropped in new schema). Could be
    extended to hold any other "preserve raw, never re-render" archive data.
    """

    source_app = models.CharField(max_length=64)
    source_model = models.CharField(max_length=64)
    source_pk = models.CharField(max_length=64)
    occurred_at = models.DateTimeField(null=True, blank=True)
    payload = models.JSONField(default=dict)
    archived_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("source_app", "source_model", "source_pk")]
        indexes = [
            models.Index(fields=["source_app", "source_model", "-occurred_at"]),
            models.Index(fields=["source_app", "source_model", "source_pk"]),
        ]
        ordering = ["-occurred_at"]

    def __str__(self) -> str:
        return f"{self.source_app}.{self.source_model} #{self.source_pk}"
