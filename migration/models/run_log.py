from django.db import models


class MigrationRunLog(models.Model):
    job = models.ForeignKey("migration.MigrationJob", on_delete=models.CASCADE, related_name="run_logs")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    cursor_in = models.CharField(max_length=128, blank=True, default="")
    cursor_out = models.CharField(max_length=128, blank=True, default="")
    rows_in_page = models.IntegerField(default=0)
    rows_written = models.IntegerField(default=0)
    rows_skipped = models.IntegerField(default=0)
    rows_errored = models.IntegerField(default=0)
    http_status = models.IntegerField(null=True, blank=True)
    retry_attempt = models.IntegerField(default=0)
    is_retry = models.BooleanField(default=False)
    is_dry_run = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default="")

    class Meta:
        indexes = [models.Index(fields=["job", "-started_at"])]
        ordering = ["-started_at"]
