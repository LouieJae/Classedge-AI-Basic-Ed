from django.test import TestCase, Client
from django.urls import reverse

from activity.models.activity_model import Activity, ActivityType
from activity.models.student_activity_model import StudentActivity
from ai_content.tests.test_models import _create_test_user, _create_subject
from course.models.semester_model import Semester
from course.models.subject_enrollment_model import SubjectEnrollment
from course.models.term_model import Term
from gamification.models import StudentGamification, StudentBadge, BadgeDefinition
from gamification.teacher_models import TeacherRecognition
from module.models.module import Module
from module.models.student_progress import StudentProgress

import datetime


def _make_semester():
    today = datetime.date.today()
    return Semester.objects.create(
        semester_name="First",
        start_date=today - datetime.timedelta(days=30),
        end_date=today + datetime.timedelta(days=60),
    )


def _enroll(student, subject, semester):
    return SubjectEnrollment.objects.create(
        student=student, subject=subject, semester=semester, status="enrolled",
    )


class SubjectPanelViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = _create_test_user("sp3_teach", "teacher")
        self.student1 = _create_test_user("sp3_stu1", "student")
        self.student2 = _create_test_user("sp3_stu2", "student")
        self.subject = _create_subject()
        self.subject.assign_teacher = self.teacher
        self.subject.save()
        self.semester = _make_semester()
        _enroll(self.student1, self.subject, self.semester)
        _enroll(self.student2, self.subject, self.semester)
        # ensure StudentGamification exists
        StudentGamification.objects.get_or_create(student=self.student1)
        StudentGamification.objects.get_or_create(student=self.student2)
        self.url = reverse("subject_analytics_panel", args=[self.subject.pk])

    def test_panel_requires_teacher(self):
        """Unauthenticated and student users cannot access the panel."""
        # unauthenticated
        r = self.client.get(self.url)
        self.assertNotEqual(r.status_code, 200)
        # student
        self.client.force_login(self.student1)
        r = self.client.get(self.url)
        self.assertNotEqual(r.status_code, 200)

    def test_panel_returns_full_page(self):
        """Panel response is a full HTML page (not an HTMX fragment) — it
        now renders inside base_operation.html as a dedicated route."""
        self.client.force_login(self.teacher)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        content = r.content.decode().lower()
        self.assertIn("<html", content)
        self.assertIn(self.subject.subject_name.lower(), content)

    def test_panel_non_owner_teacher_gets_403(self):
        """A teacher who doesn't own/collaborate on the subject gets 403."""
        other_teacher = _create_test_user("sp3_other_teach", "teacher")
        self.client.force_login(other_teacher)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)

    def test_panel_summary_tiles_in_context(self):
        """Context contains the 4 summary tile keys."""
        self.client.force_login(self.teacher)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        for key in ("avg_score", "at_risk_count", "completion_pct", "streak_count"):
            self.assertIn(key, r.context)

    def test_panel_student_table_in_context(self):
        """Context contains student_rows with expected keys."""
        self.client.force_login(self.teacher)
        r = self.client.get(self.url)
        self.assertIn("student_rows", r.context)
        for row in r.context["student_rows"]:
            for key in ("student", "avg_score", "risk_level", "streak", "badge_count"):
                self.assertIn(key, row)

    def test_panel_student_table_sorted_by_risk(self):
        """High-risk students appear before low-risk students in student_rows."""
        self.client.force_login(self.teacher)
        r = self.client.get(self.url)
        rows = r.context["student_rows"]
        RISK_ORDER = {"high": 0, "medium": 1, "low": 2}
        risk_values = [RISK_ORDER[row["risk_level"]] for row in rows]
        self.assertEqual(risk_values, sorted(risk_values))

    def test_panel_heatmap_in_context(self):
        """Context contains heatmap_rows and heatmap_students."""
        Module.objects.create(subject=self.subject, file_name="Module 1")
        StudentProgress.objects.create(
            student=self.student1,
            module=Module.objects.filter(subject=self.subject).first(),
            progress=75,
        )
        self.client.force_login(self.teacher)
        r = self.client.get(self.url)
        self.assertIn("heatmap_rows", r.context)
        self.assertIn("heatmap_students", r.context)

    def test_panel_xp_chart_in_context(self):
        """Context contains xp_chart as a list of 4 ints."""
        self.client.force_login(self.teacher)
        r = self.client.get(self.url)
        self.assertIn("xp_chart", r.context)
        self.assertEqual(len(r.context["xp_chart"]), 4)


class StudentDetailViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = _create_test_user("sd_teach", "teacher")
        self.student = _create_test_user("sd_stu", "student")
        self.subject = _create_subject()
        self.subject.assign_teacher = self.teacher
        self.subject.save()
        self.semester = _make_semester()
        _enroll(self.student, self.subject, self.semester)
        StudentGamification.objects.get_or_create(student=self.student)
        self.url = reverse("subject_student_detail", args=[self.subject.pk, self.student.pk])

    def test_student_detail_requires_teacher(self):
        """Unauthenticated and student users cannot access student detail."""
        r = self.client.get(self.url)
        self.assertNotEqual(r.status_code, 200)
        self.client.force_login(self.student)
        r = self.client.get(self.url)
        self.assertNotEqual(r.status_code, 200)

    def test_student_detail_non_owner_gets_403(self):
        """Teacher who doesn't own the subject gets 403."""
        other = _create_test_user("sd_other_teach", "teacher")
        self.client.force_login(other)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)

    def test_student_detail_renders(self):
        """Owner teacher gets 200 and expected context keys."""
        self.client.force_login(self.teacher)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        for key in ("subject", "student", "semester", "avg_score", "total_xp", "login_streak",
                    "risk_level", "activity_history", "risk_breakdown",
                    "module-progress", "xp_stats", "badges", "recognitions"):
            self.assertIn(key, r.context, msg=f"Missing context key: {key}")

    def test_student_detail_activity_history(self):
        """Activity history contains activities for this subject."""
        term = Term.objects.create(
            semester=self.semester, term_name="Term 1",
            start_date=self.semester.start_date, end_date=self.semester.end_date,
        )
        act_type = ActivityType.objects.create(name="Quiz")
        act = Activity.objects.create(
            activity_name="Quiz 1", subject=self.subject, term=term,
            max_score=100, is_graded=True, activity_type=act_type,
        )
        import datetime as dt
        StudentActivity.objects.create(
            student=self.student, activity=act, subject=self.subject,
            total_score=85, end_time=dt.datetime.now(),
        )
        self.client.force_login(self.teacher)
        r = self.client.get(self.url)
        history = r.context["activity_history"]
        names = [a["name"] for a in history]
        self.assertIn("Quiz 1", names)

    def test_student_detail_risk_breakdown_keys(self):
        """risk_breakdown contains grade_score, completion_score, attendance_score."""
        self.client.force_login(self.teacher)
        r = self.client.get(self.url)
        rb = r.context["risk_breakdown"]
        for key in ("grade_score", "completion_score", "attendance_score"):
            self.assertIn(key, rb)

    def test_student_detail_module_progress(self):
        """module_progress lists modules with progress and status."""
        Module.objects.create(subject=self.subject, file_name="Chapter 1")
        self.client.force_login(self.teacher)
        r = self.client.get(self.url)
        mp = r.context["module-progress"]
        self.assertTrue(len(mp) >= 1)
        for entry in mp:
            for key in ("module", "progress", "status"):
                self.assertIn(key, entry)

    def test_student_detail_recognition_history(self):
        """Recognitions sent by this teacher to this student appear in context."""
        TeacherRecognition.objects.create(
            teacher=self.teacher, student=self.student,
            message="Great work!", xp_awarded=10,
        )
        self.client.force_login(self.teacher)
        r = self.client.get(self.url)
        self.assertEqual(r.context["recognitions"].count(), 1)
        self.assertEqual(r.context["recognitions"].first().message, "Great work!")
