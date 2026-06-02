from django.test import TestCase, override_settings

from activity.models.activity_model import ActivityType
from central_content.models import CentralActivity
from central_content.tests.factories import (
    make_editor, make_reviewer, make_subject, make_activity,
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


@override_settings(**_OVERRIDES)
class ActivityViewTests(TestCase):
    def setUp(self):
        self.editor = make_editor(email="e@example.com", password="pw")
        self.reviewer = make_reviewer(email="r@example.com", password="pw")
        self.subject = make_subject(created_by=self.editor)
        self.atype, _ = ActivityType.objects.get_or_create(name="Quiz")
        self.client.post("/login", {"email": "e@example.com", "password": "pw"})

    def test_new_form_renders(self):
        resp = self.client.get(f"/subjects/{self.subject.id}/activities/new")
        self.assertEqual(resp.status_code, 200)

    def test_create_activity(self):
        resp = self.client.post(f"/subjects/{self.subject.id}/activities/new", {
            "activity_name": "Q1",
            "activity_type": self.atype.id,
            "activity_instruction": "",
            "max_score": "100",
            "time_duration": "0",
            "passing_score": "50",
            "passing_score_type": "percentage",
            "max_retake": "0",
            "retake_method": "highest",
            "is_graded": "on",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            CentralActivity.objects.filter(
                central_subject=self.subject, activity_name="Q1"
            ).exists()
        )

    def test_submit_and_approve_cycle(self):
        act = make_activity(central_subject=self.subject, created_by=self.editor)
        self.client.post(f"/subjects/{self.subject.id}/activities/{act.id}/submit")
        act.refresh_from_db()
        self.assertEqual(act.state, "in_review")

        self.client.post("/login", {"email": "r@example.com", "password": "pw"})
        self.client.post(f"/subjects/{self.subject.id}/activities/{act.id}/approve")
        act.refresh_from_db()
        self.assertEqual(act.state, "approved")

    def test_edit_blocked_when_not_draft(self):
        act = make_activity(central_subject=self.subject, created_by=self.editor,
                            state=CentralActivity.State.APPROVED)
        resp = self.client.get(
            f"/subjects/{self.subject.id}/activities/{act.id}/edit"
        )
        self.assertEqual(resp.status_code, 400)
