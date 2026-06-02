from unittest.mock import patch

from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import CustomUser
from activity.models import (
    Activity,
    ActivityQuestion,
    QuizType,
    RetakeRecord,
    RetakeRecordDetail,
    StudentActivity,
    StudentQuestion,
)


class WebSubmitWritesRetakeOnlyTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            username="student1", email="s@x.com", password="pw"
        )
        self.client.force_login(self.user)
        qt, _ = QuizType.objects.get_or_create(name="Essay")
        self.act = Activity.objects.create(
            activity_name="A", max_score=10, max_retake=1
        )
        self.q = ActivityQuestion.objects.create(
            activity=self.act, quiz_type=qt, score=10
        )

    @patch("activity.views.answer_views.check_activity_access", return_value=(True, None))
    def test_submit_creates_retakerecord_and_detail_no_studentquestion(self, _):
        StudentActivity.objects.create(student=self.user, activity=self.act)
        url = reverse("submit_answers", args=[str(self.act.pk)])
        resp = self.client.post(url, {f"question_{self.q.pk}": "essay text"})
        self.assertIn(resp.status_code, (200, 302))

        sa = StudentActivity.objects.get(student=self.user, activity=self.act)
        rr = RetakeRecord.objects.filter(student_activity=sa).first()
        self.assertIsNotNone(rr, "submit must create a RetakeRecord")
        d = RetakeRecordDetail.objects.filter(
            retake_record=rr, activity_question=self.q
        ).first()
        self.assertIsNotNone(d, "submit must create a RetakeRecordDetail")
        self.assertEqual(d.student_answer, "essay text")
        self.assertFalse(
            StudentQuestion.objects.filter(
                student=self.user, activity_question=self.q
            ).exists(),
            "submit must not write a StudentQuestion row",
        )
