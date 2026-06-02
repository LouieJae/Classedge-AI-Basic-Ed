"""[Classedge LMS] Phase 2 data migration — verify role-permission grants.

We exercise the real RunPython callbacks via the migration's PHASE2_GRANTS
constant so the test cannot drift from the migration's intent.
"""
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from roles.migrations._m0004_grant_phase2_perms_helper import (  # see Step 2
    PHASE2_GRANTS,
    grant_phase2_perms,
    revoke_phase2_perms,
)
from roles.models import Role


def _resolve(app_label, codename):
    model_name = codename.split("_", 1)[1]
    ct = ContentType.objects.get(app_label=app_label, model=model_name)
    return Permission.objects.get(content_type=ct, codename=codename)


class _AppsShim:
    """Tiny wrapper so we can call grant/revoke against real models in a test."""

    def get_model(self, app_label, model_name):
        from django.apps import apps as real_apps
        return real_apps.get_model(app_label, model_name)


class Phase2DataMigrationTests(TestCase):
    """[Classedge LMS] grant_phase2_perms/revoke_phase2_perms are idempotent and behavior-preserving."""

    def setUp(self):
        # Create every role mentioned in PHASE2_GRANTS so we exercise all rows.
        for role_name in PHASE2_GRANTS.keys():
            Role.objects.get_or_create(name=role_name)

    def _expected_perm_ids(self, role_name):
        codenames = PHASE2_GRANTS[role_name]
        return {_resolve(app, code).id for app, code in codenames}

    def test_forward_grants_expected_perms_per_role(self):
        grant_phase2_perms(_AppsShim(), None)
        for role_name in PHASE2_GRANTS:
            role = Role.objects.get(name=role_name)
            actual = set(role.permissions.values_list("id", flat=True))
            expected = self._expected_perm_ids(role_name)
            self.assertTrue(
                expected.issubset(actual),
                f"Role '{role_name}' missing perms after forward migration: "
                f"{expected - actual}",
            )

    def test_forward_is_idempotent(self):
        grant_phase2_perms(_AppsShim(), None)
        before = {
            r.name: set(r.permissions.values_list("id", flat=True))
            for r in Role.objects.all()
        }
        grant_phase2_perms(_AppsShim(), None)  # second run
        after = {
            r.name: set(r.permissions.values_list("id", flat=True))
            for r in Role.objects.all()
        }
        self.assertEqual(before, after)

    def test_reverse_removes_granted_perms(self):
        grant_phase2_perms(_AppsShim(), None)
        revoke_phase2_perms(_AppsShim(), None)
        for role_name in PHASE2_GRANTS:
            role = Role.objects.get(name=role_name)
            actual = set(role.permissions.values_list("id", flat=True))
            expected = self._expected_perm_ids(role_name)
            self.assertTrue(
                expected.isdisjoint(actual),
                f"Role '{role_name}' still has Phase 2 perms after reverse: "
                f"{expected & actual}",
            )

    def test_missing_role_is_skipped_not_crashed(self):
        Role.objects.filter(name="Program Head").delete()
        # Must not raise.
        grant_phase2_perms(_AppsShim(), None)
