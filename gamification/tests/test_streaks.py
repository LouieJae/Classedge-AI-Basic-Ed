from datetime import date, timedelta
from django.test import TestCase
from ai_content.tests.test_models import _create_test_user
from gamification.models import StudentGamification
from gamification.streaks import update_login_streak, update_submission_streak, update_accuracy_streak


class LoginStreakTests(TestCase):
    def setUp(self):
        self.student = _create_test_user(username="streak_stu", role_name="student")
        self.gam = StudentGamification.objects.create(student=self.student)

    def test_first_login_sets_streak_to_1(self):
        update_login_streak(self.student)
        self.gam.refresh_from_db()
        self.assertEqual(self.gam.login_streak, 1)
        self.assertEqual(self.gam.last_active_date, date.today())

    def test_consecutive_day_increments(self):
        yesterday = date.today() - timedelta(days=1)
        self.gam.login_streak = 5
        self.gam.last_active_date = yesterday
        self.gam.save()
        update_login_streak(self.student)
        self.gam.refresh_from_db()
        self.assertEqual(self.gam.login_streak, 6)

    def test_same_day_no_op(self):
        self.gam.login_streak = 5
        self.gam.last_active_date = date.today()
        self.gam.save()
        update_login_streak(self.student)
        self.gam.refresh_from_db()
        self.assertEqual(self.gam.login_streak, 5)

    def test_gap_resets_streak(self):
        two_days_ago = date.today() - timedelta(days=2)
        self.gam.login_streak = 10
        self.gam.last_active_date = two_days_ago
        self.gam.streak_freezes_available = 0
        self.gam.save()
        update_login_streak(self.student)
        self.gam.refresh_from_db()
        self.assertEqual(self.gam.login_streak, 1)

    def test_freeze_preserves_streak_on_one_day_gap(self):
        two_days_ago = date.today() - timedelta(days=2)
        self.gam.login_streak = 10
        self.gam.last_active_date = two_days_ago
        self.gam.streak_freezes_available = 1
        self.gam.save()
        update_login_streak(self.student)
        self.gam.refresh_from_db()
        self.assertEqual(self.gam.login_streak, 11)
        self.assertEqual(self.gam.streak_freezes_available, 0)


class SubmissionStreakTests(TestCase):
    def setUp(self):
        self.student = _create_test_user(username="sub_streak", role_name="student")
        self.gam = StudentGamification.objects.create(student=self.student, submission_streak=5)

    def test_on_time_increments(self):
        update_submission_streak(self.student, is_on_time=True)
        self.gam.refresh_from_db()
        self.assertEqual(self.gam.submission_streak, 6)

    def test_late_resets(self):
        update_submission_streak(self.student, is_on_time=False)
        self.gam.refresh_from_db()
        self.assertEqual(self.gam.submission_streak, 0)


class AccuracyStreakTests(TestCase):
    def setUp(self):
        self.student = _create_test_user(username="acc_streak", role_name="student")
        self.gam = StudentGamification.objects.create(student=self.student, accuracy_streak=3)

    def test_high_score_increments(self):
        update_accuracy_streak(self.student, score_pct=85.0)
        self.gam.refresh_from_db()
        self.assertEqual(self.gam.accuracy_streak, 4)

    def test_low_score_resets(self):
        update_accuracy_streak(self.student, score_pct=70.0)
        self.gam.refresh_from_db()
        self.assertEqual(self.gam.accuracy_streak, 0)

    def test_exactly_80_increments(self):
        update_accuracy_streak(self.student, score_pct=80.0)
        self.gam.refresh_from_db()
        self.assertEqual(self.gam.accuracy_streak, 4)
