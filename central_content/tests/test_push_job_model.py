from django.test import TestCase
from django.utils import timezone

from central_content.models import PushJob
from central_content.tests.factories import make_subject, make_publisher, make_school


class PushJobModelTests(TestCase):
    def test_create_success_push_job(self):
        subject = make_subject(version=2)
        school = make_school()
        publisher = make_publisher()
        job = PushJob.objects.create(
            central_subject=subject,
            target_school=school,
            kind=PushJob.Kind.PUSH,
            status=PushJob.Status.SUCCESS,
            subject_version=2,
            http_status=200,
            response_body='{"received_subject_id": 1}',
            finished_at=timezone.now(),
            triggered_by=publisher,
        )
        self.assertEqual(job.kind, "push")
        self.assertEqual(job.status, "success")

    def test_create_failed_push_job(self):
        job = PushJob.objects.create(
            central_subject=make_subject(version=1),
            target_school=make_school(),
            kind=PushJob.Kind.PUSH,
            status=PushJob.Status.FAILED,
            subject_version=1,
            http_status=500,
            error_message="internal server error",
            finished_at=timezone.now(),
            triggered_by=make_publisher(),
        )
        self.assertEqual(job.status, "failed")
        self.assertEqual(job.http_status, 500)

    def test_create_delete_job(self):
        job = PushJob.objects.create(
            central_subject=make_subject(),
            target_school=make_school(),
            kind=PushJob.Kind.DELETE,
            status=PushJob.Status.SUCCESS,
            subject_version=1,
            http_status=204,
            finished_at=timezone.now(),
            triggered_by=make_publisher(),
        )
        self.assertEqual(job.kind, "delete")
