from django.test import TestCase, Client
from ai_content.tests.test_models import _create_test_user
from gamification.models import BadgeDefinition, StudentBadge


class BadgeManagementTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = _create_test_user(username="bm_teach", role_name="teacher")
        self.student = _create_test_user(username="bm_stu", role_name="student")
        self.admin = _create_test_user(username="bm_admin", role_name="admin")

    def test_teacher_sees_badge_list(self):
        self.client.login(username="bm_teach", password="testpass")
        resp = self.client.get("/gamification/badges/manage/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("badges", resp.context)

    def test_admin_sees_badge_list(self):
        self.client.login(username="bm_admin", password="testpass")
        resp = self.client.get("/gamification/badges/manage/")
        self.assertEqual(resp.status_code, 200)

    def test_student_cannot_access_badge_management(self):
        self.client.login(username="bm_stu", password="testpass")
        resp = self.client.get("/gamification/badges/manage/")
        self.assertEqual(resp.status_code, 403)

    def test_toggle_badge_active(self):
        badge = BadgeDefinition.objects.create(
            code="toggle_test", name="Toggle", description="d",
            tier="bronze", icon="x", criteria_json={}, is_active=True,
        )
        self.client.login(username="bm_teach", password="testpass")
        resp = self.client.post(f"/gamification/badges/{badge.pk}/toggle/")
        self.assertEqual(resp.status_code, 302)
        badge.refresh_from_db()
        self.assertFalse(badge.is_active)

    def test_badge_edit_renders(self):
        badge = BadgeDefinition.objects.create(
            code="edit_test", name="Edit Me", description="d",
            tier="bronze", icon="x", criteria_json={"type": "xp_total", "threshold": 100},
        )
        self.client.login(username="bm_teach", password="testpass")
        resp = self.client.get(f"/gamification/badges/{badge.pk}/edit/")
        self.assertEqual(resp.status_code, 200)

    def test_badge_edit_saves(self):
        badge = BadgeDefinition.objects.create(
            code="edit_save", name="Old Name", description="old desc",
            tier="bronze", icon="x", criteria_json={},
        )
        self.client.login(username="bm_teach", password="testpass")
        resp = self.client.post(f"/gamification/badges/{badge.pk}/edit/", {
            "name": "New Name",
            "description": "new desc",
            "icon": "y",
            "tier": "silver",
        })
        self.assertEqual(resp.status_code, 302)
        badge.refresh_from_db()
        self.assertEqual(badge.name, "New Name")
        self.assertEqual(badge.tier, "silver")

    def test_manual_award_creates_student_badge(self):
        badge = BadgeDefinition.objects.create(
            code="manual_test", name="Manual", description="d",
            tier="platinum", icon="x", criteria_json={},
        )
        self.client.login(username="bm_teach", password="testpass")
        resp = self.client.post(f"/gamification/badges/{badge.pk}/award/", {
            "student": self.student.pk,
            "reason": "Great work!",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(StudentBadge.objects.filter(
            student=self.student, badge=badge, awarded_by=self.teacher,
        ).exists())

    def test_manual_award_prevents_duplicate(self):
        badge = BadgeDefinition.objects.create(
            code="dup_test", name="Dup", description="d",
            tier="platinum", icon="x", criteria_json={},
        )
        StudentBadge.objects.create(student=self.student, badge=badge)
        self.client.login(username="bm_teach", password="testpass")
        resp = self.client.post(f"/gamification/badges/{badge.pk}/award/", {
            "student": self.student.pk,
            "reason": "Again",
        })
        self.assertEqual(resp.status_code, 200)  # re-renders form with error
        self.assertEqual(StudentBadge.objects.filter(student=self.student, badge=badge).count(), 1)
