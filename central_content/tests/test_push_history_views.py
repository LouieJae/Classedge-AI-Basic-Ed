from django.test import TestCase, override_settings
from django.utils import timezone

from central_content.models import PushJob
from central_content.tests.factories import (
    make_publisher, make_reviewer, make_editor, make_binding,
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
class PushHistoryViewTests(TestCase):
    def setUp(self):
        binding = make_binding()
        self.binding = binding
        pub = make_publisher(email="trigger@example.com")
        PushJob.objects.create(
            central_subject=binding.central_subject,
            target_school=binding.target_school,
            kind="push", status="success", subject_version=1,
            http_status=200, finished_at=timezone.now(), triggered_by=pub,
        )
        PushJob.objects.create(
            central_subject=binding.central_subject,
            target_school=binding.target_school,
            kind="push", status="failed", subject_version=1,
            http_status=500, error_message="boom",
            finished_at=timezone.now(), triggered_by=pub,
        )
        self.pub = make_publisher(email="pub@example.com", password="pw")
        self.rev = make_reviewer(email="rev@example.com", password="pw")
        self.ed = make_editor(email="ed@example.com", password="pw")

    def _login(self, email):
        self.client.post("/login", {"email": email, "password": "pw"})

    def test_publisher_sees_all_rows(self):
        self._login("pub@example.com")
        resp = self.client.get("/push-history/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "boom")

    def test_reviewer_sees_all_rows(self):
        self._login("rev@example.com")
        resp = self.client.get("/push-history/")
        self.assertEqual(resp.status_code, 200)

    def test_editor_forbidden(self):
        self._login("ed@example.com")
        resp = self.client.get("/push-history/")
        self.assertEqual(resp.status_code, 403)

    def test_filter_by_status(self):
        self._login("pub@example.com")
        resp = self.client.get("/push-history/?status=failed")
        self.assertContains(resp, "boom")
