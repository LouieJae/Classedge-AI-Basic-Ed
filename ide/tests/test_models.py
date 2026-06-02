from django.test import TestCase
from django.db import IntegrityError

from ide.models import CodingExercise, CodeSubmission
from activity.models.activity_model import Activity, ActivityType
from course.models.term_model import Term
from course.models.semester_model import Semester
from ai_content.tests.test_models import _create_test_user, _create_subject
from datetime import date


class CodingExerciseModelTests(TestCase):
    def setUp(self):
        self.user = _create_test_user()
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
            activity_name="Hello World",
            activity_type=self.activity_type,
            subject=self.subject,
            term=self.term,
        )

    def test_create_exercise(self):
        test_cases = [
            {"input": "", "expected_output": "Hello World"},
        ]
        ex = CodingExercise.objects.create(
            activity=self.activity,
            language="python",
            starter_code="# write your code",
            solution_code='print("Hello World")',
            test_cases=test_cases,
        )
        self.assertEqual(ex.language, "python")
        self.assertEqual(ex.test_cases, test_cases)
        self.assertEqual(ex.time_limit_seconds, 5)
        self.assertEqual(ex.memory_limit_kb, 256000)
        self.assertIsNotNone(ex.created_at)

    def test_one_to_one_constraint(self):
        CodingExercise.objects.create(
            activity=self.activity,
            language="python",
            test_cases=[{"input": "", "expected_output": "hi"}],
        )
        with self.assertRaises(IntegrityError):
            CodingExercise.objects.create(
                activity=self.activity,
                language="javascript",
                test_cases=[{"input": "", "expected_output": "hi"}],
            )

    def test_create_submission(self):
        ex = CodingExercise.objects.create(
            activity=self.activity,
            language="python",
            test_cases=[{"input": "", "expected_output": "ok"}],
        )
        sub = CodeSubmission.objects.create(
            student=self.user,
            exercise=ex,
            code='print("ok")',
            language="python",
        )
        self.assertEqual(sub.status, "pending")
        self.assertIsNone(sub.score)
        self.assertIsNone(sub.execution_time_ms)
        self.assertIsNone(sub.memory_used_kb)

    def test_completed_submission(self):
        ex = CodingExercise.objects.create(
            activity=self.activity,
            language="python",
            test_cases=[{"input": "", "expected_output": "ok"}],
        )
        sub = CodeSubmission.objects.create(
            student=self.user,
            exercise=ex,
            code='print("ok")',
            language="python",
            status="completed",
            score=1.0,
            result_json={"passed": 1, "total": 1},
            execution_time_ms=42,
        )
        self.assertEqual(sub.status, "completed")
        self.assertEqual(sub.score, 1.0)
        self.assertEqual(sub.result_json, {"passed": 1, "total": 1})
        self.assertEqual(sub.execution_time_ms, 42)
