from unittest.mock import patch, MagicMock
from datetime import date

from django.test import TestCase, Client, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile

from ai_content.models import GenerationRequest
from ai_content.tests.test_models import _create_test_user, _create_subject
from course.models.semester_model import Semester
from course.models.term_model import Term
from subject.models.subject_model import Subject

_OVERRIDES = dict(
    AI_CONTENT_MODELS={
        "haiku": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5-20251001",
            "api_key_env": "ANTHROPIC_API_KEY",
        },
    },
    AI_CONTENT_DEFAULT_MODEL="haiku",
)


@override_settings(**_OVERRIDES)
class GenerateContentViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = _create_test_user(username="teacher1", role_name="teacher")
        self.student = _create_test_user(username="student1", role_name="student")
        self.subject = _create_subject()
        # Assign teacher to subject
        Subject.objects.filter(pk=self.subject.pk).update(assign_teacher=self.teacher)
        self.subject.refresh_from_db()

        self.semester = Semester.objects.create(
            semester_name="First Semester",
            start_date=date(2026, 1, 1),
            end_date=date(2027, 12, 31),
        )
        self.term = Term.objects.create(
            term_name="Prelim",
            semester=self.semester,
            start_date=date(2026, 8, 15),
            end_date=date(2026, 10, 15),
        )

    def test_form_renders_for_teacher(self):
        self.client.login(username="teacher1", password="testpass")
        resp = self.client.get(f"/ai-content/generate/{self.subject.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Generate with AI")
        self.assertContains(resp, "haiku")

    def test_student_cannot_access(self):
        self.client.login(username="student1", password="testpass")
        resp = self.client.get(f"/ai-content/generate/{self.subject.pk}/")
        self.assertEqual(resp.status_code, 302)

    @patch("ai_content.views.generate_school_content.delay")
    def test_post_creates_request_and_redirects(self, mock_delay):
        self.client.login(username="teacher1", password="testpass")
        resp = self.client.post(
            f"/ai-content/generate/{self.subject.pk}/",
            {
                "term_id": self.term.pk,
                "topic": "Algebra Basics",
                "objectives": "Learn variables and expressions",
                "content_type": "both",
                "model_key": "haiku",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(GenerationRequest.objects.count(), 1)
        req = GenerationRequest.objects.first()
        self.assertEqual(req.topic, "Algebra Basics")
        self.assertEqual(req.content_type, "both")
        mock_delay.assert_called_once_with(req.pk)

    def test_unauthenticated_redirects_to_login(self):
        resp = self.client.get(f"/ai-content/generate/{self.subject.pk}/")
        self.assertEqual(resp.status_code, 302)
        # Project LOGIN_URL resolves to '/' (admin_login_view); confirm redirect
        # contains the next param pointing back at the generate URL.
        self.assertIn("next", resp.url.lower())

    @patch("ai_content.views.generate_school_content.delay")
    def test_rejects_non_pdf_file(self, mock_delay):
        self.client.login(username="teacher1", password="testpass")
        bad_file = SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain")
        resp = self.client.post(
            f"/ai-content/generate/{self.subject.pk}/",
            {
                "term_id": self.term.pk,
                "topic": "Test",
                "objectives": "Test",
                "content_type": "both",
                "model_key": "haiku",
                "reference_file": bad_file,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(GenerationRequest.objects.count(), 0)
        mock_delay.assert_not_called()
