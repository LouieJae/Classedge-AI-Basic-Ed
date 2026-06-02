# central_content/tests/test_audit_log.py
from django.test import TestCase, override_settings

from central_content.models import AuditLogEntry
from central_content.state_machine import submit_for_review
from central_content.tests.factories import make_editor, make_subject

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
class SubjectHistoryViewTests(TestCase):
    def test_history_lists_entries(self):
        editor = make_editor(email="e@example.com", password="pw")
        subj = make_subject(created_by=editor)
        submit_for_review(subj, actor=editor)
        self.client.post("/login", {"email": "e@example.com", "password": "pw"})
        resp = self.client.get(f"/subjects/{subj.id}/history")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "draft")
        self.assertContains(resp, "in_review")

    def test_audit_entries_written_on_each_transition(self):
        editor = make_editor()
        subj = make_subject(created_by=editor)
        submit_for_review(subj, actor=editor)
        self.assertEqual(AuditLogEntry.objects.count(), 1)
