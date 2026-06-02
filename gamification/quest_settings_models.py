from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

PROVIDER_CHOICES = [("anthropic", "Anthropic"), ("openai", "OpenAI")]


class OrganizationQuestSettings(models.Model):
    """[Classedge LMS] Singleton config for quest authoring modes & AI provider."""
    ai_mode_enabled = models.BooleanField(default=True)
    manual_mode_enabled = models.BooleanField(default=True)
    upload_mode_enabled = models.BooleanField(default=True)
    ai_provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default="anthropic")
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        verbose_name = "Organization Quest Settings"
        verbose_name_plural = "Organization Quest Settings"

    def __str__(self):
        return "Organization Quest Settings"

    def clean(self):
        if not (self.ai_mode_enabled or self.manual_mode_enabled or self.upload_mode_enabled):
            raise ValidationError("At least one authoring mode must remain enabled.")

    def save(self, *args, **kwargs):
        self.pk = 1
        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
