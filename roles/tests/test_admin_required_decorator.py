"""[Classedge LMS] Verify @admin_required gates strictly on is_superuser (post-Phase-1 simplification)."""
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from accounts.models.account_models import CustomUser, Profile
from roles.decorators import admin_required
from roles.models import Role


@admin_required
def _dummy_view(request):
    """[Classedge LMS] Minimal gated view used only by the decorator test suite."""
    return HttpResponse("ok")


class AdminRequiredDecoratorTests(TestCase):
    """[Classedge LMS] Post-Phase-1 @admin_required gates strictly on is_superuser."""

    def setUp(self):
        self.factory = RequestFactory()
        self.it_admin_role, _ = Role.objects.get_or_create(name="IT Admin")
        self.teacher_role, _ = Role.objects.get_or_create(name="Teacher")

    def _request_as(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_superuser_passes(self):
        """[Classedge LMS] Superuser with IT Admin role passes."""
        user = CustomUser.objects.create_superuser(
            username="su", email="su@x.io", password="x",
        )
        # Profile auto-created by signal_utils; update its role to IT Admin.
        profile = Profile.objects.get(user=user)
        profile.role = self.it_admin_role
        profile.save()
        user.refresh_from_db()  # sync signal may update is_superuser on DB; reload here
        resp = _dummy_view(self._request_as(user))
        self.assertEqual(resp.status_code, 200)

    def test_teacher_denied(self):
        """[Classedge LMS] Teacher (non-superuser) must be denied."""
        user = CustomUser.objects.create_user(
            username="t", email="t@x.io", password="x",
        )
        profile = Profile.objects.get(user=user)
        profile.role = self.teacher_role
        profile.save()
        with self.assertRaises(PermissionDenied):
            _dummy_view(self._request_as(user))

    def test_anonymous_denied(self):
        """[Classedge LMS] Anonymous requests are denied."""
        request = self.factory.get("/")
        request.user = AnonymousUser()
        with self.assertRaises(PermissionDenied):
            _dummy_view(request)
