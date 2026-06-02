from datetime import date
from unittest.mock import patch

from django.test import TestCase, override_settings

from activity.models.activity_model import Activity, ActivityType
from activity.models.student_activity_model import StudentActivity
from course.models.semester_model import Semester
from course.models.term_model import Term
from gamification.models import XPTransaction
from ide.models import CodingExercise, CodeSubmission
from ide.tasks import run_code_submission
from ai_content.tests.test_models import _create_test_user, _create_subject

_GAM_SETTINGS = {
    "GAMIFICATION_XP_RATES": {
        "submission": 50, "early_submission": 75,
        "score_90": 30, "score_75": 15,
        "daily_login": 5, "perfect_attendance_week": 50,
    },
    "GAMIFICATION_STREAK_FREEZE_MONTHLY": 1,
}


def _judge0_result(stdout, status_id=3, status_desc="Accepted", time_val=0.05, memory=2048):
    """Helper to build a mock Judge0 response."""
    return {
        "stdout": stdout,
        "stderr": None,
        "compile_output": None,
        "status": {"id": status_id, "description": status_desc},
        "time": time_val,
        "memory": memory,
    }


@override_settings(**_GAM_SETTINGS)
class RunCodeSubmissionTests(TestCase):
    def setUp(self):
        self.student = _create_test_user(username="task_student", role_name="student")
        self.subject = _create_subject()
        self.semester = Semester.objects.create(
            semester_name="First Semester",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 15),
        )
        self.term = Term.objects.create(
            term_name="Prelim",
            semester=self.semester,
            start_date=date(2026, 8, 15),
            end_date=date(2026, 10, 15),
        )
        self.activity_type, _ = ActivityType.objects.get_or_create(name="Coding")
        self.activity = Activity.objects.create(
            activity_name="Sum Two Numbers",
            activity_type=self.activity_type,
            subject=self.subject,
            term=self.term,
            max_score=100,
        )
        self.test_cases = [
            {"input": "1 2", "expected_output": "3"},
            {"input": "5 10", "expected_output": "15"},
            {"input": "0 0", "expected_output": "0"},
        ]
        self.exercise = CodingExercise.objects.create(
            activity=self.activity,
            language="python",
            starter_code="# add two numbers",
            solution_code="a, b = map(int, input().split())\nprint(a + b)",
            test_cases=self.test_cases,
        )

    def _make_submission(self):
        return CodeSubmission.objects.create(
            student=self.student,
            exercise=self.exercise,
            code="a, b = map(int, input().split())\nprint(a + b)",
            language="python",
        )

    @patch("ide.tasks.submit_code")
    def test_all_tests_pass(self, mock_submit):
        mock_submit.side_effect = [
            _judge0_result("3"),
            _judge0_result("15"),
            _judge0_result("0"),
        ]
        sub = self._make_submission()
        run_code_submission(sub.pk)
        sub.refresh_from_db()

        self.assertEqual(sub.status, "completed")
        self.assertEqual(sub.score, 1.0)
        self.assertEqual(len(sub.result_json["tests"]), 3)
        self.assertTrue(all(t["passed"] for t in sub.result_json["tests"]))

    @patch("ide.tasks.submit_code")
    def test_partial_pass(self, mock_submit):
        mock_submit.side_effect = [
            _judge0_result("3"),
            _judge0_result("15"),
            _judge0_result("999"),  # wrong
        ]
        sub = self._make_submission()
        run_code_submission(sub.pk)
        sub.refresh_from_db()

        self.assertEqual(sub.status, "completed")
        self.assertAlmostEqual(sub.score, 2 / 3, places=3)
        self.assertTrue(sub.result_json["tests"][0]["passed"])
        self.assertTrue(sub.result_json["tests"][1]["passed"])
        self.assertFalse(sub.result_json["tests"][2]["passed"])

    @patch("ide.tasks.submit_code")
    def test_updates_student_activity(self, mock_submit):
        mock_submit.side_effect = [
            _judge0_result("3"),
            _judge0_result("15"),
            _judge0_result("0"),
        ]
        sub = self._make_submission()
        run_code_submission(sub.pk)

        sa = StudentActivity.objects.get(student=self.student, activity=self.activity)
        self.assertEqual(sa.total_score, 100.0)

    @patch("ide.tasks.submit_code")
    def test_awards_xp_high_score(self, mock_submit):
        mock_submit.side_effect = [
            _judge0_result("3"),
            _judge0_result("15"),
            _judge0_result("0"),
        ]
        sub = self._make_submission()
        run_code_submission(sub.pk)

        xp = XPTransaction.objects.filter(
            student=self.student, source_type="coding", source_id=sub.pk,
        )
        self.assertTrue(xp.exists())
        self.assertEqual(xp.first().amount, 30)

    @patch("ide.tasks.submit_code")
    def test_compilation_error(self, mock_submit):
        mock_submit.side_effect = [
            _judge0_result("", status_id=6, status_desc="Compilation Error", time_val=0, memory=0),
            _judge0_result("", status_id=6, status_desc="Compilation Error", time_val=0, memory=0),
            _judge0_result("", status_id=6, status_desc="Compilation Error", time_val=0, memory=0),
        ]
        sub = self._make_submission()
        run_code_submission(sub.pk)
        sub.refresh_from_db()

        self.assertEqual(sub.status, "completed")
        self.assertEqual(sub.score, 0.0)
        self.assertFalse(any(t["passed"] for t in sub.result_json["tests"]))
