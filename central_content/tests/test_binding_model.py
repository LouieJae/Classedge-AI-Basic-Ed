from django.db import IntegrityError
from django.test import TestCase

from central_content.models import SchoolSubjectBinding
from central_content.tests.factories import (
    make_binding, make_subject, make_publisher, make_school,
)


class BindingModelTests(TestCase):
    def test_create_binding_fields(self):
        b = make_binding()
        self.assertIsNone(b.pushed_version)
        self.assertIsNone(b.last_pushed_at)
        self.assertIsNotNone(b.bound_at)

    def test_unique_constraint(self):
        subject = make_subject()
        school = make_school()
        make_binding(central_subject=subject, target_school=school)
        with self.assertRaises(IntegrityError):
            make_binding(central_subject=subject, target_school=school)

    def test_drift_state_never_pushed(self):
        b = make_binding(pushed_version=None)
        self.assertEqual(b.drift_state, "never")

    def test_drift_state_up_to_date(self):
        subject = make_subject(version=3)
        b = make_binding(central_subject=subject, pushed_version=3)
        self.assertEqual(b.drift_state, "up_to_date")

    def test_drift_state_drift(self):
        subject = make_subject(version=5)
        b = make_binding(central_subject=subject, pushed_version=3)
        self.assertEqual(b.drift_state, "drift")

    def test_cascade_from_central_subject(self):
        b = make_binding()
        b.central_subject.delete()
        self.assertFalse(
            SchoolSubjectBinding.objects.filter(pk=b.pk).exists()
        )
