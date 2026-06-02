from datetime import date

from django.test import TestCase, Client, override_settings

from ai_content.tests.test_models import _create_test_user, _create_subject
from course.models.semester_model import Semester
from course.models.subject_enrollment_model import SubjectEnrollment
from gamification.models import BadgeDefinition, StudentBadge, StudentGamification
from subject.models.subject_model import Subject

_GAM_SETTINGS = {
    "GAMIFICATION_XP_RATES": {
        "submission": 50, "early_submission": 75,
        "score_90": 30, "score_75": 15,
        "daily_login": 5, "perfect_attendance_week": 50,
    },
    "GAMIFICATION_STREAK_FREEZE_MONTHLY": 1,
}


@override_settings(**_GAM_SETTINGS)
class StudentDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = _create_test_user(username="dash_stu", role_name="student")
        self.teacher = _create_test_user(username="dash_teach", role_name="teacher")
        self.subject = _create_subject()
        self.semester = Semester.objects.create(
            semester_name="Sem",
            start_date=date(2026, 1, 1),
            end_date=date(2027, 12, 31),
        )
        SubjectEnrollment.objects.create(
            student=self.student, subject=self.subject,
            semester=self.semester, status="enrolled",
        )
        StudentGamification.objects.create(
            student=self.student, total_xp=500, current_level=2,
            login_streak=5, submission_streak=3, accuracy_streak=2,
        )

    def test_student_redirected_from_old_dashboard(self):
        self.client.login(username="dash_stu", password="testpass")
        resp = self.client.get("/dashboard/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("gamification/dashboard", resp.url)

    def test_student_dashboard_renders(self):
        self.client.login(username="dash_stu", password="testpass")
        resp = self.client.get("/gamification/dashboard/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "data-theme")

    def test_dashboard_shows_xp(self):
        self.client.login(username="dash_stu", password="testpass")
        resp = self.client.get("/gamification/dashboard/")
        self.assertContains(resp, "500")

    def test_teacher_sees_old_dashboard(self):
        self.client.login(username="dash_teach", password="testpass")
        resp = self.client.get("/dashboard/")
        self.assertEqual(resp.status_code, 200)

    def test_unauthenticated_redirects(self):
        resp = self.client.get("/gamification/dashboard/")
        self.assertEqual(resp.status_code, 302)


@override_settings(**_GAM_SETTINGS)
class LeaderboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = _create_test_user(username="lb_stu", role_name="student")

    def test_leaderboard_renders(self):
        self.client.login(username="lb_stu", password="testpass")
        resp = self.client.get("/gamification/leaderboard/")
        self.assertEqual(resp.status_code, 200)


@override_settings(**_GAM_SETTINGS)
class BadgeCollectionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = _create_test_user(username="bc_stu", role_name="student")

    def test_badge_collection_renders(self):
        self.client.login(username="bc_stu", password="testpass")
        resp = self.client.get("/gamification/badges/")
        self.assertEqual(resp.status_code, 200)

    def test_shows_badges(self):
        self.client.login(username="bc_stu", password="testpass")
        badge = BadgeDefinition.objects.first()
        if badge:
            StudentBadge.objects.get_or_create(student=self.student, badge=badge)
        resp = self.client.get("/gamification/badges/")
        self.assertEqual(resp.status_code, 200)


@override_settings(**_GAM_SETTINGS)
class CalendarTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = _create_test_user(username="cal_stu", role_name="student")

    def test_calendar_renders(self):
        self.client.login(username="cal_stu", password="testpass")
        resp = self.client.get("/gamification/calendar/")
        self.assertEqual(resp.status_code, 200)

    def test_calendar_month_navigation(self):
        self.client.login(username="cal_stu", password="testpass")
        resp = self.client.get("/gamification/calendar/?year=2026&month=3")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "March 2026")


@override_settings(**_GAM_SETTINGS)
class QuestMapTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = _create_test_user(username="qm_stu", role_name="student")
        self.subject = _create_subject()
        self.semester = Semester.objects.create(
            semester_name="Sem", start_date=date(2026, 1, 1), end_date=date(2027, 12, 31),
        )
        SubjectEnrollment.objects.create(
            student=self.student, subject=self.subject,
            semester=self.semester, status="enrolled",
        )

    def test_picker_renders(self):
        self.client.login(username="qm_stu", password="testpass")
        resp = self.client.get("/gamification/quest-map/")
        self.assertEqual(resp.status_code, 200)

    def test_map_renders(self):
        self.client.login(username="qm_stu", password="testpass")
        resp = self.client.get(f"/gamification/quest-map/{self.subject.pk}/")
        self.assertEqual(resp.status_code, 200)


@override_settings(**_GAM_SETTINGS)
class ThemeTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = _create_test_user(username="theme_stu", role_name="student")

    def test_theme_cookie_respected(self):
        self.client.login(username="theme_stu", password="testpass")
        self.client.cookies["theme"] = "light"
        resp = self.client.get("/gamification/dashboard/")
        self.assertContains(resp, 'data-theme="light"')
