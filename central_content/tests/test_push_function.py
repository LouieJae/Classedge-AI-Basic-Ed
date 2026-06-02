import responses
from requests.exceptions import ConnectionError

from django.test import TestCase

from central_content.models import PushJob
from central_content.push import push_subject_to_school
from central_content.tests.factories import (
    make_binding, make_subject, make_publisher, make_school, make_module,
)


class PushFunctionTests(TestCase):
    def _setup_binding(self, version=1):
        subject = make_subject(version=version)
        school = make_school(base_url="https://school.example.com")
        return make_binding(central_subject=subject, target_school=school)

    @responses.activate
    def test_happy_path_updates_binding_and_creates_success_job(self):
        binding = self._setup_binding(version=3)
        publisher = make_publisher()
        responses.add(
            responses.POST,
            "https://school.example.com/api/central/ingest/",
            json={"received_subject_id": 99, "central_version": 3, "received_at": "x"},
            status=200,
        )
        job = push_subject_to_school(binding, triggered_by=publisher)
        self.assertEqual(job.status, PushJob.Status.SUCCESS)
        self.assertEqual(job.kind, PushJob.Kind.PUSH)
        self.assertEqual(job.http_status, 200)
        binding.refresh_from_db()
        self.assertEqual(binding.pushed_version, 3)
        self.assertIsNotNone(binding.last_pushed_at)

    @responses.activate
    def test_401_from_school_creates_failed_job(self):
        binding = self._setup_binding()
        responses.add(
            responses.POST,
            "https://school.example.com/api/central/ingest/",
            json={"error": "unauthorized"},
            status=401,
        )
        job = push_subject_to_school(binding, triggered_by=make_publisher())
        self.assertEqual(job.status, PushJob.Status.FAILED)
        self.assertEqual(job.http_status, 401)
        binding.refresh_from_db()
        self.assertIsNone(binding.pushed_version)

    @responses.activate
    def test_422_unresolved_sdg_creates_failed_job(self):
        binding = self._setup_binding()
        responses.add(
            responses.POST,
            "https://school.example.com/api/central/ingest/",
            json={"error": "unresolved_sdgs", "names": ["X"]},
            status=422,
        )
        job = push_subject_to_school(binding, triggered_by=make_publisher())
        self.assertEqual(job.status, PushJob.Status.FAILED)
        self.assertEqual(job.http_status, 422)
        self.assertIn("unresolved_sdgs", job.response_body)

    @responses.activate
    def test_5xx_creates_failed_job(self):
        binding = self._setup_binding()
        responses.add(
            responses.POST,
            "https://school.example.com/api/central/ingest/",
            body="boom", status=500,
        )
        job = push_subject_to_school(binding, triggered_by=make_publisher())
        self.assertEqual(job.status, PushJob.Status.FAILED)
        self.assertEqual(job.http_status, 500)

    @responses.activate
    def test_connection_error_creates_failed_job_no_http_status(self):
        binding = self._setup_binding()
        responses.add(
            responses.POST,
            "https://school.example.com/api/central/ingest/",
            body=ConnectionError("boom"),
        )
        job = push_subject_to_school(binding, triggered_by=make_publisher())
        self.assertEqual(job.status, PushJob.Status.FAILED)
        self.assertIsNone(job.http_status)
        self.assertIn("boom", job.error_message)
