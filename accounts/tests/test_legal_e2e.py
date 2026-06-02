from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import LegalDocument, UserLegalConsent

User = get_user_model()


class LegalConsentHappyPathTests(TestCase):
    def test_publish_gate_accept_flow(self):
        user = User.objects.create_user(
            "e2e", "e2e@e.com", "pw", legal_update_required=False
        )

        # Admin publishes three active docs — triggers the flag.
        LegalDocument.objects.create(
            doc_type="EULA", version="1.0.0", title="E", content="<p>e</p>", is_active=True
        )
        LegalDocument.objects.create(
            doc_type="PRIVACY", version="1.0.0", title="P", content="<p>p</p>", is_active=True
        )
        LegalDocument.objects.create(
            doc_type="NDA", version="1.0.0", title="N", content="<p>n</p>", is_active=True
        )

        user.refresh_from_db()
        self.assertTrue(user.legal_update_required)

        # User logs in and hits the dashboard — redirected.
        self.client.login(username="e2e", password="pw")
        response = self.client.get("/dashboard/", follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accept-legal/", response["Location"])

        # User accepts via the API.
        response = self.client.post(
            "/api/legal-consents/accept-all/",
            data='{"accepted": true}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(UserLegalConsent.objects.filter(user=user).count(), 3)
        user.refresh_from_db()
        self.assertFalse(user.legal_update_required)

        # User can now hit a normal page without the redirect.
        response = self.client.get("/dashboard/", follow=False)
        self.assertNotEqual(response.status_code, 302)

    def test_new_version_reflags_existing_user(self):
        user = User.objects.create_user("e2e2", "e2@e.com", "pw")
        doc = LegalDocument.objects.create(
            doc_type="EULA", version="1.0.0", title="E", content="<p>a</p>", is_active=True
        )
        # User accepted v1.0.0.
        user.legal_update_required = False
        user.accepted_eula_version = "1.0.0"
        user.save()
        UserLegalConsent.objects.create(user=user, document=doc)

        # Admin publishes v1.1.0.
        LegalDocument.objects.create(
            doc_type="EULA", version="1.1.0", title="E", content="<p>b</p>", is_active=True
        )

        user.refresh_from_db()
        self.assertTrue(user.legal_update_required)
