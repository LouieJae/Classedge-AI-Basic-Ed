"""[Classedge LMS] Tests the seed_it_admin management command."""
from io import StringIO
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from accounts.models.account_models import CustomUser, Profile
from roles.models import Role


class SeedItAdminTests(TestCase):
    """[Classedge LMS] Behavior tests for the seed_it_admin management command."""

    def _run(self, **kwargs):
        out = StringIO()
        call_command("seed_it_admin", stdout=out, **kwargs)
        return out.getvalue()

    def test_creates_role_and_user_on_fresh_db(self):
        """[Classedge LMS] First run creates IT Admin role + user; signal flips is_superuser=True."""
        Role.objects.filter(name="IT Admin").delete()
        CustomUser.objects.filter(email="it@example.com").delete()
        self._run(email="it@example.com", password="seedpw1234")
        self.assertTrue(Role.objects.filter(name="IT Admin").exists())
        user = CustomUser.objects.get(email="it@example.com")
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.profile.role.name, "IT Admin")

    def test_idempotent_on_second_run(self):
        """[Classedge LMS] Second run with same args: no extra users/roles created."""
        Role.objects.filter(name="IT Admin").delete()
        CustomUser.objects.filter(email="it2@example.com").delete()
        self._run(email="it2@example.com", password="seedpw1234")
        self._run(email="it2@example.com", password="seedpw1234")
        self.assertEqual(CustomUser.objects.filter(email="it2@example.com").count(), 1)
        self.assertEqual(Role.objects.filter(name="IT Admin").count(), 1)

    def test_grants_role_to_existing_user(self):
        """[Classedge LMS] If a user with that email exists, grant them IT Admin; don't create a duplicate."""
        Role.objects.filter(name="IT Admin").delete()
        existing = CustomUser.objects.create_user(
            username="existing", email="exist@example.com", password="orig",
        )
        teacher_role, _ = Role.objects.get_or_create(name="Teacher")
        profile = Profile.objects.get(user=existing)
        profile.role = teacher_role
        profile.save()
        self._run(email="exist@example.com", password="seedpw1234")
        existing.refresh_from_db()
        self.assertTrue(existing.is_superuser)
        self.assertEqual(existing.profile.role.name, "IT Admin")
        # Password NOT reset unless --force-reset-password:
        self.assertTrue(existing.check_password("orig"))

    def test_force_reset_password_resets(self):
        """[Classedge LMS] --force-reset-password resets an existing user's password."""
        Role.objects.filter(name="IT Admin").delete()
        existing = CustomUser.objects.create_user(
            username="exist2", email="exist2@example.com", password="origpw",
        )
        teacher_role, _ = Role.objects.get_or_create(name="Teacher")
        profile = Profile.objects.get(user=existing)
        profile.role = teacher_role
        profile.save()
        self._run(email="exist2@example.com", password="newpw5678", force_reset_password=True)
        existing.refresh_from_db()
        self.assertTrue(existing.check_password("newpw5678"))

    @override_settings(DEBUG=False)
    def test_missing_email_in_production_errors(self):
        """[Classedge LMS] DEBUG=False + no email arg + no env var: raise CommandError."""
        Role.objects.filter(name="IT Admin").delete()
        import os
        with patch.dict("os.environ", {}, clear=False):
            os.environ.pop("IT_ADMIN_EMAIL", None)
            os.environ.pop("IT_ADMIN_PASSWORD", None)
            with self.assertRaises(CommandError):
                self._run()

    def test_dry_run_changes_nothing(self):
        """[Classedge LMS] --dry-run prints intent without touching the DB."""
        Role.objects.filter(name="IT Admin").delete()
        CustomUser.objects.filter(email="dry@example.com").delete()
        self._run(email="dry@example.com", password="seedpw1234", dry_run=True)
        self.assertFalse(Role.objects.filter(name="IT Admin").exists())
        self.assertFalse(CustomUser.objects.filter(email="dry@example.com").exists())
