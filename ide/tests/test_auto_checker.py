from datetime import date
from django.test import TestCase, Client, override_settings
from ai_content.tests.test_models import _create_test_user, _create_subject
from activity.models.activity_model import Activity, ActivityType
from course.models.semester_model import Semester
from course.models.term_model import Term
from ide.models import CodingExercise, CodeSubmission
from subject.models.subject_model import Subject

_GAM_SETTINGS = {
    "GAMIFICATION_XP_RATES": {
        "submission": 50, "early_submission": 75, "score_90": 30,
        "score_75": 15, "daily_login": 5, "perfect_attendance_week": 50,
    },
    "GAMIFICATION_STREAK_FREEZE_MONTHLY": 1,
}


@override_settings(**_GAM_SETTINGS)
class CodingOverviewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = _create_test_user(username="ac_teach", role_name="teacher")
        self.student = _create_test_user(username="ac_stu", role_name="student")
        self.subject = _create_subject()
        Subject.objects.filter(pk=self.subject.pk).update(assign_teacher=self.teacher)
        self.semester = Semester.objects.create(
            semester_name="Sem", start_date=date(2026, 1, 1), end_date=date(2027, 12, 31),
        )
        self.term = Term.objects.create(
            term_name="Prelim", semester=self.semester,
            start_date=date(2026, 8, 15), end_date=date(2026, 10, 15),
        )
        self.activity_type, _ = ActivityType.objects.get_or_create(name="Coding")
        self.activity = Activity.objects.create(
            activity_name="Sum", activity_type=self.activity_type,
            subject=self.subject, term=self.term, max_score=100,
        )
        self.exercise = CodingExercise.objects.create(
            activity=self.activity, language="python",
            starter_code="", solution_code="",
            test_cases=[{"input": "1 2", "expected_output": "3"}],
        )

    def test_teacher_sees_overview(self):
        self.client.login(username="ac_teach", password="testpass")
        resp = self.client.get("/ide/overview/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("exercises", resp.context)

    def test_student_cannot_access_overview(self):
        self.client.login(username="ac_stu", password="testpass")
        resp = self.client.get("/ide/overview/")
        self.assertEqual(resp.status_code, 403)

    def test_overview_shows_exercise_stats(self):
        CodeSubmission.objects.create(
            student=self.student, exercise=self.exercise,
            code="print(3)", language="python",
            status="completed", score=1.0,
        )
        self.client.login(username="ac_teach", password="testpass")
        resp = self.client.get("/ide/overview/")
        exercises = resp.context["exercises"]
        self.assertEqual(len(exercises), 1)
        self.assertEqual(exercises[0]["attempted_count"], 1)


@override_settings(**_GAM_SETTINGS)
class CodingExerciseResultsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = _create_test_user(username="res_teach", role_name="teacher")
        self.student = _create_test_user(username="res_stu", role_name="student")
        self.subject = _create_subject()
        Subject.objects.filter(pk=self.subject.pk).update(assign_teacher=self.teacher)
        self.semester = Semester.objects.create(
            semester_name="Sem2", start_date=date(2026, 1, 1), end_date=date(2027, 12, 31),
        )
        self.term = Term.objects.create(
            term_name="Prelim2", semester=self.semester,
            start_date=date(2026, 8, 15), end_date=date(2026, 10, 15),
        )
        self.activity_type, _ = ActivityType.objects.get_or_create(name="Coding")
        self.activity = Activity.objects.create(
            activity_name="Multiply", activity_type=self.activity_type,
            subject=self.subject, term=self.term, max_score=100,
        )
        self.exercise = CodingExercise.objects.create(
            activity=self.activity, language="python",
            starter_code="", solution_code="",
            test_cases=[{"input": "2 3", "expected_output": "6"}],
        )
        self.submission = CodeSubmission.objects.create(
            student=self.student, exercise=self.exercise,
            code="print(6)", language="python",
            status="completed", score=1.0,
            result_json={"tests": [{"test": 1, "passed": True, "stdout": "6", "expected": "6"}]},
            execution_time_ms=42,
        )

    def test_results_page_shows_submissions(self):
        self.client.login(username="res_teach", password="testpass")
        resp = self.client.get(f"/ide/exercise/{self.exercise.pk}/results/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("students", resp.context)
        self.assertEqual(len(resp.context["students"]), 1)

    def test_score_override_updates_submission(self):
        self.client.login(username="res_teach", password="testpass")
        resp = self.client.post(f"/ide/submission/{self.submission.pk}/override/", {
            "new_score": "0.8",
            "override_note": "Accepted alternative approach",
        })
        self.assertEqual(resp.status_code, 302)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.score, 0.8)
        self.assertIn("override", self.submission.result_json)
        self.assertEqual(self.submission.result_json["override"]["note"], "Accepted alternative approach")

    def test_student_cannot_override(self):
        self.client.login(username="res_stu", password="testpass")
        resp = self.client.post(f"/ide/submission/{self.submission.pk}/override/", {
            "new_score": "1.0",
            "override_note": "hack",
        })
        self.assertEqual(resp.status_code, 403)
