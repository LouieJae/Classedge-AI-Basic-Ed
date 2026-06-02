"""[Classedge LMS] Tests the post_save signal that syncs is_superuser with IT Admin role."""
from django.test import TestCase

from accounts.models.account_models import CustomUser, Profile
from roles.models import Role


class ItAdminSignalTests(TestCase):
    def setUp(self):
        self.it_admin_role, _ = Role.objects.get_or_create(name="IT Admin")
        self.teacher_role, _ = Role.objects.get_or_create(name="Teacher")

    def _make_user(self, suffix):
        return CustomUser.objects.create_user(
            username=f"u_{suffix}",
            email=f"u_{suffix}@x.io",
            password="x",
        )

    def test_assigning_it_admin_role_promotes_to_superuser(self):
        """[Classedge LMS] Saving a Profile with role=IT Admin must set user.is_superuser=True."""
        user = self._make_user("a")
        self.assertFalse(user.is_superuser)
        # Note: Profile auto-created by CustomUser post_save signal; update the existing one.
        profile = Profile.objects.get(user=user)
        profile.role = self.it_admin_role
        profile.save()
        user.refresh_from_db()
        self.assertTrue(user.is_superuser)

    def test_changing_role_away_from_it_admin_demotes_superuser(self):
        """[Classedge LMS] Switching role from IT Admin to Teacher must clear is_superuser."""
        user = self._make_user("b")
        profile = Profile.objects.get(user=user)
        profile.role = self.it_admin_role
        profile.save()
        user.refresh_from_db()
        self.assertTrue(user.is_superuser)
        profile.role = self.teacher_role
        profile.save()
        user.refresh_from_db()
        self.assertFalse(user.is_superuser)

    def test_no_role_clears_superuser(self):
        """[Classedge LMS] A profile with no role must not be a superuser."""
        user = self._make_user("c")
        profile = Profile.objects.get(user=user)
        profile.role = self.it_admin_role
        profile.save()
        user.refresh_from_db()
        self.assertTrue(user.is_superuser)
        profile.role = None
        profile.save()
        user.refresh_from_db()
        self.assertFalse(user.is_superuser)

    def test_signal_is_idempotent(self):
        """[Classedge LMS] Saving the profile twice with the same IT Admin role must leave is_superuser stable AND issue no extra writes."""
        user = self._make_user("d")
        profile = Profile.objects.get(user=user)
        profile.role = self.it_admin_role
        profile.save()
        user.refresh_from_db()
        first_state = user.is_superuser

        # Second save on an already-consistent profile must not trigger user.save()
        # (guard: `if user.is_superuser != should_be_superuser`). Allow a small budget
        # for the profile.save itself + the cascade from signal_utils.py, but NO extra
        # UPDATE on accounts_customuser.
        with self.assertNumQueries(11):
            profile.save()

        user.refresh_from_db()
        self.assertEqual(user.is_superuser, first_state)
        self.assertTrue(user.is_superuser)


class ItAdminBackfillTests(TestCase):
    """[Classedge LMS] Guards that the backfill migration leaves all IT Admin profiles with is_superuser=True."""

    def test_existing_it_admin_profiles_have_superuser_flag(self):
        """[Classedge LMS] Every Profile with role 'IT Admin' must have is_superuser=True."""
        it_admin = Role.objects.filter(name="IT Admin").first()
        if not it_admin:
            self.skipTest("No IT Admin role in this test DB — backfill target absent.")
        for profile in Profile.objects.filter(role=it_admin).select_related("user"):
            self.assertTrue(
                profile.user.is_superuser,
                f"Profile {profile.user.username} has IT Admin role but is_superuser=False.",
            )


class CreateSuperuserCompatibilityTests(TestCase):
    """[Classedge LMS] Guards that Django's create_superuser() flow is not broken by the signal."""

    def test_create_superuser_keeps_is_superuser_true(self):
        """[Classedge LMS] After create_superuser + auto-created Profile (Student role), is_superuser stays True."""
        user = CustomUser.objects.create_superuser(
            username="su_compat",
            email="su_compat@x.io",
            password="x",
        )
        # Auto-created profile has Student role (default); signal must NOT demote is_superuser.
        user.refresh_from_db()
        self.assertTrue(
            user.is_superuser,
            "create_superuser() must leave is_superuser=True even though the auto-created Profile starts as Student.",
        )
