"""[Classedge LMS] Gating tests for ide/views.py teacher-facing routes."""
from django.test import Client, TestCase
from django.urls import reverse

from ide.models import CodingExercise, CodeSubmission
from gradebookcomponent.tests.helpers import make_activity, make_subject
from roles.tests.helpers import make_it_admin, make_user_with_role


class IdeGatingTests(TestCase):

    def setUp(self):
        self.teacher = make_user_with_role("phase2_ide_teacher", "Teacher")
        self.student = make_user_with_role("phase2_ide_student", "Student")
        self.it_admin = make_it_admin(username="phase2_ide_itadmin")
        self.subject = make_subject(self.teacher, name="CS 101")
        self.activity = make_activity(self.subject, quiz_type_name="Coding")
        self.exercise = CodingExercise.objects.create(
            activity=self.activity,
            language="python",
            starter_code="",
            solution_code="",
            test_cases=[],
        )
        self.submission = CodeSubmission.objects.create(
            exercise=self.exercise,
            student=self.student,
            code="",
            language="python",
            status="completed",
            score=0.5,
        )
        self.client = Client()

    def _assert_gating(self, url, *, method="get", post_data=None):
        # Teacher with perm
        self.client.force_login(self.teacher)
        resp = getattr(self.client, method)(url, data=post_data or {})
        self.assertIn(resp.status_code, (200, 302, 400),
                      f"Teacher denied {url} (got {resp.status_code})")
        # Student without perm
        self.client.force_login(self.student)
        resp = getattr(self.client, method)(url, data=post_data or {})
        self.assertEqual(resp.status_code, 403,
                         f"Student not denied at {url}")
        # IT Admin (superuser bypass)
        self.client.force_login(self.it_admin)
        resp = getattr(self.client, method)(url, data=post_data or {})
        self.assertIn(resp.status_code, (200, 302, 400),
                      f"IT Admin denied {url} (got {resp.status_code})")

    def test_coding_overview(self):
        self._assert_gating(reverse("coding_overview"))

    def test_coding_exercise_results(self):
        self._assert_gating(
            reverse("coding_exercise_results", args=[self.exercise.id])
        )

    def test_coding_score_override(self):
        self._assert_gating(
            reverse("coding_score_override", args=[self.submission.id]),
            method="post",
            post_data={"new_score": "0.75", "override_note": "x"},
        )
