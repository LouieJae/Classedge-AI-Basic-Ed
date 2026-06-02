import json
from unittest.mock import patch, MagicMock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from central_content.models import (
    CurriculumPlan, ParsedTextbook, ParsedChapter,
)
from central_content.tests.factories import (
    make_editor, make_publisher, make_reviewer, make_subject,
    make_school, make_binding, make_textbook, make_curriculum_plan,
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
        "sonnet": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-6",
            "api_key_env": "ANTHROPIC_API_KEY",
        },
    },
    CURRICULUM_PLANNER_DEFAULT_MODEL="haiku",
)


@override_settings(**_OVERRIDES)
class PlanGenerateViewTests(TestCase):
    def setUp(self):
        self.publisher = make_publisher(email="pub@example.com", password="testpass")
        self.editor = make_editor(email="ed@example.com", password="testpass")
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

    def _login(self, email):
        self.client.post("/login", {"email": email, "password": "testpass"})

    def test_generate_page_renders(self):
        self._login("pub@example.com")
        resp = self.client.get(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/generate"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "haiku")
        self.assertContains(resp, "sonnet")

    @patch("central_content.views.plans.generate_curriculum_plan.delay")
    def test_post_triggers_task_and_redirects(self, mock_delay):
        mock_delay.return_value = MagicMock(id="task-123")
        self._login("pub@example.com")
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/generate",
            {"binding_id": self.binding.pk, "model_key": "haiku"},
        )
        self.assertEqual(resp.status_code, 302)
        mock_delay.assert_called_once_with(
            self.textbook.pk, self.binding.pk, "haiku", self.publisher.pk,
        )

    def test_editor_cannot_access_generate(self):
        self._login("ed@example.com")
        resp = self.client.get(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/generate"
        )
        self.assertIn(resp.status_code, [302, 403])


@override_settings(**_OVERRIDES)
class PlanDetailViewTests(TestCase):
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
        )

    def _login(self, email):
        self.client.post("/login", {"email": email, "password": "testpass"})

    def test_detail_renders(self):
        self._login("pub@example.com")
        resp = self.client.get(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Week 1")
        self.assertContains(resp, "Week 2")


@override_settings(**_OVERRIDES)
class PlanEditViewTests(TestCase):
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
        )

    def _login(self, email):
        self.client.post("/login", {"email": email, "password": "testpass"})

    def test_save_valid_edit(self):
        self._login("pub@example.com")
        new_plan_data = [
            {"week": 1, "chapters": [1], "title": "Intro", "description": "Start"},
            {"week": 2, "chapters": [2, 3], "title": "Core", "description": "Middle"},
            {"week": 3, "chapters": [4, 5], "title": "End", "description": "Finish"},
        ]
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/edit",
            {"plan_data": json.dumps(new_plan_data)},
        )
        self.assertEqual(resp.status_code, 302)
        self.plan.refresh_from_db()
        self.assertEqual(len(self.plan.plan_data), 3)

    def test_save_invalid_edit_returns_error(self):
        self._login("pub@example.com")
        bad_plan_data = [
            {"week": 1, "chapters": [1, 2], "title": "A", "description": ""},
        ]
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/edit",
            {"plan_data": json.dumps(bad_plan_data)},
        )
        self.assertEqual(resp.status_code, 400)

    def test_cannot_edit_approved_plan(self):
        self._login("pub@example.com")
        self.plan.status = CurriculumPlan.Status.APPROVED
        self.plan.save(update_fields=["status"])
        new_plan_data = [
            {"week": 1, "chapters": [1, 2, 3], "title": "A", "description": ""},
            {"week": 2, "chapters": [4, 5], "title": "B", "description": ""},
        ]
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/edit",
            {"plan_data": json.dumps(new_plan_data)},
        )
        self.assertEqual(resp.status_code, 400)


@override_settings(**_OVERRIDES)
class PlanApproveRejectViewTests(TestCase):
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
        )

    def _login(self, email):
        self.client.post("/login", {"email": email, "password": "testpass"})

    def test_approve_plan(self):
        self._login("pub@example.com")
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/approve"
        )
        self.assertEqual(resp.status_code, 302)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.status, CurriculumPlan.Status.APPROVED)

    def test_reject_plan(self):
        self._login("pub@example.com")
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/reject"
        )
        self.assertEqual(resp.status_code, 302)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.status, CurriculumPlan.Status.REJECTED)

    def test_cannot_approve_already_approved(self):
        self._login("pub@example.com")
        self.plan.status = CurriculumPlan.Status.APPROVED
        self.plan.save(update_fields=["status"])
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/approve"
        )
        self.assertEqual(resp.status_code, 400)

    def test_editor_cannot_approve(self):
        self._login("ed@example.com")
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/approve"
        )
        self.assertIn(resp.status_code, [302, 403])


@override_settings(**_OVERRIDES)
class BulkRunViewTests(TestCase):
    def setUp(self):
        self.publisher = make_publisher(email="pub@example.com", password="testpass")
        self.editor = make_editor(email="ed@example.com", password="testpass")
        self.subject = make_subject(created_by=self.editor)
        self.school = make_school(created_by=self.publisher)
        self.binding = make_binding(
            central_subject=self.subject,
            target_school=self.school,
            school_subject_id=42,
            bound_by=self.publisher,
        )

    def _login(self, email):
        self.client.post("/login", {"email": email, "password": "testpass"})

    @patch("central_content.views.plans.bulk_generate_plans.delay")
    def test_bulk_run_triggers_task(self, mock_delay):
        self._login("pub@example.com")
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/plans/bulk-generate",
            {"binding_id": self.binding.pk, "model_key": "haiku"},
        )
        self.assertEqual(resp.status_code, 302)
        mock_delay.assert_called_once_with(
            self.subject.pk, self.binding.pk, "haiku", self.publisher.pk,
        )
