from unittest.mock import patch, MagicMock
from datetime import date

from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile

from ai_content.models import GenerationRequest
from ai_content.tests.test_models import _create_test_user, _create_subject
from activity.models.activity_model import Activity, ActivityType
from module.models.module import Module
from course.models.semester_model import Semester
from course.models.term_model import Term

_LLM_SETTINGS = {
    "AI_CONTENT_MODELS": {
        "haiku": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5-20251001",
            "api_key_env": "ANTHROPIC_API_KEY",
        },
    },
    "AI_CONTENT_DEFAULT_MODEL": "haiku",
}

_BOTH_RESULT = {
    "lesson_description": "This lesson covers algebra fundamentals.",
    "quiz_questions": "1. What is x?\nA) Number\nB) Variable\nAnswer: B",
}

_MODULE_RESULT = {
    "lesson_description": "Lesson outline for geometry.",
}

_QUIZ_RESULT = {
    "quiz_questions": "1. What is a triangle?\nAnswer: A 3-sided polygon",
}


@override_settings(**_LLM_SETTINGS)
class GenerateSchoolContentTaskTests(TestCase):
    def setUp(self):
        self.user = _create_test_user()
        self.subject = _create_subject()
        self.semester = Semester.objects.create(
            semester_name="First Semester",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 15),
        )
        self.term = Term.objects.create(
            term_name="Prelim",
            semester=self.semester,
            start_date=date(2026, 8, 15),
            end_date=date(2026, 10, 15),
        )
        ActivityType.objects.get_or_create(name="Quiz")

    def _make_request(self, content_type="both", **kw):
        defaults = {
            "subject": self.subject,
            "term": self.term,
            "requested_by": self.user,
            "topic": "Algebra Basics",
            "objectives": "Learn variables",
            "content_type": content_type,
            "model_key": "haiku",
        }
        defaults.update(kw)
        return GenerationRequest.objects.create(**defaults)

    @patch("ai_content.tasks.call_school_content_generator")
    def test_both_creates_module_and_activity(self, mock_llm):
        mock_llm.return_value = _BOTH_RESULT
        req = self._make_request(content_type="both")

        from ai_content.tasks import generate_school_content
        generate_school_content(req.pk)

        req.refresh_from_db()
        self.assertEqual(req.status, GenerationRequest.Status.COMPLETE)
        self.assertIsNotNone(req.generated_module_id)
        self.assertIsNotNone(req.generated_activity_id)

        module = Module.objects.get(pk=req.generated_module_id)
        self.assertEqual(module.file_name, "Algebra Basics")
        self.assertEqual(module.description, _BOTH_RESULT["lesson_description"])
        self.assertEqual(module.subject, self.subject)
        self.assertEqual(module.term, self.term)

        activity = Activity.objects.get(pk=req.generated_activity_id)
        self.assertEqual(activity.activity_name, "Algebra Basics Quiz")
        self.assertEqual(activity.activity_instruction, _BOTH_RESULT["quiz_questions"])
        self.assertTrue(activity.additional_modules.filter(pk=module.pk).exists())

    @patch("ai_content.tasks.call_school_content_generator")
    def test_module_only(self, mock_llm):
        mock_llm.return_value = _MODULE_RESULT
        req = self._make_request(content_type="module")

        from ai_content.tasks import generate_school_content
        generate_school_content(req.pk)

        req.refresh_from_db()
        self.assertEqual(req.status, GenerationRequest.Status.COMPLETE)
        self.assertIsNotNone(req.generated_module_id)
        self.assertIsNone(req.generated_activity_id)

    @patch("ai_content.tasks.call_school_content_generator")
    def test_quiz_only(self, mock_llm):
        mock_llm.return_value = _QUIZ_RESULT
        req = self._make_request(content_type="quiz")

        from ai_content.tasks import generate_school_content
        generate_school_content(req.pk)

        req.refresh_from_db()
        self.assertEqual(req.status, GenerationRequest.Status.COMPLETE)
        self.assertIsNone(req.generated_module_id)
        self.assertIsNotNone(req.generated_activity_id)

    @patch("ai_content.tasks.call_school_content_generator")
    @patch("ai_content.tasks.extract_text_from_pdf")
    def test_extracts_reference_pdf(self, mock_extract, mock_llm):
        mock_extract.return_value = "Extracted PDF text"
        mock_llm.return_value = _BOTH_RESULT

        pdf = SimpleUploadedFile("ref.pdf", b"%PDF-fake", content_type="application/pdf")
        req = self._make_request(reference_file=pdf)

        from ai_content.tasks import generate_school_content
        generate_school_content(req.pk)

        mock_extract.assert_called_once()
        req.refresh_from_db()
        self.assertEqual(req.reference_text, "Extracted PDF text")
        mock_llm.assert_called_once()
        call_kwargs = mock_llm.call_args.kwargs
        self.assertEqual(call_kwargs["reference_text"], "Extracted PDF text")

    @patch("ai_content.tasks.call_school_content_generator")
    def test_llm_failure_sets_failed(self, mock_llm):
        mock_llm.side_effect = ValueError("LLM error")
        req = self._make_request()

        from ai_content.tasks import generate_school_content
        generate_school_content(req.pk)

        req.refresh_from_db()
        self.assertEqual(req.status, GenerationRequest.Status.FAILED)
        self.assertIn("LLM error", req.error_message)
