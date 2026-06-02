import responses
from requests.exceptions import ConnectionError

from django.test import TestCase

from central_content.models import PushJob
from central_content.push import delete_subject_from_school
from central_content.tests.factories import make_binding, make_publisher


class DeleteFunctionTests(TestCase):
    def _setup_binding(self):
        binding = make_binding()
        binding.target_school.base_url = "https://school.example.com"
        binding.target_school.save()
        return binding

    @responses.activate
    def test_204_is_success(self):
        binding = self._setup_binding()
        url = f"https://school.example.com/api/central/ingest/{binding.central_subject_id}/"
        responses.add(responses.DELETE, url, status=204)
        job = delete_subject_from_school(binding, triggered_by=make_publisher())
        self.assertEqual(job.status, PushJob.Status.SUCCESS)
        self.assertEqual(job.kind, PushJob.Kind.DELETE)
        self.assertEqual(job.http_status, 204)

    @responses.activate
    def test_404_treated_as_success(self):
        binding = self._setup_binding()
        url = f"https://school.example.com/api/central/ingest/{binding.central_subject_id}/"
        responses.add(responses.DELETE, url, json={"error": "not_found"}, status=404)
        job = delete_subject_from_school(binding, triggered_by=make_publisher())
        self.assertEqual(job.status, PushJob.Status.SUCCESS)
        self.assertEqual(job.http_status, 404)

    @responses.activate
    def test_connection_error_is_failure(self):
        binding = self._setup_binding()
        url = f"https://school.example.com/api/central/ingest/{binding.central_subject_id}/"
        responses.add(responses.DELETE, url, body=ConnectionError("boom"))
        job = delete_subject_from_school(binding, triggered_by=make_publisher())
        self.assertEqual(job.status, PushJob.Status.FAILED)
        self.assertIsNone(job.http_status)
        self.assertIn("boom", job.error_message)

    @responses.activate
    def test_500_is_failure(self):
        binding = self._setup_binding()
        url = f"https://school.example.com/api/central/ingest/{binding.central_subject_id}/"
        responses.add(responses.DELETE, url, status=500)
        job = delete_subject_from_school(binding, triggered_by=make_publisher())
        self.assertEqual(job.status, PushJob.Status.FAILED)
        self.assertEqual(job.http_status, 500)
