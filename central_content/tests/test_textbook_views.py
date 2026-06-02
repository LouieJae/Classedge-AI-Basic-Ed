# central_content/tests/test_textbook_views.py
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from central_content.models import ParsedTextbook, ParsedChapter
from central_content.tests.factories import (
    make_editor, make_publisher, make_reviewer, make_subject,
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


def _fake_pdf():
    return SimpleUploadedFile("test.pdf", b"%PDF-fake", content_type="application/pdf")


@override_settings(**_OVERRIDES)
class TextbookUploadViewTests(TestCase):
    def setUp(self):
        self.publisher = make_publisher(email="pub@example.com", password="testpass")
        self.editor = make_editor(email="ed@example.com", password="testpass")
        self.reviewer = make_reviewer(email="rev@example.com", password="testpass")
        self.subject = make_subject(created_by=self.editor)

    def _login(self, email):
        self.client.post("/login", {"email": email, "password": "testpass"})

    def test_upload_form_renders_for_publisher(self):
        self._login("pub@example.com")
        resp = self.client.get(f"/subjects/{self.subject.pk}/textbooks/upload")
        self.assertEqual(resp.status_code, 200)

    def test_upload_form_renders_for_editor(self):
        self._login("ed@example.com")
        resp = self.client.get(f"/subjects/{self.subject.pk}/textbooks/upload")
        self.assertEqual(resp.status_code, 200)

    def test_upload_forbidden_for_reviewer(self):
        self._login("rev@example.com")
        resp = self.client.get(f"/subjects/{self.subject.pk}/textbooks/upload")
        self.assertIn(resp.status_code, [302, 403])

    @patch("central_content.views.textbooks.parse_textbook_toc.delay")
    def test_upload_creates_textbook_and_triggers_task(self, mock_delay):
        self._login("pub@example.com")
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/upload",
            {"title": "My Textbook", "file": _fake_pdf()},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ParsedTextbook.objects.count(), 1)
        tb = ParsedTextbook.objects.first()
        self.assertEqual(tb.title, "My Textbook")
        mock_delay.assert_called_once_with(tb.pk)

    @patch("central_content.views.textbooks.parse_textbook_toc.delay")
    def test_upload_rejects_non_pdf(self, mock_delay):
        self._login("pub@example.com")
        bad_file = SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain")
        self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/upload",
            {"title": "Bad File", "file": bad_file},
        )
        self.assertEqual(ParsedTextbook.objects.count(), 0)
        mock_delay.assert_not_called()


@override_settings(**_OVERRIDES)
class TextbookDetailViewTests(TestCase):
    def setUp(self):
        self.editor = make_editor(email="ed2@example.com", password="testpass")
        self.client.post("/login", {"email": "ed2@example.com", "password": "testpass"})
        self.subject = make_subject(created_by=self.editor)
        self.textbook = ParsedTextbook.objects.create(
            central_subject=self.subject,
            title="Detail Book",
            original_file=_fake_pdf(),
            uploaded_by=self.editor,
            status=ParsedTextbook.Status.TOC_READY,
        )

    def test_detail_renders(self):
        resp = self.client.get(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Detail Book")

    def test_status_badge_endpoint(self):
        resp = self.client.get(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/status"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Ready")


@override_settings(**_OVERRIDES)
class SubjectDetailTextbookSectionTests(TestCase):
    def setUp(self):
        self.editor = make_editor(email="ed3@example.com", password="testpass")
        self.client.post("/login", {"email": "ed3@example.com", "password": "testpass"})
        self.subject = make_subject(created_by=self.editor)

    def test_subject_detail_shows_textbooks_section(self):
        resp = self.client.get(f"/subjects/{self.subject.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Textbooks")
        self.assertContains(resp, "Upload textbook")

    def test_subject_detail_lists_textbook(self):
        ParsedTextbook.objects.create(
            central_subject=self.subject,
            title="Listed Textbook",
            original_file=_fake_pdf(),
            uploaded_by=self.editor,
        )
        resp = self.client.get(f"/subjects/{self.subject.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Listed Textbook")
