from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import LegalDocument


class ActiveLegalDocumentsTests(APITestCase):
    url = "/api/legal-documents/active/"

    def test_anonymous_can_read(self):
        LegalDocument.objects.create(
            doc_type="EULA", version="1.0.0", title="E", content="<p>a</p>", is_active=True
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["eula"]["version"], "1.0.0")
        self.assertIsNone(body["privacy"])
        self.assertIsNone(body["nda"])
        self.assertEqual(sorted(body["missing"]), ["NDA", "PRIVACY"])

    def test_only_active_is_returned(self):
        LegalDocument.objects.create(
            doc_type="EULA", version="0.9.0", title="E", content="<p>old</p>", is_active=False
        )
        LegalDocument.objects.create(
            doc_type="EULA", version="1.0.0", title="E", content="<p>new</p>", is_active=True
        )
        response = self.client.get(self.url)
        self.assertEqual(response.json()["eula"]["version"], "1.0.0")


class ActiveLegalDocumentByTypeTests(APITestCase):
    def test_found(self):
        LegalDocument.objects.create(
            doc_type="NDA", version="1.0.0", title="N", content="<p>n</p>", is_active=True
        )
        response = self.client.get("/api/legal-documents/active/NDA/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["version"], "1.0.0")

    def test_missing_returns_404(self):
        response = self.client.get("/api/legal-documents/active/NDA/")
        self.assertEqual(response.status_code, 404)

    def test_invalid_type_returns_404(self):
        response = self.client.get("/api/legal-documents/active/BOGUS/")
        self.assertEqual(response.status_code, 404)


from django.contrib.auth import get_user_model
from accounts.models import UserLegalConsent

User = get_user_model()


class LegalStatusTests(APITestCase):
    url = "/api/me/legal-status/"

    def setUp(self):
        self.user = User.objects.create_user(
            username="s", email="s@e.com", password="x"
        )
        self.client.force_authenticate(self.user)

    def test_requires_authentication(self):
        from rest_framework.test import APIClient
        anon = APIClient()
        self.assertEqual(anon.get(self.url).status_code, 401)

    def test_no_active_docs_means_no_acceptance_needed(self):
        body = self.client.get(self.url).json()
        self.assertFalse(body["needsAcceptance"])
        self.assertEqual(body["pending"], [])

    def test_pending_doc_without_acceptance(self):
        LegalDocument.objects.create(
            doc_type="EULA", version="1.0.0", title="E", content="<p>a</p>", is_active=True
        )
        body = self.client.get(self.url).json()
        self.assertTrue(body["needsAcceptance"])
        self.assertEqual(body["pending"], ["EULA"])

    def test_accepted_doc_not_pending(self):
        doc = LegalDocument.objects.create(
            doc_type="EULA", version="1.0.0", title="E", content="<p>a</p>", is_active=True
        )
        UserLegalConsent.objects.create(user=self.user, document=doc)
        body = self.client.get(self.url).json()
        self.assertFalse(body["needsAcceptance"])
        self.assertEqual(body["pending"], [])


class AcceptAllTests(APITestCase):
    url = "/api/legal-consents/accept-all/"

    def setUp(self):
        self.user = User.objects.create_user(
            username="u", email="u@e.com", password="x", legal_update_required=True
        )
        self.eula = LegalDocument.objects.create(
            doc_type="EULA", version="1.0.0", title="E", content="<p>e</p>", is_active=True
        )
        self.privacy = LegalDocument.objects.create(
            doc_type="PRIVACY", version="2.0.0", title="P", content="<p>p</p>", is_active=True
        )
        self.nda = LegalDocument.objects.create(
            doc_type="NDA", version="1.0.0", title="N", content="<p>n</p>", is_active=True
        )
        self.client.force_authenticate(self.user)

    def test_requires_authentication(self):
        from rest_framework.test import APIClient
        anon = APIClient()
        self.assertEqual(anon.post(self.url, {"accepted": True}).status_code, 401)

    def test_accept_creates_rows_and_updates_snapshots(self):
        response = self.client.post(
            self.url, {"accepted": True}, HTTP_USER_AGENT="Mozilla/UA"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(sorted(response.json()["accepted"]), ["EULA", "NDA", "PRIVACY"])

        self.assertEqual(UserLegalConsent.objects.filter(user=self.user).count(), 3)
        row = UserLegalConsent.objects.get(user=self.user, document=self.eula)
        self.assertEqual(row.user_agent, "Mozilla/UA")

        self.user.refresh_from_db()
        self.assertFalse(self.user.legal_update_required)
        self.assertEqual(self.user.accepted_eula_version, "1.0.0")
        self.assertEqual(self.user.accepted_privacy_version, "2.0.0")
        self.assertEqual(self.user.accepted_nda_version, "1.0.0")

    def test_idempotent(self):
        self.client.post(self.url, {"accepted": True})
        response = self.client.post(self.url, {"accepted": True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(UserLegalConsent.objects.filter(user=self.user).count(), 3)

    def test_no_active_docs_returns_400(self):
        LegalDocument.objects.update(is_active=False)
        response = self.client.post(self.url, {"accepted": True})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "no_documents_to_accept")


class JWTPendingClaimTests(APITestCase):
    def test_helper_lists_missing_types(self):
        from accounts.views.user_views import _pending_legal_doc_types
        user = User.objects.create_user("jwt", "jwt@e.com", "x", legal_update_required=True)
        LegalDocument.objects.create(
            doc_type="EULA", version="1.0.0", title="E", content="<p>a</p>", is_active=True
        )
        LegalDocument.objects.create(
            doc_type="NDA", version="1.0.0", title="N", content="<p>n</p>", is_active=True
        )
        self.assertCountEqual(_pending_legal_doc_types(user), ["EULA", "NDA"])

    def test_helper_excludes_already_accepted(self):
        from accounts.views.user_views import _pending_legal_doc_types
        user = User.objects.create_user("jwt2", "jwt2@e.com", "x")
        eula = LegalDocument.objects.create(
            doc_type="EULA", version="1.0.0", title="E", content="<p>a</p>", is_active=True
        )
        LegalDocument.objects.create(
            doc_type="NDA", version="1.0.0", title="N", content="<p>n</p>", is_active=True
        )
        UserLegalConsent.objects.create(user=user, document=eula)
        self.assertCountEqual(_pending_legal_doc_types(user), ["NDA"])


class AcceptLegalPageTests(APITestCase):
    url = "/accept-legal/"

    def setUp(self):
        self.user = User.objects.create_user(
            "gate", "gate@e.com", "x", legal_update_required=True
        )
        self.eula = LegalDocument.objects.create(
            doc_type="EULA", version="1.0.0", title="E", content="<p>eula-content</p>", is_active=True
        )

    def test_anonymous_redirected(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/", response["Location"])

    def test_authenticated_renders_active_docs(self):
        self.client.login(username="gate", password="x")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "eula-content")
        self.assertContains(response, "I have read and agree")
