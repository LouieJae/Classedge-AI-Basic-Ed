"""[Classedge LMS] Tests for override_score view and audit log."""
from django.test import TestCase
from django.urls import reverse

from activity.models.score_log_models import ScoreChangeLog
from activity.models.student_activity_model import StudentActivity
from gradebookcomponent.tests.helpers import (
    make_user, make_subject, make_activity, make_submission,
)


class OverrideScoreTest(TestCase):
    """[Classedge LMS] Confirms override math, required reason, range check, and auth."""

    def setUp(self):
        self.teacher = make_user("t@t.local", "Teacher")
        self.student = make_user("s@t.local", "Student")
        subject = make_subject(self.teacher)
        activity = make_activity(subject, quiz_type_name="Multiple Choice", max_score=10)
        self.sa = make_submission(self.student, activity, score=5)
        self.sa.is_editable = True
        self.sa.save()
        self.client.force_login(self.teacher)

    def test_override_with_reason_writes_log(self):
        response = self.client.post(
            reverse("gradebook_override", args=[self.sa.id]),
            {"new_score": "8", "reason": "Accepted alternate answer in Q2."},
        )
        # Form POST (no HX-Request header) redirects back to the subject gradebook.
        self.assertEqual(response.status_code, 302)
        self.sa.refresh_from_db()
        self.assertEqual(self.sa.total_score, 8.0)
        log = ScoreChangeLog.objects.get(student_activity=self.sa)
        self.assertEqual(log.new_score, 8.0)
        self.assertEqual(log.previous_score, 5.0)
        self.assertEqual(log.reason, "Accepted alternate answer in Q2.")
        self.assertEqual(log.changed_by, self.teacher)

    def test_override_htmx_returns_fragment(self):
        response = self.client.post(
            reverse("gradebook_override", args=[self.sa.id]),
            {"new_score": "8", "reason": "HTMX path."},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"graded", response.content)

    def test_override_without_reason_rejected(self):
        response = self.client.post(
            reverse("gradebook_override", args=[self.sa.id]),
            {"new_score": "8", "reason": ""},
        )
        self.assertEqual(response.status_code, 400)
        self.sa.refresh_from_db()
        self.assertEqual(self.sa.total_score, 5.0)
        self.assertFalse(ScoreChangeLog.objects.filter(student_activity=self.sa).exists())

    def test_override_score_out_of_range_rejected(self):
        response = self.client.post(
            reverse("gradebook_override", args=[self.sa.id]),
            {"new_score": "99", "reason": "anything"},
        )
        self.assertEqual(response.status_code, 400)

    def test_override_creates_one_log_per_change(self):
        self.client.post(
            reverse("gradebook_override", args=[self.sa.id]),
            {"new_score": "7", "reason": "first"},
        )
        self.client.post(
            reverse("gradebook_override", args=[self.sa.id]),
            {"new_score": "9", "reason": "second"},
        )
        self.assertEqual(ScoreChangeLog.objects.filter(student_activity=self.sa).count(), 2)

    def test_other_teacher_denied(self):
        other = make_user("o@t.local", "Teacher")
        self.client.force_login(other)
        response = self.client.post(
            reverse("gradebook_override", args=[self.sa.id]),
            {"new_score": "8", "reason": "x"},
        )
        self.assertEqual(response.status_code, 403)
