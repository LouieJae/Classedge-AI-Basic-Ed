from django.db import models


class MigrationErrorRecord(models.Model):
    CATEGORY_CHOICES = [
        ("transport_error", "Transport error"),
        ("auth_error", "Auth error"),
        ("throttled", "Throttled"),
        ("mapper_error", "Mapper error"),
        ("missing_fk", "Missing FK"),
        ("validation", "Validation"),
        ("db_error", "DB error"),
        ("unknown", "Unknown"),
    ]

    job = models.ForeignKey("migration.MigrationJob", on_delete=models.CASCADE, related_name="errors")
    run_log = models.ForeignKey("migration.MigrationRunLog", on_delete=models.SET_NULL, null=True, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    old_app = models.CharField(max_length=64)
    old_model = models.CharField(max_length=64)
    old_pk = models.CharField(max_length=64, blank=True, default="")
    batch_cursor = models.CharField(max_length=128, blank=True, default="")
    batch_index = models.IntegerField(null=True, blank=True)

    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES)
    message = models.CharField(max_length=500)
    field = models.CharField(max_length=120, blank=True, default="")
    expected = models.CharField(max_length=500, blank=True, default="")
    actual = models.CharField(max_length=500, blank=True, default="")

    source_file = models.CharField(max_length=255, blank=True, default="")
    source_line = models.IntegerField(null=True, blank=True)
    source_function = models.CharField(max_length=120, blank=True, default="")
    traceback = models.TextField(blank=True, default="")

    payload_excerpt = models.JSONField(default=dict, blank=True)

    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["job", "category"]),
            models.Index(fields=["resolved", "category"]),
            models.Index(fields=["-occurred_at"]),
        ]
        ordering = ["-occurred_at"]
