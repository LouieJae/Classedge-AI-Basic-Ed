from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import uuid
import os
from django.utils.timezone import now
import secrets
from mobile.models import Attachment

def get_upload_path(instance, filename):
    filename = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
    return os.path.join('profile', filename)

def get_upload_path_attachment(instance, filename):
    filename = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
    return os.path.join('attachments', filename)

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    needs_password_setup = models.BooleanField(default=True, null=True, blank=True)
    needs_onboarding = models.BooleanField(default=True, null=True, blank=True)
    legal_update_required = models.BooleanField(default=True, null=True, blank=True)
    otp = models.CharField(max_length=6, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    otp_attempts = models.IntegerField(default=0, null=True, blank=True)
    failed_otp_count = models.IntegerField(default=0, null=True, blank=True)
    failed_login_count = models.IntegerField(default=0, null=True, blank=True)
    otp_blocked_until = models.DateTimeField(null=True, blank=True) 
    account_locked_permanent = models.BooleanField(default=False)
    last_password_reset = models.DateTimeField(null=True, blank=True)
    accepted_eula_version = models.CharField(max_length=10, default='0.0.0')
    accepted_nda_version = models.CharField(max_length=10, default='0.0.0')
    accepted_privacy_version = models.CharField(max_length=10, default='0.0.0')
    # [Classedge LMS] Track which EULA / NDA / Privacy Policy versions the user has accepted.
    # "0.0.0" = not yet accepted. Columns already exist in production; SeparateDatabaseAndState
    # migrations bring them into the Django model graph idempotently.

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    def has_perm(self, perm, obj=None):
        if super().has_perm(perm, obj):
            return True

        if hasattr(self, 'profile') and self.profile.role:
            role_permissions = self.profile.role.permissions.all()
            if role_permissions.filter(codename=perm.split('.')[1]).exists():
                return True

        return False

    @property
    def role_name(self):
        profile = getattr(self, 'profile', None)
        role = getattr(profile, 'role', None) if profile else None
        return role.name.lower() if role and role.name else ''

    @property
    def is_student(self):
        return self.role_name == 'student'

    @property
    def is_teacher(self):
        return self.role_name == 'teacher'

    @property
    def is_admin(self):
        return self.role_name == 'admin'

    @property
    def is_program_head(self):
        return self.role_name == 'program head'

    @property
    def is_dean(self):
        return self.role_name == 'dean'

    @property
    def is_time_keeper(self):
        return self.role_name == 'time keeper'

    @property
    def is_parent(self):
        return self.role_name == 'parent'

    @property
    def is_registrar(self):
        return self.role_name == 'registrar'

    @property
    def is_academic_director(self):
        return self.role_name == 'academic director'

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    role = models.ForeignKey('roles.Role', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.BooleanField(default=True, null=True, blank=True)
    STATUS_TYPE = [
        ('Regular', 'Regular'),
        ('Irregular', 'Irregular'),
    ]
    student_status = models.CharField(max_length=15, choices=STATUS_TYPE, null=True, blank=True)

    #Personal Information
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    student_photo = models.ImageField(upload_to= get_upload_path, null=True, blank=True)
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other')
    ]
    
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    nationality = models.CharField(max_length=255, null=True, blank=True)

    #Contact Information
    address = models.TextField(null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)

    #Academic Information
    id_number = models.CharField(max_length=255, null=True, blank=True)
    YEAR_LEVEL_CHOICES = [
        ('1st Year College', '1st Year College'),
        ('2nd Year College', '2nd Year College'),
        ('3rd Year College', '3rd Year College'),
        ('4th Year College', '4th Year College'),
    ]
    grade_year_level = models.CharField(max_length=255, choices=YEAR_LEVEL_CHOICES, null=True, blank=True)
    course = models.ForeignKey('Course', on_delete=models.SET_NULL, null=True, blank=True)
    department_fields = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True)
    is_coil_user = models.BooleanField(default=False, null=True, blank=True)

    # Guided-tour completion, per account. Holds the Shepherd tour ids the
    # user has finished or dismissed, so a walkthrough never auto-shows again
    # for them on any browser or device.
    seen_tours = models.JSONField(default=list, blank=True)

    # Public profile sharing (opt-in). Token is random and unrelated to pk;
    # disabling share_enabled invalidates the public link without rotating.
    share_token = models.CharField(max_length=43, blank=True, default="", db_index=True)
    share_enabled = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def role_name(self):
        return self.role.name.lower() if self.role and self.role.name else ''

    @property
    def active_toggle_label(self):
        """Used by the user-list action menu to flip between
        'Deactivate' and 'Activate' based on the underlying user's flag."""
        return "Deactivate" if getattr(self.user, "is_active", True) else "Activate"

    @property
    def is_student(self):
        return self.role_name == 'student'

    @property
    def is_teacher(self):
        return self.role_name == 'teacher'

    @property
    def is_admin(self):
        return self.role_name == 'admin'

    @property
    def is_program_head(self):
        return self.role_name == 'program head'

    @property
    def is_dean(self):
        return self.role_name == 'dean'

    @property
    def is_time_keeper(self):
        return self.role_name == 'time keeper'

    @property
    def is_parent(self):
        return self.role_name == 'parent'

    @property
    def is_registrar(self):
        return self.role_name == 'registrar'

    @property
    def is_academic_director(self):
        return self.role_name == 'academic director'

    @property
    def is_it_admin(self):
        return self.role_name == 'it admin'

    def save(self, *args, **kwargs):
        # Check if this is a new profile or if student_photo is being changed
        is_new = self.pk is None
        old_photo = None
        
        if not is_new:
            # Get the old profile instance to check for photo changes
            try:
                old_profile = Profile.objects.get(pk=self.pk)
                old_photo = old_profile.student_photo
            except Profile.DoesNotExist:
                old_photo = None
        
        # Save the profile first
        super().save(*args, **kwargs)
        
        # Create attachment if student_photo was added or changed
        if self.student_photo and (is_new or old_photo != self.student_photo):
            Attachment.objects.create(
                profile=self,
                file=self.student_photo
            )

class LoginHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    login_time = models.DateTimeField(default=now)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)  # Optional: to track browser/device info

    def __str__(self):
        try:
            username = self.user.username
        except CustomUser.DoesNotExist:
            username = f"user#{self.user_id}"
        return f"{username} - {self.login_time} - IP: {self.ip_address}"


class APIKey(models.Model):
    """API key for external integrations

    Keys are random, opaque strings and should be kept secret. They can be
    associated with a user (owner) and optionally restricted by origin.
    """

    name = models.CharField(max_length=150, help_text="Label for this API key (e.g. website name)")
    key = models.CharField(max_length=64, unique=True, db_index=True, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="api_keys",
    )
    allowed_origin = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Optional origin/domain this key is restricted to (e.g. https://example.com)",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"

    def __str__(self):
        owner_str = str(self.owner) if self.owner else "unassigned"
        return f"{self.name} ({owner_str})"

    @staticmethod
    def generate_key() -> str:
        """Generate a new random API key string."""
        return secrets.token_urlsafe(32) 

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        super().save(*args, **kwargs)


