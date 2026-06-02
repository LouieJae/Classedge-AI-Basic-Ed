# central_content/tests/test_auth.py
from django.core.management import call_command
from django.test import TestCase, override_settings

from central_content.models import CentralStaff


@override_settings(ROOT_URLCONF="central_content.urls")
class CentralAuthTests(TestCase):
    def test_login_page_renders(self):
        resp = self.client.get("/login")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Email")

    def test_login_success(self):
        CentralStaff.objects.create_user(
            email="editor@example.com", full_name="Ed", password="pw12345",
            role=CentralStaff.Role.EDITOR,
        )
        resp = self.client.post(
            "/login",
            {"email": "editor@example.com", "password": "pw12345"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/")

    def test_login_failure(self):
        CentralStaff.objects.create_user(
            email="e@example.com", full_name="E", password="correct",
            role=CentralStaff.Role.EDITOR,
        )
        resp = self.client.post(
            "/login", {"email": "e@example.com", "password": "wrong"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Invalid")

    def test_logout_clears_session(self):
        CentralStaff.objects.create_user(
            email="u@example.com", full_name="U", password="pw",
            role=CentralStaff.Role.EDITOR,
        )
        self.client.post("/login", {"email": "u@example.com", "password": "pw"})
        resp = self.client.post("/logout")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/login")


class CreateCentralStaffCommandTests(TestCase):
    def test_command_creates_user(self):
        call_command(
            "create_central_staff",
            email="boot@example.com",
            full_name="Boot",
            role="publisher",
            password="bootpw123",
        )
        staff = CentralStaff.objects.get(email="boot@example.com")
        self.assertEqual(staff.role, "publisher")
        self.assertTrue(staff.check_password("bootpw123"))
