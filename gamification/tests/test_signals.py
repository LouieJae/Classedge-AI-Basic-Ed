from datetime import date, timedelta
from django.contrib.auth.signals import user_logged_in
from django.test import TestCase, RequestFactory, override_settings
from ai_content.tests.test_models import _create_test_user, _create_subject
from activity.models.activity_model import Activity, ActivityType
from activity.models.student_activity_model import StudentActivity
from course.models.semester_model import Semester
from course.models.term_model import Term
from gamification.models import StudentGamification, XPTransaction

_GAM_SETTINGS = {
    "GAMIFICATION_XP_RATES": {
        "submission": 50, "early_submission": 75,
        "score_90": 30, "score_75": 15,
        "daily_login": 5, "perfect_attendance_week": 50,
    },
    "GAMIFICATION_STREAK_FREEZE_MONTHLY": 1,
}


@override_settings(**_GAM_SETTINGS)
class ActivitySignalTests(TestCase):
    def setUp(self):
        self.student = _create_test_user(username="sig_student", role_name="student")
        self.subject = _create_subject()
        self.semester = Semester.objects.create(
            semester_name="Sem", start_date=date(2026, 1, 1), end_date=date(2027, 12, 31),
        )
        self.term = Term.objects.create(
            term_name="Prelim", semester=self.semester,
            start_date=date(2026, 8, 15), end_date=date(2026, 10, 15),
        )
        self.quiz_type, _ = ActivityType.objects.get_or_create(name="Quiz")

    def test_submission_awards_xp(self):
        activity = Activity.objects.create(
            activity_name="Quiz 1", activity_type=self.quiz_type,
            subject=self.subject, term=self.term, max_score=100, is_graded=True,
        )
        StudentActivity.objects.create(
            student=self.student, activity=activity,
            subject=self.subject, term=self.term, total_score=60,
        )
        tx = XPTransaction.objects.filter(student=self.student, source_type="activity")
        self.assertTrue(tx.exists())

    def test_high_score_awards_bonus(self):
        activity = Activity.objects.create(
            activity_name="Quiz 2", activity_type=self.quiz_type,
            subject=self.subject, term=self.term, max_score=100, is_graded=True,
        )
        StudentActivity.objects.create(
            student=self.student, activity=activity,
            subject=self.subject, term=self.term, total_score=95,
        )
        score_tx = XPTransaction.objects.filter(student=self.student, source_type="activity_score_90")
        self.assertTrue(score_tx.exists())

    def test_no_double_award_on_update(self):
        activity = Activity.objects.create(
            activity_name="Quiz 3", activity_type=self.quiz_type,
            subject=self.subject, term=self.term, max_score=100, is_graded=True,
        )
        sa = StudentActivity.objects.create(
            student=self.student, activity=activity,
            subject=self.subject, term=self.term, total_score=50,
        )
        count_before = XPTransaction.objects.filter(student=self.student, source_type="activity").count()
        sa.total_score = 60
        sa.save()
        count_after = XPTransaction.objects.filter(student=self.student, source_type="activity").count()
        self.assertEqual(count_before, count_after)


@override_settings(**_GAM_SETTINGS)
class LoginSignalTests(TestCase):
    def setUp(self):
        self.student = _create_test_user(username="sig_login", role_name="student")
        self.factory = RequestFactory()

    def test_login_awards_xp(self):
        request = self.factory.get("/")
        request.session = {}
        user_logged_in.send(sender=self.student.__class__, request=request, user=self.student)
        tx = XPTransaction.objects.filter(student=self.student, source_type="login")
        self.assertTrue(tx.exists())

    def test_second_login_same_day_no_double(self):
        request = self.factory.get("/")
        request.session = {}
        user_logged_in.send(sender=self.student.__class__, request=request, user=self.student)
        user_logged_in.send(sender=self.student.__class__, request=request, user=self.student)
        count = XPTransaction.objects.filter(student=self.student, source_type="login").count()
        self.assertEqual(count, 1)
