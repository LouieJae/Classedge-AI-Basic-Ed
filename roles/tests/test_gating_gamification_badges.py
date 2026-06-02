"""[Classedge LMS] Gating tests for gamification/views.py badge management."""
from django.test import Client, TestCase
from django.urls import reverse

from gamification.models import BadgeDefinition
from roles.tests.helpers import make_it_admin, make_user_with_role


class GamificationBadgeGatingTests(TestCase):

    def setUp(self):
        self.teacher = make_user_with_role("phase2_g_teacher", "Teacher")
        self.student = make_user_with_role("phase2_g_student", "Student")
        self.it_admin = make_it_admin(username="phase2_g_itadmin")
        self.badge = BadgeDefinition.objects.create(
            code="phase2_test_badge",
            name="Test Badge",
            description="x",
            icon="",
            tier="bronze",
            criteria_json={"type": "general"},
            is_active=True,
        )
        self.client = Client()

    def _assert_gating(self, url, *, method="get", post_data=None):
        self.client.force_login(self.teacher)
        resp = getattr(self.client, method)(url, data=post_data or {})
        self.assertIn(resp.status_code, (200, 302, 400),
                      f"Teacher denied {url} (got {resp.status_code})")
        self.client.force_login(self.student)
        resp = getattr(self.client, method)(url, data=post_data or {})
        self.assertEqual(resp.status_code, 403,
                         f"Student not denied at {url}")
        self.client.force_login(self.it_admin)
        resp = getattr(self.client, method)(url, data=post_data or {})
        self.assertIn(resp.status_code, (200, 302, 400),
                      f"IT Admin denied {url} (got {resp.status_code})")

    def test_badge_list(self):
        self._assert_gating(reverse("badge_management"))

    def test_badge_toggle_active(self):
        self._assert_gating(
            reverse("badge_toggle_active", args=[self.badge.id]),
            method="post",
        )

    def test_badge_edit(self):
        self._assert_gating(reverse("badge_edit", args=[self.badge.id]))

    def test_badge_manual_award(self):
        self._assert_gating(
            reverse("badge_manual_award", args=[self.badge.id])
        )
