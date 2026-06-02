"""[Classedge LMS] Tests for grade_submission view."""
from django.test import TestCase
from django.urls import reverse

from activity.models.student_activity_model import StudentActivity
from gradebookcomponent.tests.helpers import (
    make_user, make_subject, make_activity, make_submission,
)


class GradeSubmissionTest(TestCase):
    """[Classedge LMS] Covers GET render, POST save, Save & Next, validation, auth."""

    def setUp(self):
        self.teacher = make_user("t@t.local", "Teacher")
        self.student = make_user("s@t.local", "Student")
        self.subject = make_subject(self.teacher)
        self.activity = make_activity(self.subject, quiz_type_name="Essay", max_score=10)
        self.sa = make_submission(self.student, self.activity, score=0, answer_text="My essay")
        self.client.force_login(self.teacher)

    def test_get_renders_form(self):
        response = self.client.get(reverse("gradebook_grade", args=[self.sa.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My essay")

    def test_post_saves_score_and_feedback(self):
        response = self.client.post(
            reverse("gradebook_grade", args=[self.sa.id]),
            {"score": "8.5", "feedback": "Solid argument."},
        )
        self.sa.refresh_from_db()
        self.assertEqual(self.sa.total_score, 8.5)
        self.assertEqual(self.sa.feedback, "Solid argument.")

    def test_post_redirects_to_next(self):
        student2 = make_user("s2@t.local", "Student")
        make_submission(student2, self.activity, score=0, answer_text="Another")
        response = self.client.post(
            reverse("gradebook_grade", args=[self.sa.id]),
            {"score": "8", "feedback": "", "save_and_next": "1"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/gradebook/grade/", response.url)

    def test_post_no_next_redirects_to_queue(self):
        response = self.client.post(
            reverse("gradebook_grade", args=[self.sa.id]),
            {"score": "8", "feedback": "", "save_and_next": "1"},
        )
        # Only one submission -> redirects to queue
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("gradebook_queue"), response.url)

    def test_score_above_max_rejected(self):
        response = self.client.post(
            reverse("gradebook_grade", args=[self.sa.id]),
            {"score": "100", "feedback": ""},
        )
        self.assertEqual(response.status_code, 400)
        self.sa.refresh_from_db()
        self.assertEqual(self.sa.total_score, 0)

    def test_other_teacher_denied(self):
        other = make_user("o@t.local", "Teacher")
        self.client.force_login(other)
        response = self.client.get(reverse("gradebook_grade", args=[self.sa.id]))
        self.assertEqual(response.status_code, 403)
