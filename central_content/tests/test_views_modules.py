# central_content/tests/test_views_modules.py
from django.test import TestCase, override_settings

from central_content.models import CentralModule, CentralSubject
from central_content.tests.factories import (
    make_editor, make_reviewer,
    make_subject, make_module,
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
class ModuleViewTests(TestCase):
    def setUp(self):
        self.editor = make_editor(email="e@example.com", password="pw")
        self.reviewer = make_reviewer(email="r@example.com", password="pw")
        self.subject = make_subject(created_by=self.editor)
        self.client.post("/login", {"email": "e@example.com", "password": "pw"})

    def test_new_form(self):
        resp = self.client.get(f"/subjects/{self.subject.id}/modules/new")
        self.assertEqual(resp.status_code, 200)

    def test_create_module(self):
        resp = self.client.post(f"/subjects/{self.subject.id}/modules/new", {
            "file_name": "L1",
            "description": "d",
            "url": "",
            "iframe_code": "",
            "order": "0",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            CentralModule.objects.filter(central_subject=self.subject,
                                         file_name="L1").exists()
        )

    def test_edit_blocked_when_not_draft(self):
        m = make_module(central_subject=self.subject, created_by=self.editor,
                        state=CentralModule.State.APPROVED)
        resp = self.client.get(f"/subjects/{self.subject.id}/modules/{m.id}/edit")
        self.assertEqual(resp.status_code, 400)

    def test_submit_transition(self):
        m = make_module(central_subject=self.subject, created_by=self.editor)
        resp = self.client.post(f"/subjects/{self.subject.id}/modules/{m.id}/submit")
        self.assertEqual(resp.status_code, 302)
        m.refresh_from_db()
        self.assertEqual(m.state, "in_review")

    def test_approve_by_editor_forbidden(self):
        m = make_module(central_subject=self.subject, created_by=self.editor,
                        state=CentralModule.State.IN_REVIEW)
        resp = self.client.post(f"/subjects/{self.subject.id}/modules/{m.id}/approve")
        self.assertEqual(resp.status_code, 403)

    def test_approve_by_reviewer(self):
        self.client.post("/login", {"email": "r@example.com", "password": "pw"})
        m = make_module(central_subject=self.subject, created_by=self.editor,
                        state=CentralModule.State.IN_REVIEW)
        resp = self.client.post(f"/subjects/{self.subject.id}/modules/{m.id}/approve")
        self.assertEqual(resp.status_code, 302)
        m.refresh_from_db()
        self.assertEqual(m.state, "approved")
