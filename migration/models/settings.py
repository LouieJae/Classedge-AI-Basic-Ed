from django.conf import settings as django_settings
from django.db import models


class MigrationSettings(models.Model):
    """Singleton row holding runtime-editable connection settings.
    Falls back to env-derived defaults when the row hasn't been edited yet.
    """

    base_url = models.CharField(max_length=500, blank=True, default="")
    token = models.CharField(max_length=500, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        verbose_name = "Migration settings"
        verbose_name_plural = "Migration settings"

    def __str__(self) -> str:
        return f"MigrationSettings(base_url={self.base_url or '(env)'})"

    @classmethod
    def load(cls) -> "MigrationSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def effective_base_url(self) -> str:
        return self.base_url or django_settings.MIGRATION_OLD_LMS_BASE_URL

    def effective_token(self) -> str:
        return self.token or django_settings.MIGRATION_OLD_LMS_TOKEN
