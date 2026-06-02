import responses

from django.test import TestCase, override_settings

from central_content.models import SchoolSubjectBinding, PushJob
from central_content.tests.factories import (
    make_publisher, make_editor, make_reviewer, make_school,
    make_subject, make_binding,
)
from central_content.models import CentralSubject

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
class MatchingWorkspaceTests(TestCase):
    def setUp(self):
        self.pub = make_publisher(email="pub@example.com", password="pw")
        self.rev = make_reviewer(email="rev@example.com", password="pw")
        self.ed = make_editor(email="ed@example.com", password="pw")

    def _login(self, email):
        self.client.post("/login", {"email": email, "password": "pw"})

    def test_publisher_sees_workspace(self):
        self._login("pub@example.com")
        make_school(name="HCCCI")
        resp = self.client.get("/matching/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "HCCCI")

    def test_editor_forbidden(self):
        self._login("ed@example.com")
        resp = self.client.get("/matching/")
        self.assertEqual(resp.status_code, 403)

    @responses.activate
    def test_school_catalog_fetched(self):
        self._login("pub@example.com")
        school = make_school(name="HCCCI", base_url="https://school.example.com")
        responses.add(
            responses.GET,
            "https://school.example.com/api/central/subjects/",
            json=[{"id": 17, "subject_name": "Math 101", "subject_code": "MATH101"}],
            status=200,
        )
        resp = self.client.get(f"/matching/?school={school.pk}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Math 101")

    @responses.activate
    def test_school_catalog_error_shows_message(self):
        self._login("pub@example.com")
        school = make_school(base_url="https://school.example.com")
        responses.add(
            responses.GET,
            "https://school.example.com/api/central/subjects/",
            status=500,
        )
        resp = self.client.get(f"/matching/?school={school.pk}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Unable to fetch school subject list")

    def test_bindings_listed_for_school(self):
        self._login("pub@example.com")
        school = make_school(base_url="https://school.example.com")
        subject = make_subject(subject_name="Algebra 1", version=3, state=CentralSubject.State.APPROVED)
        make_binding(central_subject=subject, target_school=school, pushed_version=2)
        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, "https://school.example.com/api/central/subjects/", json=[], status=200)
            resp = self.client.get(f"/matching/?school={school.pk}")
        self.assertContains(resp, "Algebra 1")
        self.assertContains(resp, "Drift")


@override_settings(**_OVERRIDES)
class BindActionTests(TestCase):
    def setUp(self):
        self.pub = make_publisher(email="pub@example.com", password="pw")

    def _login(self, email):
        self.client.post("/login", {"email": email, "password": "pw"})

    def test_bind_creates_row(self):
        self._login("pub@example.com")
        school = make_school()
        subject = make_subject(state=CentralSubject.State.APPROVED)
        resp = self.client.post(
            "/matching/bind",
            {
                "school_id": school.pk,
                "central_subject_id": subject.pk,
                "school_subject_id": 17,
                "school_subject_name": "Math 101",
                "school_subject_code": "MATH101",
            },
            follow=True,
        )
        self.assertTrue(
            SchoolSubjectBinding.objects.filter(
                central_subject=subject, target_school=school
            ).exists()
        )


@override_settings(**_OVERRIDES)
class UnbindFlowTests(TestCase):
    def setUp(self):
        self.pub = make_publisher(email="pub@example.com", password="pw")

    def _login(self, email):
        self.client.post("/login", {"email": email, "password": "pw"})

    def test_unbind_confirm_page(self):
        self._login("pub@example.com")
        binding = make_binding()
        resp = self.client.get(f"/matching/unbind-confirm/{binding.pk}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, binding.central_subject.subject_name)

    @responses.activate
    def test_unbind_success_deletes_binding(self):
        self._login("pub@example.com")
        binding = make_binding()
        binding.target_school.base_url = "https://school.example.com"
        binding.target_school.save()
        responses.add(
            responses.DELETE,
            f"https://school.example.com/api/central/ingest/{binding.central_subject_id}/",
            status=204,
        )
        self.client.post(
            f"/matching/unbind/{binding.pk}",
            {"confirm_name": binding.central_subject.subject_name},
            follow=True,
        )
        self.assertFalse(SchoolSubjectBinding.objects.filter(pk=binding.pk).exists())
        self.assertTrue(PushJob.objects.filter(kind="delete", status="success").exists())

    def test_unbind_wrong_name_rejected(self):
        self._login("pub@example.com")
        binding = make_binding()
        resp = self.client.post(
            f"/matching/unbind/{binding.pk}",
            {"confirm_name": "WRONG"},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(SchoolSubjectBinding.objects.filter(pk=binding.pk).exists())


@override_settings(**_OVERRIDES)
class PushTriggerTests(TestCase):
    def setUp(self):
        self.pub = make_publisher(email="pub@example.com", password="pw")

    def _login(self, email):
        self.client.post("/login", {"email": email, "password": "pw"})

    @responses.activate
    def test_push_success(self):
        self._login("pub@example.com")
        binding = make_binding()
        binding.target_school.base_url = "https://school.example.com"
        binding.target_school.save()
        responses.add(
            responses.POST,
            "https://school.example.com/api/central/ingest/",
            json={"received_subject_id": 1, "central_version": 1, "received_at": "x"},
            status=200,
        )
        self.client.post(f"/matching/push/{binding.pk}", follow=True)
        binding.refresh_from_db()
        self.assertIsNotNone(binding.pushed_version)
        self.assertTrue(PushJob.objects.filter(kind="push", status="success").exists())
