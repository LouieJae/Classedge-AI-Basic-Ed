# central_content/models/central_staff.py
from django.contrib.auth.hashers import make_password, check_password
from django.db import models
from django.utils import timezone


class CentralStaffManager(models.Manager):
    def create_user(self, email, full_name, password, role):
        if not email:
            raise ValueError("Email is required")
        staff = self.model(
            email=email.lower().strip(),
            full_name=full_name,
            role=role,
        )
        staff.set_password(password)
        staff.save()
        return staff


class CentralStaff(models.Model):
    class Role(models.TextChoices):
        EDITOR = "editor", "Editor"
        REVIEWER = "reviewer", "Reviewer"
        PUBLISHER = "publisher", "Publisher"

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=Role.choices)
    password = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = CentralStaffManager()

    class Meta:
        app_label = "central_content"
        db_table = "central_content_staff"
        ordering = ["email"]

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

    # ---- Django auth-ish shims (enough for request.user.is_authenticated) ----
    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def get_session_auth_hash(self):
        """Return a stable HMAC-based hash used to invalidate sessions on password change."""
        import hmac
        import hashlib
        from django.conf import settings
        key = settings.SECRET_KEY.encode()
        return hmac.new(key, self.password.encode(), hashlib.sha256).hexdigest()

    def get_session_auth_fallback_hash(self):
        return []
