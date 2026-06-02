# central_content/tests/test_views_staff.py
from django.test import TestCase, override_settings

from central_content.models import CentralStaff
from central_content.tests.factories import (
    make_editor, make_publisher,
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
class StaffViewTests(TestCase):
    def setUp(self):
        self.pub = make_publisher(email="p@example.com", password="pw")

    def _login(self, email):
        self.client.post("/login", {"email": email, "password": "pw"})

    def test_editor_cannot_access(self):
        make_editor(email="ed@example.com", password="pw")
        self._login("ed@example.com")
        resp = self.client.get("/staff/")
        self.assertEqual(resp.status_code, 403)

    def test_publisher_list(self):
        self._login("p@example.com")
        resp = self.client.get("/staff/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "p@example.com")

    def test_publisher_create(self):
        self._login("p@example.com")
        resp = self.client.post("/staff/new", {
            "email": "new@example.com",
            "full_name": "New One",
            "role": "editor",
            "password": "initialpw",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(CentralStaff.objects.filter(email="new@example.com").exists())

    def test_publisher_deactivate(self):
        target = make_editor(email="t@example.com", password="pw")
        self._login("p@example.com")
        resp = self.client.post(f"/staff/{target.id}/edit", {
            "email": target.email,
            "full_name": target.full_name,
            "role": target.role,
            "is_active": "",  # unchecked
        })
        self.assertEqual(resp.status_code, 302)
        target.refresh_from_db()
        self.assertFalse(target.is_active)
