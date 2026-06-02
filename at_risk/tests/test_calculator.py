from datetime import date

from django.test import TestCase, override_settings

from at_risk.calculator import calculate_risk_scores
from ai_content.tests.test_models import _create_test_user, _create_subject
from activity.models.activity_model import Activity, ActivityType
from activity.models.student_activity_model import StudentActivity
from course.models.semester_model import Semester
from course.models.term_model import Term
from course.models.subject_enrollment_model import SubjectEnrollment
from course.models.attendance_model import Attendance, AttendanceStatus

_RISK_SETTINGS = {
    "AT_RISK_WEIGHTS": {"grade": 0.5, "completion": 0.3, "attendance": 0.2},
    "AT_RISK_HIGH_THRESHOLD": 40,
    "AT_RISK_MEDIUM_THRESHOLD": 65,
}


@override_settings(**_RISK_SETTINGS)
class CalculateRiskScoresTests(TestCase):
    def setUp(self):
        self.teacher = _create_test_user(username="teacher_risk", role_name="teacher")
        self.student = _create_test_user(username="student_risk", role_name="student")
        self.subject = _create_subject()

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

        self.quiz_type, _ = ActivityType.objects.get_or_create(name="Quiz")
        self.present_status, _ = AttendanceStatus.objects.get_or_create(status="Present")
        self.absent_status, _ = AttendanceStatus.objects.get_or_create(status="Absent")

    def test_low_grades_high_risk(self):
        activity = Activity.objects.create(
            activity_name="Quiz 1",
            activity_type=self.quiz_type,
            subject=self.subject,
            term=self.term,
            max_score=100,
            is_graded=True,
        )
        # Second activity the student never submits — drops completion to 50%
        Activity.objects.create(
            activity_name="Quiz 2",
            activity_type=self.quiz_type,
            subject=self.subject,
            term=self.term,
            max_score=100,
            is_graded=True,
        )
        StudentActivity.objects.create(
            student=self.student,
            activity=activity,
            subject=self.subject,
            term=self.term,
            total_score=10,
        )
        # Mark absent for attendance
        Attendance.objects.create(
            student=self.student,
            subject=self.subject,
            date=date(2026, 8, 16),
            status=self.absent_status,

        )

        results = calculate_risk_scores(self.subject, self.semester)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["student_id"], self.student.pk)
        self.assertLess(results[0]["risk_score"], 40)
        self.assertEqual(results[0]["risk_level"], "high")

    def test_perfect_student_low_risk(self):
        activity = Activity.objects.create(
            activity_name="Quiz 1",
            activity_type=self.quiz_type,
            subject=self.subject,
            term=self.term,
            max_score=100,
            is_graded=True,
        )
        StudentActivity.objects.create(
            student=self.student,
            activity=activity,
            subject=self.subject,
            term=self.term,
            total_score=95,
        )
        Attendance.objects.create(
            student=self.student,
            subject=self.subject,
            date=date(2026, 8, 16),
            status=self.present_status,

        )

        results = calculate_risk_scores(self.subject, self.semester)
        self.assertEqual(len(results), 1)
        self.assertGreater(results[0]["risk_score"], 65)
        self.assertEqual(results[0]["risk_level"], "low")

    def test_no_graded_activities_neutral_grade(self):
        results = calculate_risk_scores(self.subject, self.semester)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["grade_score"], 50)

    def test_no_attendance_records_neutral(self):
        results = calculate_risk_scores(self.subject, self.semester)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["attendance_score"], 50)

    def test_empty_subject_returns_empty(self):
        SubjectEnrollment.objects.all().delete()
        results = calculate_risk_scores(self.subject, self.semester)
        self.assertEqual(results, [])

    def test_weights_applied(self):
        activity = Activity.objects.create(
            activity_name="Quiz 1",
            activity_type=self.quiz_type,
            subject=self.subject,
            term=self.term,
            max_score=100,
            is_graded=True,
        )
        StudentActivity.objects.create(
            student=self.student,
            activity=activity,
            subject=self.subject,
            term=self.term,
            total_score=75,
        )

        results = calculate_risk_scores(self.subject, self.semester)
        r = results[0]
        expected = r["grade_score"] * 0.5 + r["completion_score"] * 0.3 + r["attendance_score"] * 0.2
        self.assertAlmostEqual(r["risk_score"], expected, places=1)
