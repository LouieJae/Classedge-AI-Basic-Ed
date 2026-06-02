import json
from datetime import date
from unittest.mock import patch

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
class ExerciseDetailTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = _create_test_user(username="ide_v_stu", role_name="student")
        self.teacher = _create_test_user(username="ide_v_teach", role_name="teacher")
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
            activity_name="Add Numbers",
            activity_type=self.activity_type,
            subject=self.subject, term=self.term,
            max_score=100, is_graded=True,
        )
        self.exercise = CodingExercise.objects.create(
            activity=self.activity, language="python",
            starter_code="def add(a, b):\n    pass",
            test_cases=[{"input": "2 3", "expected_output": "5", "label": "Test 1"}],
        )

    def test_exercise_detail_renders(self):
        self.client.login(username="ide_v_stu", password="testpass")
        resp = self.client.get(f"/ide/exercise/{self.activity.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "monaco")

    def test_unauthenticated_redirects(self):
        resp = self.client.get(f"/ide/exercise/{self.activity.pk}/")
        self.assertEqual(resp.status_code, 302)

    @patch("ide.views.run_code_submission")
    def test_submit_creates_submission(self, mock_task):
        mock_task.delay = lambda *a: None
        self.client.login(username="ide_v_stu", password="testpass")
        resp = self.client.post(
            f"/ide/exercise/{self.activity.pk}/submit/",
            json.dumps({"code": "print(5)"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("submission_id", data)
        self.assertTrue(CodeSubmission.objects.filter(pk=data["submission_id"]).exists())

    def test_submission_status_endpoint(self):
        self.client.login(username="ide_v_stu", password="testpass")
        sub = CodeSubmission.objects.create(
            student=self.student, exercise=self.exercise,
            code="print(5)", language="python",
            status="completed", score=1.0,
            result_json={"tests": [{"label": "T1", "passed": True}]},
        )
        resp = self.client.get(f"/ide/submission/{sub.pk}/status/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["score"], 1.0)


@override_settings(**_GAM_SETTINGS)
class TeacherSetupTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = _create_test_user(username="ide_s_stu", role_name="student")
        self.teacher = _create_test_user(username="ide_s_teach", role_name="teacher")
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
            activity_name="Hello World",
            activity_type=self.activity_type,
            subject=self.subject, term=self.term,
            max_score=100, is_graded=True,
        )

    def test_teacher_can_access_setup(self):
        self.client.login(username="ide_s_teach", password="testpass")
        resp = self.client.get(f"/ide/exercise/{self.activity.pk}/setup/")
        self.assertEqual(resp.status_code, 200)

    def test_student_cannot_access_setup(self):
        self.client.login(username="ide_s_stu", password="testpass")
        resp = self.client.get(f"/ide/exercise/{self.activity.pk}/setup/")
        self.assertEqual(resp.status_code, 302)
