"""Tests for the 0008 backfill: StudentQuestion -> RetakeRecord/Detail."""
import importlib

from django.apps import apps as django_apps
from django.test import TestCase
from django.utils import timezone

from accounts.models import CustomUser

_backfill_module = importlib.import_module(
    "activity.migrations.0008_backfill_studentquestion_into_retake"
)


def _run_backfill():
    _backfill_module.forwards(django_apps, None)


class BackfillStudentQuestionTests(TestCase):
    def setUp(self):
        from activity.models import Activity, ActivityQuestion, StudentQuestion
        self.Activity = Activity
        self.ActivityQuestion = ActivityQuestion
        self.StudentQuestion = StudentQuestion

        self.student = CustomUser.objects.create(email="bf@x.com")
        self.activity = Activity.objects.create(
            activity_name="A", max_score=10, max_retake=1, retake_method="latest"
        )
        self.q1 = ActivityQuestion.objects.create(activity=self.activity, score=5)
        self.q2 = ActivityQuestion.objects.create(activity=self.activity, score=5)

    def test_groups_sq_into_one_retakerecord_with_two_details(self):
        from activity.models import RetakeRecord, RetakeRecordDetail
        now = timezone.now()
        self.StudentQuestion.objects.create(
            student=self.student, activity=self.activity,
            activity_question=self.q1, student_answer="a1", score=5,
            submission_time=now,
        )
        self.StudentQuestion.objects.create(
            student=self.student, activity=self.activity,
            activity_question=self.q2, student_answer="a2", score=3,
            submission_time=now,
        )

        _run_backfill()

        self.assertEqual(RetakeRecord.objects.count(), 1)
        rr = RetakeRecord.objects.first()
        self.assertEqual(rr.retake_number, 1)
        self.assertEqual(rr.status, "submitted")
        self.assertEqual(RetakeRecordDetail.objects.filter(retake_record=rr).count(), 2)
        self.assertEqual(rr.score, 8)

    def test_recomputes_student_activity_total(self):
        from activity.models import StudentActivity
        self.StudentQuestion.objects.create(
            student=self.student, activity=self.activity,
            activity_question=self.q1, score=4, submission_time=timezone.now(),
        )
        _run_backfill()
        sa = StudentActivity.objects.get(student=self.student, activity=self.activity)
        self.assertEqual(sa.total_score, 4)

    def test_idempotent_second_run_no_duplicate_records(self):
        from activity.models import RetakeRecord, RetakeRecordDetail
        self.StudentQuestion.objects.create(
            student=self.student, activity=self.activity,
            activity_question=self.q1, score=5, submission_time=timezone.now(),
        )
        _run_backfill()
        _run_backfill()
        self.assertEqual(RetakeRecord.objects.count(), 1)
        self.assertEqual(RetakeRecordDetail.objects.count(), 1)

    def test_reuses_existing_mobile_retakerecord(self):
        from datetime import timedelta
        from activity.models import (
            RetakeRecord, RetakeRecordDetail, StudentActivity,
        )
        sa = StudentActivity.objects.create(
            student=self.student, activity=self.activity
        )
        existing_rr = RetakeRecord.objects.create(
            student_activity=sa, student=self.student, activity=self.activity,
            retake_number=1, status="submitted",
        )
        old = timezone.now() - timedelta(days=1)
        new = timezone.now()
        RetakeRecordDetail.objects.create(
            retake_record=existing_rr, student=self.student,
            activity_question=self.q1, student_answer="mobile-old", score=2,
            submission_time=old,
        )
        self.StudentQuestion.objects.create(
            student=self.student, activity=self.activity,
            activity_question=self.q1, student_answer="web-new", score=5,
            submission_time=new,
        )

        _run_backfill()

        self.assertEqual(RetakeRecord.objects.count(), 1)
        d = RetakeRecordDetail.objects.get(
            retake_record=existing_rr, activity_question=self.q1
        )
        self.assertEqual(d.student_answer, "web-new")
        self.assertEqual(d.score, 5)

    def test_skips_sq_with_null_activity_question(self):
        from activity.models import RetakeRecord, RetakeRecordDetail
        self.StudentQuestion.objects.create(
            student=self.student, activity=self.activity,
            activity_question=None, score=10, is_participation=True,
            submission_time=timezone.now(),
        )
        _run_backfill()
        self.assertEqual(RetakeRecord.objects.count(), 0)
        self.assertEqual(RetakeRecordDetail.objects.count(), 0)
