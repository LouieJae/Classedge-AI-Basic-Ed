from datetime import date

from django.test import TestCase, Client, override_settings

from ai_content.tests.test_models import _create_test_user, _create_subject
from activity.models.activity_model import Activity, ActivityType
from activity.models.student_activity_model import StudentActivity
from course.models.semester_model import Semester
from course.models.term_model import Term
from course.models.subject_enrollment_model import SubjectEnrollment
from subject.models.subject_model import Subject

_RISK_SETTINGS = {
    "AT_RISK_WEIGHTS": {"grade": 0.5, "completion": 0.3, "attendance": 0.2},
    "AT_RISK_HIGH_THRESHOLD": 40,
    "AT_RISK_MEDIUM_THRESHOLD": 65,
}


@override_settings(**_RISK_SETTINGS)
class DashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = _create_test_user(username="teacher_dash", role_name="teacher")
        self.student = _create_test_user(username="student_dash", role_name="student")
        self.subject = _create_subject()
        Subject.objects.filter(pk=self.subject.pk).update(assign_teacher=self.teacher)
        self.subject.refresh_from_db()

        self.semester = Semester.objects.create(
            semester_name="First Semester",
            start_date=date(2026, 1, 1),
            end_date=date(2027, 12, 31),
            passing_grade=75,
        )
        self.term = Term.objects.create(
            term_name="Prelim",
            semester=self.semester,
            start_date=date(2026, 8, 15),
            end_date=date(2026, 10, 15),
        )
        SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            semester=self.semester,
            status="enrolled",
        )

    def test_dashboard_renders_for_teacher(self):
        self.client.login(username="teacher_dash", password="testpass")
        resp = self.client.get(f"/at-risk/dashboard/{self.subject.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "At-risk")

    def test_dashboard_shows_students(self):
        self.client.login(username="teacher_dash", password="testpass")
        resp = self.client.get(f"/at-risk/dashboard/{self.subject.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "student_dash")

    def test_student_cannot_access(self):
        self.client.login(username="student_dash", password="testpass")
        resp = self.client.get(f"/at-risk/dashboard/{self.subject.pk}/")
        self.assertEqual(resp.status_code, 302)

    def test_unauthenticated_redirects(self):
        resp = self.client.get(f"/at-risk/dashboard/{self.subject.pk}/")
        self.assertEqual(resp.status_code, 302)
