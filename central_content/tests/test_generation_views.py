from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings

from central_content.models import ContentGenerationJob, CurriculumPlan
from central_content.tests.factories import (
    make_editor, make_publisher, make_reviewer, make_subject,
    make_textbook, make_curriculum_plan, make_content_generation_job,
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
    CURRICULUM_PLANNER_MODELS={
        "haiku": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5-20251001",
            "api_key_env": "ANTHROPIC_API_KEY",
        },
    },
    CURRICULUM_PLANNER_DEFAULT_MODEL="haiku",
)


@override_settings(**_OVERRIDES)
class TriggerGenerationViewTests(TestCase):
    def setUp(self):
        self.publisher = make_publisher(email="pub@example.com", password="testpass")
        self.editor = make_editor(email="ed@example.com", password="testpass")
        self.subject = make_subject(created_by=self.editor)
        self.textbook = make_textbook(
            central_subject=self.subject,
            uploaded_by=self.editor,
            num_chapters=5,
        )
        self.plan = make_curriculum_plan(
            textbook=self.textbook,
            generated_by=self.publisher,
            status=CurriculumPlan.Status.APPROVED,
        )

    def _login(self, email):
        self.client.post("/login", {"email": email, "password": "testpass"})

    @patch("central_content.views.generation.run_content_generation.delay")
    def test_post_triggers_task_and_redirects(self, mock_delay):
        self._login("pub@example.com")
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/generate-content",
            {"model_key": "haiku"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ContentGenerationJob.objects.count(), 1)
        job = ContentGenerationJob.objects.first()
        self.assertEqual(job.model_key, "haiku")
        self.assertEqual(job.total_weeks, len(self.plan.plan_data))
        mock_delay.assert_called_once_with(job.pk)

    def test_cannot_generate_from_draft_plan(self):
        self._login("pub@example.com")
        self.plan.status = CurriculumPlan.Status.DRAFT
        self.plan.save(update_fields=["status"])
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/generate-content",
            {"model_key": "haiku"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_editor_cannot_trigger(self):
        self._login("ed@example.com")
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/generate-content",
            {"model_key": "haiku"},
        )
        self.assertIn(resp.status_code, [302, 403])


@override_settings(**_OVERRIDES)
class JobStatusViewTests(TestCase):
    def setUp(self):
        self.publisher = make_publisher(email="pub@example.com", password="testpass")
        self.editor = make_editor(email="ed@example.com", password="testpass")
        self.subject = make_subject(created_by=self.editor)
        self.textbook = make_textbook(
            central_subject=self.subject,
            uploaded_by=self.editor,
            num_chapters=5,
        )
        self.plan = make_curriculum_plan(
            textbook=self.textbook,
            generated_by=self.publisher,
            status=CurriculumPlan.Status.APPROVED,
        )
        self.job = make_content_generation_job(
            curriculum_plan=self.plan,
            triggered_by=self.publisher,
        )

    def _login(self, email):
        self.client.post("/login", {"email": email, "password": "testpass"})

    def test_status_page_renders(self):
        self._login("pub@example.com")
        resp = self.client.get(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/jobs/{self.job.pk}/"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "pending")

    def test_status_page_shows_completed_week(self):
        self._login("pub@example.com")
        self.job.week_results = [
            {"week": 1, "status": "done", "module_id": 1, "activity_id": 2},
            {"week": 2, "status": "pending"},
        ]
        self.job.completed_weeks = 1
        self.job.save(update_fields=["week_results", "completed_weeks"])
        resp = self.client.get(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/jobs/{self.job.pk}/"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "done")

    def test_status_badge_endpoint(self):
        self._login("pub@example.com")
        resp = self.client.get(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/jobs/{self.job.pk}/status"
        )
        self.assertEqual(resp.status_code, 200)
