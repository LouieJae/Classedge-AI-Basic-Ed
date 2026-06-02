import secrets

from django.test import TestCase

from central_content.models import School
from central_content.tests.factories import make_publisher, make_school


class SchoolModelTests(TestCase):
    def test_create_school_generates_token(self):
        publisher = make_publisher()
        school = School.objects.create(
            name="HCCCI",
            base_url="https://classedge.hccci.edu.ph",
            api_token=secrets.token_hex(20),
            created_by=publisher,
        )
        self.assertEqual(len(school.api_token), 40)
        self.assertTrue(school.is_active)
        self.assertEqual(school.notes, "")

    def test_default_is_active_true(self):
        school = make_school()
        self.assertTrue(school.is_active)

    def test_str_is_name(self):
        school = make_school(name="HCCCI")
        self.assertEqual(str(school), "HCCCI")

    def test_name_required(self):
        publisher = make_publisher()
        with self.assertRaises(Exception):
            School.objects.create(
                name="",
                base_url="https://x",
                api_token="t" * 40,
                created_by=publisher,
            ).full_clean()

    def test_created_by_protect(self):
        school = make_school()
        with self.assertRaises(Exception):
            school.created_by.delete()
