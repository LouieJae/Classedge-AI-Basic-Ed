"""Tests for activity.services.retake_resolver.select_canonical_details."""
import logging

from django.test import TestCase
from django.utils import timezone

from activity.models import (
    Activity,
    RetakeRecord,
    RetakeRecordDetail,
    StudentActivity,
)


class SelectCanonicalDetailsTest(TestCase):
    """Confirms which RetakeRecord's details are returned per retake_method.

    Fixtures: one StudentActivity with three RetakeRecords (scores 5, 8, 3),
    each owning two details. We assert that the helper returns the details
    belonging to the record selected by the activity's retake_method.
    """

    def setUp(self):
        self.activity = Activity.objects.create(
            activity_name="Quiz", retake_method="highest"
        )
        self.sa = StudentActivity.objects.create(activity=self.activity)

        # Three attempts, scores 5, 8, 3, in chronological order.
        # retake_time is auto_now_add so we create them in order.
        self.attempt_first = RetakeRecord.objects.create(
            student_activity=self.sa, activity=self.activity, score=5
        )
        self.detail_first_a = RetakeRecordDetail.objects.create(
            retake_record=self.attempt_first, student_answer="first-a"
        )
        self.detail_first_b = RetakeRecordDetail.objects.create(
            retake_record=self.attempt_first, student_answer="first-b"
        )

        self.attempt_highest = RetakeRecord.objects.create(
            student_activity=self.sa, activity=self.activity, score=8
        )
        self.detail_highest_a = RetakeRecordDetail.objects.create(
            retake_record=self.attempt_highest, student_answer="highest-a"
        )
        self.detail_highest_b = RetakeRecordDetail.objects.create(
            retake_record=self.attempt_highest, student_answer="highest-b"
        )

        self.attempt_latest = RetakeRecord.objects.create(
            student_activity=self.sa, activity=self.activity, score=3
        )
        self.detail_latest_a = RetakeRecordDetail.objects.create(
            retake_record=self.attempt_latest, student_answer="latest-a"
        )
        self.detail_latest_b = RetakeRecordDetail.objects.create(
            retake_record=self.attempt_latest, student_answer="latest-b"
        )

    def _import(self):
        from activity.services.retake_resolver import select_canonical_details
        return select_canonical_details

    def _ids(self, qs):
        return sorted(qs.values_list("pk", flat=True))

    def test_highest_returns_details_of_highest_scored_record(self):
        self.activity.retake_method = "highest"
        self.activity.save(update_fields=["retake_method"])
        select_canonical_details = self._import()
        self.assertEqual(
            self._ids(select_canonical_details(self.sa)),
            self._ids(self.attempt_highest.retake_record_details.all()),
        )

    def test_latest_returns_details_of_most_recent_record(self):
        self.activity.retake_method = "latest"
        self.activity.save(update_fields=["retake_method"])
        select_canonical_details = self._import()
        self.assertEqual(
            self._ids(select_canonical_details(self.sa)),
            self._ids(self.attempt_latest.retake_record_details.all()),
        )

    def test_first_returns_details_of_oldest_record(self):
        self.activity.retake_method = "first"
        self.activity.save(update_fields=["retake_method"])
        select_canonical_details = self._import()
        self.assertEqual(
            self._ids(select_canonical_details(self.sa)),
            self._ids(self.attempt_first.retake_record_details.all()),
        )

    def test_average_returns_details_of_latest_record_with_warning(self):
        self.activity.retake_method = "average"
        self.activity.save(update_fields=["retake_method"])
        select_canonical_details = self._import()
        with self.assertLogs(
            "activity.services.retake_resolver", level="WARNING"
        ) as caught:
            result = select_canonical_details(self.sa)
            self.assertEqual(
                self._ids(result),
                self._ids(self.attempt_latest.retake_record_details.all()),
            )
        self.assertTrue(
            any("average" in msg for msg in caught.output),
            f"Expected an 'average' warning; got {caught.output!r}",
        )

    def test_no_records_returns_empty_queryset(self):
        empty_activity = Activity.objects.create(
            activity_name="Empty", retake_method="latest"
        )
        empty_sa = StudentActivity.objects.create(activity=empty_activity)
        select_canonical_details = self._import()
        result = select_canonical_details(empty_sa)
        self.assertEqual(result.count(), 0)
        self.assertEqual(result.model, RetakeRecordDetail)
