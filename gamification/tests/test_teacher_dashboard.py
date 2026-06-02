from datetime import date
from django.test import TestCase, Client, RequestFactory, override_settings
from ai_content.tests.test_models import _create_test_user
from gamification.context_processors import student_context


class ContextProcessorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.teacher = _create_test_user(username="cp_teach", role_name="teacher")
        self.student = _create_test_user(username="cp_stu", role_name="student")

    def test_teacher_gets_is_teacher_role(self):
        request = self.factory.get("/")
        request.user = self.teacher
        request.COOKIES = {}
        ctx = student_context(request)
        self.assertTrue(ctx["is_teacher_role"])
        self.assertFalse(ctx["is_student_role"])

    def test_student_does_not_get_is_teacher_role(self):
        request = self.factory.get("/")
        request.user = self.student
        request.COOKIES = {}
        ctx = student_context(request)
        self.assertFalse(ctx["is_teacher_role"])
        self.assertTrue(ctx["is_student_role"])


from activity.models.activity_model import Activity, ActivityType
from activity.models.student_activity_model import StudentActivity
from course.models.semester_model import Semester
from course.models.term_model import Term
from course.models.subject_enrollment_model import SubjectEnrollment
from subject.models.subject_model import Subject
from gamification.models import StudentGamification
from module.models.module import Module
from module.models.student_progress import StudentProgress

_GAM_SETTINGS = {
    "GAMIFICATION_XP_RATES": {
        "submission": 50, "early_submission": 75, "score_90": 30,
        "score_75": 15, "daily_login": 5, "perfect_attendance_week": 50,
    },
    "GAMIFICATION_STREAK_FREEZE_MONTHLY": 1,
    "AT_RISK_WEIGHTS": {"grade": 0.5, "completion": 0.3, "attendance": 0.2},
    "AT_RISK_HIGH_THRESHOLD": 40,
    "AT_RISK_MEDIUM_THRESHOLD": 65,
}


@override_settings(**_GAM_SETTINGS)
class TeacherDashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = _create_test_user(username="td_teach", role_name="teacher")
        self.student1 = _create_test_user(username="td_stu1", role_name="student")
        self.student2 = _create_test_user(username="td_stu2", role_name="student")
        from ai_content.tests.test_models import _create_subject
        self.subject = _create_subject()
        Subject.objects.filter(pk=self.subject.pk).update(assign_teacher=self.teacher)
        self.semester = Semester.objects.create(
            semester_name="Sem", start_date=date(2026, 1, 1), end_date=date(2027, 12, 31),
        )
        self.term = Term.objects.create(
            term_name="Prelim", semester=self.semester,
            start_date=date(2026, 8, 15), end_date=date(2026, 10, 15),
        )
        SubjectEnrollment.objects.create(
            student=self.student1, subject=self.subject,
            semester=self.semester, status="enrolled",
        )
        SubjectEnrollment.objects.create(
            student=self.student2, subject=self.subject,
            semester=self.semester, status="enrolled",
        )

    def test_teacher_sees_new_dashboard(self):
        self.client.login(username="td_teach", password="testpass")
        resp = self.client.get("/dashboard/")
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "teacher/gamification/teacher_dashboard.html")

    def test_student_does_not_see_teacher_dashboard(self):
        self.client.login(username="td_stu1", password="testpass")
        resp = self.client.get("/dashboard/")
        # Students get redirected to student_dashboard
        self.assertEqual(resp.status_code, 302)

    def test_dashboard_shows_subject_cards(self):
        self.client.login(username="td_teach", password="testpass")
        resp = self.client.get("/dashboard/")
        self.assertIn("subjects", resp.context)
        self.assertEqual(len(resp.context["subjects"]), 1)

    def test_dashboard_metric_cards_present(self):
        self.client.login(username="td_teach", password="testpass")
        resp = self.client.get("/dashboard/")
        self.assertIn("metrics", resp.context)
        self.assertEqual(len(resp.context["metrics"]), 4)

    def test_dashboard_spotlight_with_data(self):
        quiz_type, _ = ActivityType.objects.get_or_create(name="Quiz")
        # Student1: two activities, scores improving
        for i, score in enumerate([60, 90]):
            act = Activity.objects.create(
                activity_name=f"Quiz {i}", activity_type=quiz_type,
                subject=self.subject, term=self.term, max_score=100, is_graded=True,
            )
            StudentActivity.objects.create(
                student=self.student1, activity=act,
                subject=self.subject, term=self.term, total_score=score,
            )
        self.client.login(username="td_teach", password="testpass")
        resp = self.client.get("/dashboard/")
        self.assertIn("spotlight", resp.context)

    def test_empty_semester_no_crash(self):
        # Delete only the semester created in setUp (avoid touching pre-existing protected rows)
        SubjectEnrollment.objects.filter(semester=self.semester).delete()
        Term.objects.filter(semester=self.semester).delete()
        self.semester.delete()
        self.client.login(username="td_teach", password="testpass")
        resp = self.client.get("/dashboard/")
        self.assertEqual(resp.status_code, 200)
