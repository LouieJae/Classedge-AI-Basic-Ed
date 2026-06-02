import os
import uuid

from django.db import models


def _received_module_file_path(instance, filename):
    new_name = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
    return os.path.join("received_central", "module", new_name)


class ReceivedCentralModule(models.Model):
    received_subject = models.ForeignKey(
        "received_central_content.ReceivedCentralSubject",
        on_delete=models.CASCADE,
        related_name="modules",
    )
    central_id = models.IntegerField(unique=True)

    file_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to=_received_module_file_path, blank=True, null=True)
    url = models.URLField(max_length=1500, blank=True)
    iframe_code = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = "received_central_content"
        db_table = "received_central_module"
        ordering = ["order"]

    def __str__(self):
        return self.file_name
