import json
from unittest.mock import patch, MagicMock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from central_content.models import ParsedTextbook, ParsedChapter, CurriculumPlan
from central_content.tests.factories import (
    make_editor, make_publisher, make_subject, make_school, make_binding,
    make_textbook,
)

_LLM_SETTINGS = {
    "CURRICULUM_PLANNER_MODELS": {
        "haiku": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5-20251001",
            "api_key_env": "ANTHROPIC_API_KEY",
        },
    },
    "CURRICULUM_PLANNER_DEFAULT_MODEL": "haiku",
}

_VALID_PLAN = [
    {"week": 1, "chapters": [1, 2, 3], "title": "Foundations", "description": "Intro"},
    {"week": 2, "chapters": [4, 5], "title": "Advanced", "description": "More"},
]

_SCHEDULE_RESPONSE = {
    "subject_id": 42,
    "subject_name": "Math 101",
    "term": {"name": "Prelim", "start_date": "2026-08-15", "end_date": "2026-10-15"},
    "sessions": [{"date": "2026-08-16", "start_time": "08:00", "end_time": "09:30", "minutes": 90}] * 30,
    "session_count": 30,
    "minutes_per_session": 90,
}


@override_settings(**_LLM_SETTINGS)
class GenerateCurriculumPlanTaskTests(TestCase):
    def setUp(self):
        self.editor = make_editor()
        self.publisher = make_publisher()
        self.subject = make_subject(created_by=self.editor)
        self.school = make_school(created_by=self.publisher)
        self.binding = make_binding(
            central_subject=self.subject,
            target_school=self.school,
            school_subject_id=42,
            bound_by=self.publisher,
        )
        self.textbook = make_textbook(
            central_subject=self.subject,
            uploaded_by=self.editor,
            num_chapters=5,
        )

    @patch("central_content.tasks.call_curriculum_planner")
    @patch("central_content.tasks.requests.get")
    def test_success_creates_draft_plan(self, mock_get, mock_llm):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _SCHEDULE_RESPONSE
        mock_get.return_value = mock_resp
        mock_llm.return_value = _VALID_PLAN

        from central_content.tasks import generate_curriculum_plan
        result = generate_curriculum_plan(
            self.textbook.pk, self.binding.pk, "haiku", self.publisher.pk,
        )

        self.assertEqual(result["status"], "success")
        plan = CurriculumPlan.objects.get(textbook=self.textbook)
        self.assertEqual(plan.status, CurriculumPlan.Status.DRAFT)
        self.assertEqual(plan.model_key, "haiku")
        self.assertEqual(plan.session_count, 30)
        self.assertEqual(len(plan.plan_data), 2)

    @patch("central_content.tasks.call_curriculum_planner")
    @patch("central_content.tasks.requests.get")
    def test_schedule_fetch_failure(self, mock_get, mock_llm):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = "not found"
        mock_get.return_value = mock_resp

        from central_content.tasks import generate_curriculum_plan
        result = generate_curriculum_plan(
            self.textbook.pk, self.binding.pk, "haiku", self.publisher.pk,
        )

        self.assertEqual(result["status"], "error")
        self.assertIn("schedule", result["detail"].lower())
        self.assertEqual(CurriculumPlan.objects.count(), 0)

    @patch("central_content.tasks.call_curriculum_planner")
    @patch("central_content.tasks.requests.get")
    def test_llm_failure_returns_error(self, mock_get, mock_llm):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _SCHEDULE_RESPONSE
        mock_get.return_value = mock_resp
        mock_llm.side_effect = ValueError("LLM returned invalid JSON")

        from central_content.tasks import generate_curriculum_plan
        result = generate_curriculum_plan(
            self.textbook.pk, self.binding.pk, "haiku", self.publisher.pk,
        )

        self.assertEqual(result["status"], "error")
        self.assertEqual(CurriculumPlan.objects.count(), 0)

    @patch("central_content.tasks.call_curriculum_planner")
    @patch("central_content.tasks.requests.get")
    def test_invalid_plan_retries_then_stores_with_warnings(self, mock_get, mock_llm):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _SCHEDULE_RESPONSE
        mock_get.return_value = mock_resp

        bad_plan = [
            {"week": 1, "chapters": [1, 2], "title": "A", "description": ""},
            {"week": 2, "chapters": [4, 5], "title": "B", "description": ""},
        ]
        mock_llm.return_value = bad_plan

        from central_content.tasks import generate_curriculum_plan
        result = generate_curriculum_plan(
            self.textbook.pk, self.binding.pk, "haiku", self.publisher.pk,
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(mock_llm.call_count, 2)
        plan = CurriculumPlan.objects.get(textbook=self.textbook)
        self.assertEqual(plan.status, CurriculumPlan.Status.DRAFT)


@override_settings(**_LLM_SETTINGS)
class BulkGeneratePlansTaskTests(TestCase):
    def setUp(self):
        self.editor = make_editor()
        self.publisher = make_publisher()
        self.subject = make_subject(created_by=self.editor)
        self.school = make_school(created_by=self.publisher)
        self.binding = make_binding(
            central_subject=self.subject,
            target_school=self.school,
            school_subject_id=42,
            bound_by=self.publisher,
        )

    @patch("central_content.tasks.generate_curriculum_plan.delay")
    def test_dispatches_per_textbook(self, mock_delay):
        tb1 = make_textbook(
            central_subject=self.subject,
            uploaded_by=self.editor,
            status=ParsedTextbook.Status.TOC_READY,
        )
        tb2 = make_textbook(
            central_subject=self.subject,
            uploaded_by=self.editor,
            status=ParsedTextbook.Status.TOC_READY,
        )
        make_textbook(
            central_subject=self.subject,
            uploaded_by=self.editor,
            status=ParsedTextbook.Status.UPLOADING,
        )

        from central_content.tasks import bulk_generate_plans
        result = bulk_generate_plans(
            self.subject.pk, self.binding.pk, "haiku", self.publisher.pk,
        )

        self.assertEqual(mock_delay.call_count, 2)
        self.assertEqual(result["dispatched"], 2)
