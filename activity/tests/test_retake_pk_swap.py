from django.db import models as dj_models
from django.test import TestCase

from accounts.models import CustomUser
from activity.models import (
    Activity,
    ActivityQuestion,
    RetakeRecord,
    RetakeRecordDetail,
    StudentActivity,
)


class RetakePKSwapTests(TestCase):
    def test_pk_is_local_id_charfield(self):
        for M in (RetakeRecord, RetakeRecordDetail):
            self.assertEqual(M._meta.pk.name, "local_id")
            self.assertIsInstance(M._meta.pk, dj_models.CharField)
            self.assertEqual(M._meta.pk.max_length, 36)

    def test_client_minted_cuid_is_accepted_as_pk(self):
        s = CustomUser.objects.create(email="t@x.com")
        a = Activity.objects.create(activity_name="A", max_score=10)
        sa = StudentActivity.objects.create(student=s, activity=a)
        rr = RetakeRecord.objects.create(
            local_id="client_minted_cuid_001",
            student_activity=sa,
            student=s,
            activity=a,
        )
        self.assertEqual(
            RetakeRecord.objects.get(pk="client_minted_cuid_001").pk, rr.pk
        )

    def test_fk_integrity_string_keys(self):
        s = CustomUser.objects.create(email="u@x.com")
        a = Activity.objects.create(activity_name="A", max_score=10)
        sa = StudentActivity.objects.create(student=s, activity=a)
        q = ActivityQuestion.objects.create(activity=a)
        rr = RetakeRecord.objects.create(student_activity=sa, student=s, activity=a)
        d = RetakeRecordDetail.objects.create(
            retake_record=rr, student=s, activity_question=q
        )
        self.assertIsInstance(d.retake_record_id, str)
        self.assertEqual(d.retake_record_id, rr.local_id)
