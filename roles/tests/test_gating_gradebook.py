"""[Classedge LMS] Gating tests for gradebookcomponent/views/instructor_grading.py.

Each test asserts the perm-based contract (Teacher 200 / Student 403 /
IT Admin 200). Object-level authorization (authorize_subject_access) is
covered by the gradebookcomponent test suite, not here.
"""
from django.test import Client, TestCase
from django.urls import reverse

from gradebookcomponent.tests.helpers import (
    make_activity, make_subject, make_submission,
)
from roles.tests.helpers import make_it_admin, make_user_with_role


class GradebookGatingTests(TestCase):

    def setUp(self):
        self.teacher = make_user_with_role("phase2_teacher", "Teacher")
        self.student = make_user_with_role("phase2_student", "Student")
        self.it_admin = make_it_admin()
        self.subject = make_subject(self.teacher)
        # Views that call authorize_subject_access(user, subject) perform an
        # object-level check that rejects non-owners/non-collaborators. That
        # check is orthogonal to the perm-gating contract under test here.
        # Adding IT Admin as a collaborator lets the perm-gated request flow
        # through the inner object-level guard so these tests isolate the
        # decorator's behavior (which is what they are meant to verify).
        self.subject.collaborators.add(self.it_admin)
        self.activity = make_activity(self.subject)
        self.sa = make_submission(self.student, self.activity)
        self.client = Client()

    def _assert_gating(self, url, *, method="get", post_data=None):
        # Teacher with perm
        self.client.force_login(self.teacher)
        resp = getattr(self.client, method)(url, data=post_data or {})
        self.assertIn(
            resp.status_code, (200, 302, 400),
            f"Teacher denied {url} (got {resp.status_code})",
        )
        # Student without perm
        self.client.force_login(self.student)
        resp = getattr(self.client, method)(url, data=post_data or {})
        self.assertEqual(
            resp.status_code, 403,
            f"Student not denied at {url}",
        )
        # IT Admin (superuser bypass)
        self.client.force_login(self.it_admin)
        resp = getattr(self.client, method)(url, data=post_data or {})
        self.assertIn(
            resp.status_code, (200, 302, 400),
            f"IT Admin denied {url} (got {resp.status_code})",
        )

    def test_gradebook_home(self):
        self._assert_gating(reverse("gradebook_home"))

    def test_subject_gradebook(self):
        self._assert_gating(reverse("gradebook_subject", args=[self.subject.id]))

    def test_subject_gradebook_csv(self):
        self._assert_gating(reverse("gradebook_subject_csv", args=[self.subject.id]))

    def test_grading_queue(self):
        self._assert_gating(reverse("gradebook_queue"))

    def test_grade_submission(self):
        self._assert_gating(reverse("gradebook_grade", args=[self.sa.id]))

    def test_override_score(self):
        self._assert_gating(
            reverse("gradebook_override", args=[self.sa.id]),
            method="post",
            post_data={"reason": "test", "new_score": "5"},
        )
