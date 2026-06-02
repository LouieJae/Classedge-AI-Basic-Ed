# central_content/auth_backends.py
from central_content.models import CentralStaff


class CentralStaffAuthBackend:
    """Authenticates against CentralStaff. Wired in lms.settings_central."""

    def authenticate(self, request, email=None, password=None, **kwargs):
        if not email or not password:
            return None
        try:
            staff = CentralStaff.objects.get(email=email.lower().strip())
        except CentralStaff.DoesNotExist:
            return None
        if not staff.is_active:
            return None
        if staff.check_password(password):
            return staff
        return None

    def get_user(self, user_id):
        try:
            return CentralStaff.objects.get(pk=user_id, is_active=True)
        except CentralStaff.DoesNotExist:
            return None
