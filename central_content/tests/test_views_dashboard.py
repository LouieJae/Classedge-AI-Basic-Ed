# central_content/tests/test_views_dashboard.py
from django.test import TestCase, override_settings

from central_content.models import CentralSubject
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
class DashboardTests(TestCase):
    def test_requires_login(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 302)

    def test_shows_counts(self):
        editor = make_editor(email="e@example.com", password="pw")
        make_subject(state=CentralSubject.State.DRAFT, created_by=editor)
        make_subject(state=CentralSubject.State.IN_REVIEW, created_by=editor)
        make_subject(state=CentralSubject.State.APPROVED, created_by=editor)
        self.client.post("/login", {"email": "e@example.com", "password": "pw"})
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Draft")
        self.assertContains(resp, "In Review")
        self.assertContains(resp, "Approved")
