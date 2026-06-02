from django.conf import settings
from django.db import models
from django.utils import timezone


class LegalDocument(models.Model):
    DOC_TYPE_CHOICES = [
        ("EULA", "End User License Agreement"),
        ("PRIVACY", "Privacy Policy"),
        ("NDA", "Non-Disclosure Agreement"),
    ]

    doc_type = models.CharField(max_length=10, choices=DOC_TYPE_CHOICES)
    version = models.CharField(max_length=10)
    title = models.CharField(max_length=255)
    content = models.TextField()
    is_active = models.BooleanField(default=False)
    effective_date = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authored_legal_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("doc_type", "version")
        verbose_name = "Legal Document"
        verbose_name_plural = "Legal Documents"
        ordering = ["doc_type", "-effective_date"]

    def __str__(self):
        flag = " (active)" if self.is_active else ""
        return f"{self.doc_type} v{self.version}{flag}"

    def save(self, *args, **kwargs):
        from accounts.utils.legal_sanitize import sanitize_legal_html

        self.content = sanitize_legal_html(self.content or "")
        super().save(*args, **kwargs)


class UserLegalConsent(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="legal_consents",
    )
    document = models.ForeignKey(
        LegalDocument,
        on_delete=models.PROTECT,
        related_name="acceptances",
    )
    accepted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "document")
        verbose_name = "User Legal Consent"
        verbose_name_plural = "User Legal Consents"
        indexes = [
            models.Index(fields=["user", "document"], name="ulc_user_doc_idx"),
        ]

    def __str__(self):
        return f"{self.user.email} accepted {self.document}"
