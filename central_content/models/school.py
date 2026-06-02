from django.db import models


class School(models.Model):
    name = models.CharField(max_length=100)
    base_url = models.URLField()
    api_token = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.PROTECT,
        related_name="schools_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "central_content"
        db_table = "central_content_school"
        ordering = ["name"]

    def __str__(self):
        return self.name
