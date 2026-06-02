from django.test import TestCase, override_settings

from central_content.models import School
from central_content.tests.factories import (
    make_publisher, make_editor, make_reviewer, make_school,
)

_SAFE_TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

_OVERRIDES = dict(
    ROOT_URLCONF="central_content.urls",
    AUTHENTICATION_BACKENDS=["central_content.auth_backends.CentralStaffAuthBackend"],
    TEMPLATES=_SAFE_TEMPLATES,
)


@override_settings(**_OVERRIDES)
class SchoolsViewsTests(TestCase):
    def setUp(self):
        self.pub = make_publisher(email="pub@example.com", password="pw")
        self.rev = make_reviewer(email="rev@example.com", password="pw")
        self.ed = make_editor(email="ed@example.com", password="pw")

    def _login(self, email):
        self.client.post("/login", {"email": email, "password": "pw"})

    def test_list_requires_login(self):
        resp = self.client.get("/schools/")
        self.assertEqual(resp.status_code, 302)

    def test_list_publisher_sees_page(self):
        self._login("pub@example.com")
        make_school(name="HCCCI")
        resp = self.client.get("/schools/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "HCCCI")

    def test_list_reviewer_read_only(self):
        self._login("rev@example.com")
        resp = self.client.get("/schools/")
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Add school")

    def test_list_editor_forbidden(self):
        self._login("ed@example.com")
        resp = self.client.get("/schools/")
        self.assertEqual(resp.status_code, 403)

    def test_create_publisher(self):
        self._login("pub@example.com")
        resp = self.client.post("/schools/new", {
            "name": "New School",
            "base_url": "https://new.example.com",
            "notes": "",
            "is_active": "on",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(School.objects.filter(name="New School").exists())
        school = School.objects.get(name="New School")
        self.assertEqual(len(school.api_token), 40)
        self.assertContains(resp, school.api_token)

    def test_create_editor_forbidden(self):
        self._login("ed@example.com")
        resp = self.client.post("/schools/new", {"name": "X", "base_url": "https://x"})
        self.assertEqual(resp.status_code, 403)

    def test_edit_updates_fields(self):
        self._login("pub@example.com")
        school = make_school(name="Old Name")
        resp = self.client.post(f"/schools/{school.pk}/edit", {
            "name": "New Name",
            "base_url": school.base_url,
            "notes": "",
            "is_active": "on",
        }, follow=True)
        school.refresh_from_db()
        self.assertEqual(school.name, "New Name")

    def test_regenerate_token(self):
        self._login("pub@example.com")
        school = make_school()
        old_token = school.api_token
        self.client.post(f"/schools/{school.pk}/regenerate-token")
        school.refresh_from_db()
        self.assertNotEqual(school.api_token, old_token)
        self.assertEqual(len(school.api_token), 40)
