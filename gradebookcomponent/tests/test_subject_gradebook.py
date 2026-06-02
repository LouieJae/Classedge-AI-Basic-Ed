"""[Classedge LMS] Tests for subject_gradebook grid view."""
from django.test import TestCase
from django.urls import reverse

from gradebookcomponent.tests.helpers import (
    make_activity,
    make_subject,
    make_submission,
    make_user,
)


class SubjectGradebookTest(TestCase):
    """[Classedge LMS] Validates rendering and owner/other-teacher access."""

    def setUp(self):
        self.teacher = make_user("t@t.local", "Teacher")
        self.subject = make_subject(self.teacher, name="Algebra")
        self.client.force_login(self.teacher)

    def test_renders_grid(self):
        student = make_user("s@t.local", "Student")
        activity = make_activity(self.subject, quiz_type_name="Essay")
        make_submission(student, activity, score=8)
        response = self.client.get(
            reverse("gradebook_subject", args=[self.subject.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Algebra")
        self.assertContains(response, "Essay activity")
        self.assertContains(response, "8")

    def test_other_teacher_denied(self):
        other = make_user("o@t.local", "Teacher")
        self.client.force_login(other)
        response = self.client.get(
            reverse("gradebook_subject", args=[self.subject.id])
        )
        self.assertEqual(response.status_code, 403)
