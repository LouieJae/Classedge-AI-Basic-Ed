"""[Classedge LMS] Gating test for gamification/teacher_views.py:send_recognition."""
import json

from django.test import Client, TestCase
from django.urls import reverse

from roles.tests.helpers import make_it_admin, make_user_with_role


class SendRecognitionGatingTests(TestCase):

    def setUp(self):
        self.teacher = make_user_with_role("phase2_tv_teacher", "Teacher")
        self.student = make_user_with_role("phase2_tv_student", "Student")
        self.it_admin = make_it_admin(username="phase2_tv_itadmin")
        self.target = make_user_with_role("phase2_tv_target", "Student")
        self.client = Client()
        self.url = reverse("send_recognition")
        self.payload = json.dumps({
            "student_id": self.target.id,
            "message": "Great job!",
            "xp_amount": 10,
        })

    def _post_as(self, user):
        self.client.force_login(user)
        return self.client.post(
            self.url, data=self.payload, content_type="application/json",
        )

    def test_teacher_passes(self):
        resp = self._post_as(self.teacher)
        self.assertNotEqual(resp.status_code, 403)

    def test_student_denied(self):
        resp = self._post_as(self.student)
        self.assertEqual(resp.status_code, 403)

    def test_it_admin_passes(self):
        resp = self._post_as(self.it_admin)
        self.assertNotEqual(resp.status_code, 403)
