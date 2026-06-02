"""[Classedge LMS] Phase 2 — verify legacy role-name decorators are gone."""
from django.test import TestCase


class LegacyDecoratorsRemovedTests(TestCase):
    """[Classedge LMS] roles.decorators must not expose the four role-name decorators."""

    LEGACY_NAMES = (
        "teacher_required",
        "student_required",
        "registrar_required",
        "teacher_or_admin_required",
    )

    def test_legacy_decorators_not_importable(self):
        import roles.decorators as d
        for name in self.LEGACY_NAMES:
            self.assertFalse(
                hasattr(d, name),
                f"{name} should have been deleted in Phase 2 but is still in roles.decorators",
            )

    def test_admin_required_still_present(self):
        """[Classedge LMS] @admin_required is intentionally kept (Phase 1's superuser shim)."""
        import roles.decorators as d
        self.assertTrue(hasattr(d, "admin_required"))
