"""[Classedge LMS] Tests for grading_queue view."""
from django.test import TestCase
from django.urls import reverse

from gradebookcomponent.tests.helpers import (
    make_user, make_subject, make_activity, make_submission,
)


class GradingQueueTest(TestCase):
    """[Classedge LMS] Confirms queue view handles empty + populated state."""

    def setUp(self):
        self.teacher = make_user("t@t.local", "Teacher")
        self.client.force_login(self.teacher)

    def test_empty_queue(self):
        response = self.client.get(reverse("gradebook_queue"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No submissions awaiting your attention")

    def test_queue_lists_essay(self):
        subject = make_subject(self.teacher, name="Algebra")
        activity = make_activity(subject, quiz_type_name="Essay")
        student = make_user("s@t.local", "Student")
        make_submission(student, activity, score=0)
        response = self.client.get(reverse("gradebook_queue"))
        self.assertContains(response, "Essay activity")
        self.assertContains(response, "Algebra")
        self.assertContains(response, "Needs grading")
