"""[Classedge LMS] Behavioral tests for the Admin → IT Admin rename and orphan teacher merge migrations."""
import importlib

from django.apps import apps
from django.test import TestCase

from roles.models import Role


class AdminRenameMigrationTests(TestCase):
    """[Classedge LMS] Exercises rename_admin_to_it_admin + reverse in isolation."""

    def setUp(self):
        """[Classedge LMS] Seed an Admin role; clear any IT Admin from prior test runs."""
        Role.objects.filter(name__in=["Admin", "IT Admin"]).delete()
        Role.objects.create(name="Admin")
        self.migration = importlib.import_module(
            "roles.migrations.0002_rename_admin_to_it_admin"
        )

    def test_forward_renames_admin_to_it_admin(self):
        """[Classedge LMS] Forward migration: Admin row becomes IT Admin."""
        self.migration.rename_admin_to_it_admin(apps, None)
        self.assertFalse(
            Role.objects.filter(name="Admin").exists(),
            "Admin should have been renamed to IT Admin.",
        )
        self.assertTrue(
            Role.objects.filter(name="IT Admin").exists(),
            "IT Admin should exist after forward migration.",
        )

    def test_reverse_renames_it_admin_back_to_admin(self):
        """[Classedge LMS] Reverse migration: IT Admin row becomes Admin."""
        self.migration.rename_admin_to_it_admin(apps, None)
        self.migration.rename_it_admin_back_to_admin(apps, None)
        self.assertTrue(
            Role.objects.filter(name="Admin").exists(),
            "Reverse migration should restore the Admin row.",
        )
        self.assertFalse(
            Role.objects.filter(name="IT Admin").exists(),
            "Reverse migration should remove the IT Admin row.",
        )


class OrphanTeacherMergeMigrationTests(TestCase):
    """[Classedge LMS] Exercises merge_orphan_teacher + reverse in isolation."""

    def setUp(self):
        """[Classedge LMS] Seed canonical Teacher, orphan teacher, and a Profile member of the orphan."""
        from accounts.models.account_models import CustomUser, Profile

        Role.objects.filter(name__in=["Teacher", "teacher"]).delete()
        self.canonical = Role.objects.create(name="Teacher")
        self.orphan = Role.objects.create(name="teacher")

        self.user = CustomUser.objects.create_user(
            username="orphan_member",
            email="orphan_member@x.io",
            password="x",
        )
        # Signal auto-creates a Profile; update its role to the orphan to simulate the data state.
        self.profile = Profile.objects.get(user=self.user)
        self.profile.role = self.orphan
        self.profile.save()

        self.migration = importlib.import_module(
            "roles.migrations.0003_merge_orphan_teacher_role"
        )

    def test_forward_reassigns_profile_and_deletes_orphan(self):
        """[Classedge LMS] Forward migration: profile on 'teacher' moves to 'Teacher'; orphan deleted."""
        self.migration.merge_orphan_teacher(apps, None)
        self.assertFalse(
            Role.objects.filter(name="teacher").exists(),
            "Orphan 'teacher' role should be deleted.",
        )
        self.assertTrue(
            Role.objects.filter(name="Teacher").exists(),
            "Canonical 'Teacher' role should remain.",
        )
        self.profile.refresh_from_db()
        self.assertEqual(
            self.profile.role.name,
            "Teacher",
            "Profile should be reassigned to the canonical Teacher role.",
        )

    def test_reverse_recreates_empty_orphan_role(self):
        """[Classedge LMS] Reverse migration: recreate orphan role (profile NOT restored to it; documented loss)."""
        self.migration.merge_orphan_teacher(apps, None)
        self.migration.restore_orphan_teacher(apps, None)
        self.assertTrue(
            Role.objects.filter(name="teacher").exists(),
            "Reverse migration should recreate the empty orphan role.",
        )
        self.profile.refresh_from_db()
        self.assertEqual(
            self.profile.role.name,
            "Teacher",
            "Profile stays with canonical Teacher after reverse (reassignment is not restored).",
        )
