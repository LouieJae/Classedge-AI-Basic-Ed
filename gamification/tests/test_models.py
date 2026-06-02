from django.db import IntegrityError
from django.test import TestCase

from ai_content.tests.test_models import _create_test_user
from gamification.models import (
    BadgeDefinition,
    StudentBadge,
    StudentGamification,
    XPTransaction,
)


class StudentGamificationTests(TestCase):
    def test_create_defaults(self):
        user = _create_test_user("gam_user1", "student")
        sg = StudentGamification.objects.create(student=user)
        self.assertEqual(sg.total_xp, 0)
        self.assertEqual(sg.current_level, 1)
        self.assertEqual(sg.login_streak, 0)
        self.assertEqual(sg.streak_freezes_available, 1)

    def test_one_to_one_enforced(self):
        user = _create_test_user("gam_user2", "student")
        StudentGamification.objects.create(student=user)
        with self.assertRaises(IntegrityError):
            StudentGamification.objects.create(student=user)


class XPTransactionTests(TestCase):
    def test_create_transaction(self):
        user = _create_test_user("gam_user3", "student")
        tx = XPTransaction.objects.create(
            student=user,
            amount=50,
            reason="submission",
            source_type="assignment",
            source_id=1,
        )
        self.assertEqual(tx.amount, 50)
        self.assertIsNotNone(tx.created_at)


class BadgeDefinitionTests(TestCase):
    def test_create_badge(self):
        badge = BadgeDefinition.objects.create(
            code="first_submit",
            name="First Submission",
            description="Submit your first assignment",
            tier="bronze",
            icon="trophy",
            criteria_json={"type": "submission_count", "threshold": 1},
        )
        self.assertEqual(badge.code, "first_submit")
        self.assertEqual(badge.tier, "bronze")
        self.assertEqual(badge.criteria_json["threshold"], 1)
        self.assertTrue(badge.is_active)

    def test_code_unique(self):
        BadgeDefinition.objects.create(
            code="unique_code",
            name="Badge A",
            description="desc",
            tier="silver",
            icon="star",
        )
        with self.assertRaises(IntegrityError):
            BadgeDefinition.objects.create(
                code="unique_code",
                name="Badge B",
                description="desc",
                tier="gold",
                icon="star",
            )


class StudentBadgeTests(TestCase):
    def setUp(self):
        self.badge = BadgeDefinition.objects.create(
            code="test_badge",
            name="Test Badge",
            description="For testing",
            tier="bronze",
            icon="medal",
        )

    def test_create_earned_badge(self):
        user = _create_test_user("gam_user4", "student")
        sb = StudentBadge.objects.create(student=user, badge=self.badge)
        self.assertEqual(sb.progress_percent, 100)
        self.assertIsNone(sb.awarded_by)

    def test_unique_together(self):
        user = _create_test_user("gam_user5", "student")
        StudentBadge.objects.create(student=user, badge=self.badge)
        with self.assertRaises(IntegrityError):
            StudentBadge.objects.create(student=user, badge=self.badge)

    def test_teacher_awarded(self):
        student = _create_test_user("gam_user6", "student")
        teacher = _create_test_user("gam_teacher1", "teacher")
        sb = StudentBadge.objects.create(
            student=student,
            badge=self.badge,
            awarded_by=teacher,
            award_reason="Outstanding participation",
        )
        self.assertEqual(sb.awarded_by, teacher)
        self.assertEqual(sb.award_reason, "Outstanding participation")
