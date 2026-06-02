import math
from django.test import TestCase
from ai_content.tests.test_models import _create_test_user
from gamification.models import StudentGamification, XPTransaction
from gamification.services import award_xp


class AwardXPTests(TestCase):
    def setUp(self):
        self.student = _create_test_user(username="xp_svc_stu", role_name="student")

    def test_award_xp_creates_transaction(self):
        tx = award_xp(self.student, 50, "test award", "test", source_id=1)
        self.assertIsNotNone(tx)
        self.assertEqual(tx.amount, 50)
        self.assertEqual(XPTransaction.objects.count(), 1)

    def test_award_xp_updates_total(self):
        award_xp(self.student, 50, "first", "test", source_id=1)
        award_xp(self.student, 30, "second", "test", source_id=2)
        gam = StudentGamification.objects.get(student=self.student)
        self.assertEqual(gam.total_xp, 80)

    def test_award_xp_auto_creates_gamification(self):
        self.assertFalse(StudentGamification.objects.filter(student=self.student).exists())
        award_xp(self.student, 10, "auto create", "test", source_id=1)
        self.assertTrue(StudentGamification.objects.filter(student=self.student).exists())

    def test_duplicate_source_returns_none(self):
        award_xp(self.student, 50, "first", "activity", source_id=99)
        result = award_xp(self.student, 50, "duplicate", "activity", source_id=99)
        self.assertIsNone(result)
        self.assertEqual(XPTransaction.objects.count(), 1)

    def test_level_calculation(self):
        # level = floor(sqrt(xp / 100)), 10000 XP → level 10
        award_xp(self.student, 10000, "big award", "test", source_id=1)
        gam = StudentGamification.objects.get(student=self.student)
        self.assertEqual(gam.current_level, 10)

    def test_level_stays_1_for_small_xp(self):
        award_xp(self.student, 50, "small", "test", source_id=1)
        gam = StudentGamification.objects.get(student=self.student)
        # floor(sqrt(50/100)) = 0, but min level is 1
        self.assertEqual(gam.current_level, 1)

    def test_level_20_at_40000_xp(self):
        award_xp(self.student, 40000, "massive", "test", source_id=1)
        gam = StudentGamification.objects.get(student=self.student)
        self.assertEqual(gam.current_level, 20)
