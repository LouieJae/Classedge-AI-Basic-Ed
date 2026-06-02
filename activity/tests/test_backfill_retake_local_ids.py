from django.core.management import call_command
from django.test import TestCase

from accounts.models import CustomUser
from activity.models import Activity, RetakeRecord, StudentActivity


class BackfillRetakeLocalIdsTests(TestCase):
    """After Phase B, local_id is the PK and cannot be NULL/empty for any new
    row. The backfill command is retained as a defensive no-op for legacy data
    that may exist in long-lived dev/staging DBs predating the migration. These
    tests pin the no-op contract."""

    def setUp(self):
        self.student = CustomUser.objects.create(email="s@x.com")
        self.activity = Activity.objects.create(activity_name="A", max_score=10)
        self.sa = StudentActivity.objects.create(
            student=self.student, activity=self.activity
        )

    def test_check_mode_exits_zero_when_clean(self):
        try:
            call_command("backfill_retake_local_ids", "--check")
        except SystemExit as e:
            self.assertEqual(e.code, 0)

    def test_idempotent_second_run_no_change(self):
        rr = RetakeRecord.objects.create(
            student_activity=self.sa, student=self.student, activity=self.activity
        )
        call_command("backfill_retake_local_ids")
        rr.refresh_from_db()
        before = rr.local_id
        call_command("backfill_retake_local_ids")
        rr.refresh_from_db()
        self.assertEqual(rr.local_id, before)
