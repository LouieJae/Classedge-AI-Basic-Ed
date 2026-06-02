import json
from unittest.mock import patch, MagicMock
from datetime import date

from django.test import TestCase, Client, override_settings

from rag_tutor.models import ContentChunk
from ai_content.tests.test_models import _create_test_user, _create_subject
from subject.models.subject_model import Subject
from course.models.semester_model import Semester
from course.models.subject_enrollment_model import SubjectEnrollment

_RAG_SETTINGS = {
    "RAG_TUTOR_EMBEDDING_MODEL": "text-embedding-3-small",
    "RAG_TUTOR_LLM_MODEL": "claude-haiku-4-5-20251001",
    "RAG_TUTOR_TOP_K": 5,
    "RAG_TUTOR_RELEVANCE_THRESHOLD": 0.8,
}


@override_settings(**_RAG_SETTINGS)
class AskEndpointTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = _create_test_user(username="teacher_rag", role_name="teacher")
        self.student = _create_test_user(username="student_rag", role_name="student")
        self.subject = _create_subject()
        Subject.objects.filter(pk=self.subject.pk).update(assign_teacher=self.teacher)
        self.subject.refresh_from_db()

        self.semester = Semester.objects.create(
            semester_name="First Semester",
            start_date=date(2026, 1, 1),
            end_date=date(2027, 12, 31),
        )
        SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            semester=self.semester,
            status="enrolled",
        )

        ContentChunk.objects.create(
            subject=self.subject,
            source_type="module",
            source_id=1,
            source_title="Test Module",
            chunk_index=0,
            text="Variables represent values.",
            embedding=[0.1] * 1536,
        )

    @patch("rag_tutor.query.anthropic.Anthropic")
    @patch("rag_tutor.query.embed_texts")
    def test_student_can_ask(self, mock_embed, MockAnthropic):
        mock_embed.return_value = [[0.1] * 1536]
        mock_block = MagicMock()
        mock_block.text = "A variable represents a value."
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = mock_response

        self.client.login(username="student_rag", password="testpass")
        resp = self.client.post(
            f"/rag-tutor/ask/{self.subject.pk}/",
            json.dumps({"question": "What is a variable?"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("answer", data)
        self.assertIn("sources", data)

    @patch("rag_tutor.query.anthropic.Anthropic")
    @patch("rag_tutor.query.embed_texts")
    def test_teacher_can_ask(self, mock_embed, MockAnthropic):
        mock_embed.return_value = [[0.1] * 1536]
        mock_block = MagicMock()
        mock_block.text = "Answer."
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = mock_response

        self.client.login(username="teacher_rag", password="testpass")
        resp = self.client.post(
            f"/rag-tutor/ask/{self.subject.pk}/",
            json.dumps({"question": "Test?"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_unauthenticated_returns_redirect(self):
        resp = self.client.post(
            f"/rag-tutor/ask/{self.subject.pk}/",
            json.dumps({"question": "Test?"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 302)

    def test_missing_question_returns_400(self):
        self.client.login(username="student_rag", password="testpass")
        resp = self.client.post(
            f"/rag-tutor/ask/{self.subject.pk}/",
            json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
