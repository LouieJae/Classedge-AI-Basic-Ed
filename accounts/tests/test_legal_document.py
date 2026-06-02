from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from accounts.models import LegalDocument


class LegalDocumentModelTests(TestCase):
    def test_create_with_defaults(self):
        doc = LegalDocument.objects.create(
            doc_type="EULA",
            version="1.0.0",
            title="End User License Agreement",
            content="<p>Terms.</p>",
        )
        self.assertFalse(doc.is_active)
        self.assertIsNotNone(doc.effective_date)
        self.assertLessEqual(doc.created_at, timezone.now())

    def test_unique_doc_type_version(self):
        LegalDocument.objects.create(
            doc_type="EULA", version="1.0.0", title="E", content="<p>a</p>"
        )
        with self.assertRaises(IntegrityError):
            LegalDocument.objects.create(
                doc_type="EULA", version="1.0.0", title="E2", content="<p>b</p>"
            )


class LegalDocumentSanitizationTests(TestCase):
    def test_strips_script_tag(self):
        doc = LegalDocument.objects.create(
            doc_type="EULA",
            version="1.0.0",
            title="E",
            content="<p>Safe</p><script>alert(1)</script>",
        )
        self.assertIn("<p>Safe</p>", doc.content)
        self.assertNotIn("<script>", doc.content)
        self.assertNotIn("alert(1)", doc.content)

    def test_strips_javascript_href(self):
        doc = LegalDocument.objects.create(
            doc_type="PRIVACY",
            version="1.0.0",
            title="P",
            content='<a href="javascript:alert(1)">bad</a>',
        )
        self.assertNotIn("javascript:", doc.content)

    def test_keeps_safe_tags(self):
        safe = "<h2>Hello</h2><p><strong>Bold</strong> and <em>italic</em>.</p><ul><li>one</li></ul>"
        doc = LegalDocument.objects.create(
            doc_type="NDA", version="1.0.0", title="N", content=safe
        )
        for fragment in ["<h2>", "<strong>", "<em>", "<ul>", "<li>"]:
            self.assertIn(fragment, doc.content)


from django.contrib.auth import get_user_model

from accounts.models import UserLegalConsent

User = get_user_model()


class LegalDocumentActivationSignalTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            username="alice", email="alice@example.com", password="x"
        )
        self.bob = User.objects.create_user(
            username="bob", email="bob@example.com", password="x"
        )
        # Both start cleared.
        User.objects.all().update(legal_update_required=False)

    def test_activating_new_doc_deactivates_sibling(self):
        old = LegalDocument.objects.create(
            doc_type="EULA", version="1.0.0", title="E", content="<p>a</p>", is_active=True
        )
        new = LegalDocument.objects.create(
            doc_type="EULA", version="1.1.0", title="E", content="<p>b</p>", is_active=True
        )
        old.refresh_from_db()
        self.assertFalse(old.is_active)
        self.assertTrue(new.is_active)

    def test_activating_flags_users_who_have_not_accepted(self):
        doc = LegalDocument.objects.create(
            doc_type="EULA", version="1.0.0", title="E", content="<p>a</p>", is_active=True
        )
        # Only alice has accepted this doc.
        UserLegalConsent.objects.create(user=self.alice, document=doc)

        # Publish v1.1.0 — alice must re-accept, bob too.
        LegalDocument.objects.create(
            doc_type="EULA", version="1.1.0", title="E", content="<p>b</p>", is_active=True
        )
        self.alice.refresh_from_db()
        self.bob.refresh_from_db()
        self.assertTrue(self.alice.legal_update_required)
        self.assertTrue(self.bob.legal_update_required)

    def test_saving_inactive_doc_is_a_noop(self):
        LegalDocument.objects.create(
            doc_type="EULA", version="1.0.0", title="E", content="<p>a</p>", is_active=False
        )
        self.alice.refresh_from_db()
        self.assertFalse(self.alice.legal_update_required)
