from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

User = get_user_model()


@override_settings(
    MIDDLEWARE=[
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "accounts.middleware.LegalConsentRequiredMiddleware",
    ]
)
class LegalConsentMiddlewareTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="u", email="u@e.com", password="pw", legal_update_required=True
        )

    def test_blocks_html_request_with_redirect(self):
        self.client.login(username="u", password="pw")
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accept-legal/", response["Location"])

    def test_api_request_gets_409(self):
        self.client.login(username="u", password="pw")
        response = self.client.get("/api/some-other/", HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"], "legal_update_required")

    def test_allowlisted_paths_pass_through(self):
        self.client.login(username="u", password="pw")
        for path in [
            "/accept-legal/",
            "/api/me/legal-status/",
            "/api/legal-consents/accept-all/",
            "/api/legal-documents/active/",
            "/static/x.css",
        ]:
            response = self.client.get(path)
            # Not a 302 back to /accept-legal/ and not a 409.
            self.assertNotEqual(response.status_code, 302, f"{path} redirected")
            self.assertNotEqual(response.status_code, 409, f"{path} 409d")

    def test_user_without_flag_passes_through(self):
        self.user.legal_update_required = False
        self.user.save(update_fields=["legal_update_required"])
        self.client.login(username="u", password="pw")
        response = self.client.get("/dashboard/")
        self.assertNotEqual(response.status_code, 302)

    def test_anonymous_passes_through(self):
        response = self.client.get("/dashboard/")
        # Middleware does nothing; whatever the view returns is fine.
        self.assertNotEqual(response.status_code, 409)
