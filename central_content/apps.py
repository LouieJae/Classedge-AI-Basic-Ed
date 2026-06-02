# central_content/apps.py
from django.apps import AppConfig


class CentralContentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "central_content"
    verbose_name = "Central Content"
