"""[Classedge LMS] Gating tests for gamification/subject_analytics.py."""
from django.test import Client, TestCase
from django.urls import reverse

from gradebookcomponent.tests.helpers import make_subject
from roles.tests.helpers import make_it_admin, make_user_with_role


class SubjectAnalyticsGatingTests(TestCase):

    def setUp(self):
        self.teacher = make_user_with_role("phase2_sa_teacher", "Teacher")
        self.student = make_user_with_role("phase2_sa_student", "Student")
        self.it_admin = make_it_admin(username="phase2_sa_itadmin")
        self.subject = make_subject(self.teacher, name="Phys 101")
        # Perm-gating happens at the decorator; inner object-level check
        # (_authorize_subject) also requires subject membership. Add both
        # teacher (already assigned) and IT Admin as collaborators so the
        # perm gate is what's actually under test here.
        self.subject.collaborators.add(self.it_admin)
        self.client = Client()

    def _assert_gating(self, url):
        self.client.force_login(self.teacher)
        self.assertIn(self.client.get(url).status_code, (200, 302, 400))
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.it_admin)
        self.assertIn(self.client.get(url).status_code, (200, 302, 400))

    def test_subject_panel_view(self):
        self._assert_gating(
            reverse("subject_analytics_panel", args=[self.subject.id])
        )

    def test_student_detail_view(self):
        self._assert_gating(
            reverse("subject_student_detail", args=[self.subject.id, self.student.id])
        )
