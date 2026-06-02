from unittest.mock import patch

from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import CustomUser
from subject.models import Subject
from activity.models import (
    Activity,
    ActivityQuestion,
    QuizType,
    RetakeRecord,
    RetakeRecordDetail,
    StudentActivity,
    StudentQuestion,
)


class GradingViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = CustomUser.objects.create_user(
            username="teacher1", email="t@x.com", password="pw"
        )
        self.student = CustomUser.objects.create_user(
            username="student1", email="s@x.com", password="pw"
        )
        self.client.force_login(self.teacher)
        qt, _ = QuizType.objects.get_or_create(name="Essay")
        self.subject = Subject.objects.create(subject_name="S")
        self.act = Activity.objects.create(
            activity_name="A", max_score=10, max_retake=1, subject=self.subject,
        )
        self.q = ActivityQuestion.objects.create(
            activity=self.act, quiz_type=qt, score=10
        )
        self.sa = StudentActivity.objects.create(
            student=self.student, activity=self.act
        )
        self.rr = RetakeRecord.objects.create(
            student_activity=self.sa, student=self.student, retake_number=1
        )

    @patch("activity.views.grading_views.check_activity_access", return_value=(True, None))
    def test_grade_essays_lists_ungraded_details(self, _):
        graded = RetakeRecordDetail.objects.create(
            retake_record=self.rr, student=self.student,
            activity_question=self.q, student_answer="done", score=5,
        )
        ungraded = RetakeRecordDetail.objects.create(
            retake_record=self.rr, student=self.student,
            activity_question=self.q, student_answer="todo", score=0,
        )
        url = reverse("grade_essays", args=[str(self.act.pk)])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        details = list(resp.context["submission_details"])
        ids = {d.local_id for d in details}
        self.assertIn(ungraded.local_id, ids)
        self.assertNotIn(graded.local_id, ids)

    @patch("activity.views.grading_views.check_activity_access", return_value=(True, None))
    def test_grade_individual_essay_post_updates_score_and_total(self, _):
        detail = RetakeRecordDetail.objects.create(
            retake_record=self.rr, student=self.student,
            activity_question=self.q, student_answer="hi", score=0,
        )
        url = reverse("grade_individual_essay",
                      args=[str(self.act.pk), detail.local_id])
        resp = self.client.post(url, {"score": "7"})
        self.assertIn(resp.status_code, (200, 302))

        detail.refresh_from_db()
        self.assertEqual(detail.score, 7)

        self.rr.refresh_from_db()
        self.assertEqual(self.rr.score, 7)

        self.sa.refresh_from_db()
        self.assertGreater(self.sa.total_score, 0)

    @patch("activity.views.grading_views.check_activity_access", return_value=(True, None))
    def test_legacy_redirect_with_existing_sq_redirects_to_detail(self, _):
        sq = StudentQuestion.objects.create(
            student=self.student, activity_question=self.q,
            activity=self.act, score=0, student_answer="x",
        )
        detail = RetakeRecordDetail.objects.create(
            retake_record=self.rr, student=self.student,
            activity_question=self.q, student_answer="x", score=0,
        )
        url = reverse("grade_individual_essay_legacy",
                      args=[str(self.act.pk), sq.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        expected = reverse("grade_individual_essay",
                           args=[str(self.act.pk), detail.local_id])
        self.assertEqual(resp["Location"], expected)

    @patch("activity.views.grading_views.check_activity_access", return_value=(True, None))
    def test_legacy_redirect_with_missing_sq_redirects_to_listing(self, _):
        url = reverse("grade_individual_essay_legacy",
                      args=[str(self.act.pk), 999999])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        expected = reverse("grade_essays", args=[str(self.act.pk)])
        self.assertEqual(resp["Location"], expected)
