import json
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings

from central_content.models import (
    CentralModule, CentralActivity, ContentGenerationJob, ParsedChapter,
)
from central_content.tests.factories import (
    make_editor, make_publisher, make_subject, make_textbook,
    make_curriculum_plan, make_content_generation_job,
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

_LLM_RESULT = {
    "lesson_description": "This week covers foundations of algebra.",
    "quiz_questions": "1. What is a variable?\nA) A number\nB) A letter\nC) A symbol representing a value\nD) An equation\nAnswer: C",
}


@override_settings(**_LLM_SETTINGS)
class GenerateWeekContentTaskTests(TestCase):
    def setUp(self):
        self.editor = make_editor()
        self.publisher = make_publisher()
        self.subject = make_subject(created_by=self.editor)
        self.textbook = make_textbook(
            central_subject=self.subject,
            uploaded_by=self.editor,
            num_chapters=5,
        )
        # Set chapters to COMPLETE with parsed_data
        for ch in self.textbook.chapters.all():
            ch.status = ParsedChapter.Status.COMPLETE
            ch.parsed_data = {"text": f"Content for chapter {ch.chapter_number}..."}
            ch.save(update_fields=["status", "parsed_data"])

        self.plan = make_curriculum_plan(
            textbook=self.textbook,
            generated_by=self.publisher,
        )
        self.job = make_content_generation_job(
            curriculum_plan=self.plan,
            triggered_by=self.publisher,
        )

    @patch("central_content.content_tasks.call_content_generator")
    def test_success_creates_module_and_activity(self, mock_llm):
        from activity.models.activity_model import ActivityType
        ActivityType.objects.get_or_create(name="Quiz")
        mock_llm.return_value = _LLM_RESULT

        from central_content.content_tasks import generate_week_content
        generate_week_content(self.job.pk, 0)

        self.assertEqual(CentralModule.objects.filter(central_subject=self.subject).count(), 1)
        self.assertEqual(CentralActivity.objects.filter(central_subject=self.subject).count(), 1)

        module = CentralModule.objects.get(central_subject=self.subject)
        self.assertEqual(module.state, CentralModule.State.DRAFT)
        self.assertIn("Week 1", module.file_name)
        self.assertEqual(module.description, _LLM_RESULT["lesson_description"])
        self.assertEqual(module.created_by, self.publisher)

        activity = CentralActivity.objects.get(central_subject=self.subject)
        self.assertEqual(activity.state, CentralActivity.State.DRAFT)
        self.assertIn("Week 1", activity.activity_name)
        self.assertEqual(activity.activity_instruction, _LLM_RESULT["quiz_questions"])
        self.assertEqual(activity.max_score, 100)
        self.assertEqual(activity.time_duration, 30)
        self.assertTrue(activity.related_modules.filter(pk=module.pk).exists())

        self.job.refresh_from_db()
        self.assertEqual(self.job.week_results[0]["status"], "done")
        self.assertEqual(self.job.week_results[0]["module_id"], module.pk)

    @patch("central_content.content_tasks.call_content_generator")
    def test_unparsed_chapter_triggers_parsing(self, mock_llm):
        from activity.models.activity_model import ActivityType
        ActivityType.objects.get_or_create(name="Quiz")
        mock_llm.return_value = _LLM_RESULT

        # Reset first chapter to pending
        ch = self.textbook.chapters.first()
        ch.status = ParsedChapter.Status.PENDING
        ch.parsed_data = None
        ch.save(update_fields=["status", "parsed_data"])

        with patch("central_content.content_tasks.parse_single_chapter") as mock_parse:
            def side_effect(chapter_id):
                c = ParsedChapter.objects.get(pk=chapter_id)
                c.status = ParsedChapter.Status.COMPLETE
                c.parsed_data = {"text": "Parsed content"}
                c.save(update_fields=["status", "parsed_data"])
                return {"status": "success"}
            mock_parse.apply = MagicMock(side_effect=lambda args: side_effect(args[0]))

            from central_content.content_tasks import generate_week_content
            generate_week_content(self.job.pk, 0)

        mock_parse.apply.assert_called()
        self.assertEqual(CentralModule.objects.filter(central_subject=self.subject).count(), 1)

    @patch("central_content.content_tasks.call_content_generator")
    def test_chapter_parse_failure_marks_week_failed(self, mock_llm):
        # Reset first chapter to pending, it won't get parsed_data
        ch = self.textbook.chapters.first()
        ch.status = ParsedChapter.Status.PENDING
        ch.parsed_data = None
        ch.save(update_fields=["status", "parsed_data"])

        with patch("central_content.content_tasks.parse_single_chapter") as mock_parse:
            def side_effect(chapter_id):
                c = ParsedChapter.objects.get(pk=chapter_id)
                c.status = ParsedChapter.Status.FAILED
                c.error_message = "MinerU error"
                c.save(update_fields=["status", "error_message"])
                return {"status": "error"}
            mock_parse.apply = MagicMock(side_effect=lambda args: side_effect(args[0]))

            from central_content.content_tasks import generate_week_content
            generate_week_content(self.job.pk, 0)

        self.job.refresh_from_db()
        self.assertEqual(self.job.week_results[0]["status"], "failed")
        self.assertIn("parse", self.job.week_results[0]["error"].lower())
        self.assertEqual(self.job.failed_weeks, 1)
        mock_llm.assert_not_called()

    @patch("central_content.content_tasks.call_content_generator")
    def test_llm_failure_marks_week_failed(self, mock_llm):
        from activity.models.activity_model import ActivityType
        ActivityType.objects.get_or_create(name="Quiz")
        mock_llm.side_effect = ValueError("LLM returned invalid JSON")

        from central_content.content_tasks import generate_week_content
        generate_week_content(self.job.pk, 0)

        self.job.refresh_from_db()
        self.assertEqual(self.job.week_results[0]["status"], "failed")
        self.assertEqual(self.job.failed_weeks, 1)
        self.assertEqual(CentralModule.objects.filter(central_subject=self.subject).count(), 0)


@override_settings(**_LLM_SETTINGS)
class RunContentGenerationTaskTests(TestCase):
    def setUp(self):
        self.editor = make_editor()
        self.publisher = make_publisher()
        self.subject = make_subject(created_by=self.editor)
        self.textbook = make_textbook(
            central_subject=self.subject,
            uploaded_by=self.editor,
            num_chapters=5,
        )
        for ch in self.textbook.chapters.all():
            ch.status = ParsedChapter.Status.COMPLETE
            ch.parsed_data = {"text": f"Content for chapter {ch.chapter_number}"}
            ch.save(update_fields=["status", "parsed_data"])

        self.plan = make_curriculum_plan(
            textbook=self.textbook,
            generated_by=self.publisher,
        )
        self.job = make_content_generation_job(
            curriculum_plan=self.plan,
            triggered_by=self.publisher,
        )

    @patch("central_content.content_tasks.generate_week_content")
    def test_runs_all_weeks_and_completes(self, mock_gen):
        from central_content.content_tasks import run_content_generation
        run_content_generation(self.job.pk)

        self.assertEqual(mock_gen.call_count, len(self.plan.plan_data))
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, ContentGenerationJob.Status.COMPLETE)

    @patch("central_content.content_tasks.generate_week_content")
    def test_sets_running_status(self, mock_gen):
        statuses = []
        def capture_status(job_id, week_idx):
            job = ContentGenerationJob.objects.get(pk=job_id)
            statuses.append(job.status)
        mock_gen.side_effect = capture_status

        from central_content.content_tasks import run_content_generation
        run_content_generation(self.job.pk)

        self.assertIn(ContentGenerationJob.Status.RUNNING, statuses)
