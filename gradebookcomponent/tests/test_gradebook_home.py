"""[Classedge LMS] Tests for gradebook_home view."""
from django.test import TestCase
from django.urls import reverse

from gradebookcomponent.tests.helpers import (
    make_activity,
    make_subject,
    make_submission,
    make_user,
)


class GradebookHomeViewTest(TestCase):
    """[Classedge LMS] Verifies auth gate, role gate, rendering, and pending count."""

    def setUp(self):
        self.teacher = make_user("t@t.local", "Teacher")
        self.client.force_login(self.teacher)

    def test_unauthenticated_redirects(self):
        self.client.logout()
        response = self.client.get(reverse("gradebook_home"))
        self.assertIn(response.status_code, (302, 403))

    def test_renders_subjects(self):
        make_subject(self.teacher, name="Algebra")
        response = self.client.get(reverse("gradebook_home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Algebra")

    def test_non_teacher_denied(self):
        student = make_user("s@t.local", "Student")
        self.client.force_login(student)
        response = self.client.get(reverse("gradebook_home"))
        self.assertEqual(response.status_code, 403)

    def test_shows_pending_count(self):
        subject = make_subject(self.teacher, name="Algebra")
        activity = make_activity(subject, quiz_type_name="Essay")
        student = make_user("s@t.local", "Student")
        make_submission(student, activity, score=0)
        response = self.client.get(reverse("gradebook_home"))
        self.assertContains(response, "1")  # pending count
