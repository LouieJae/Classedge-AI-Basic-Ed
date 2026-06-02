from datetime import date
from django.test import TestCase, override_settings
from django.utils import timezone
from ai_content.tests.test_models import _create_test_user, _create_subject
from gamification.models import CodingStats
from activity.models.activity_model import Activity, ActivityType
from course.models.semester_model import Semester
from course.models.term_model import Term
from ide.models import CodingExercise, CodeSubmission
from gamification.coding_stats_service import update_coding_stats, update_coding_stats_kata
from gamification.side_activity_models import SideActivity, SideActivityAttempt


class CodingStatsModelTests(TestCase):
    def test_create_coding_stats(self):
        student = _create_test_user(username="cs_student", role_name="student")
        stats = CodingStats.objects.create(student=student)
        self.assertEqual(stats.total_submissions, 0)
        self.assertEqual(stats.perfect_submissions, 0)
        self.assertEqual(stats.total_katas, 0)
        self.assertEqual(stats.perfect_katas, 0)
        self.assertEqual(stats.languages_used, [])
        self.assertEqual(stats.fast_perfects, 0)
        self.assertEqual(stats.current_streak, 0)
        self.assertEqual(stats.best_streak, 0)

    def test_one_per_student(self):
        student = _create_test_user(username="cs_unique", role_name="student")
        CodingStats.objects.create(student=student)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            CodingStats.objects.create(student=student)


_GAM_SETTINGS = {
    "GAMIFICATION_XP_RATES": {
        "submission": 50, "early_submission": 75, "score_90": 30,
        "score_75": 15, "daily_login": 5, "perfect_attendance_week": 50,
    },
    "GAMIFICATION_STREAK_FREEZE_MONTHLY": 1,
}


@override_settings(**_GAM_SETTINGS)
class UpdateCodingStatsTests(TestCase):
    def setUp(self):
        self.student = _create_test_user(username="ucs_student", role_name="student")
        self.subject = _create_subject()
        self.semester = Semester.objects.create(
            semester_name="Sem", start_date=date(2026, 1, 1), end_date=date(2027, 12, 31),
        )
        self.term = Term.objects.create(
            term_name="Prelim", semester=self.semester,
            start_date=date(2026, 8, 15), end_date=date(2026, 10, 15),
        )
        self.activity_type, _ = ActivityType.objects.get_or_create(name="Coding")
        self.activity = Activity.objects.create(
            activity_name="Test Ex", activity_type=self.activity_type,
            subject=self.subject, term=self.term, max_score=100,
        )
        self.exercise = CodingExercise.objects.create(
            activity=self.activity, language="python",
            starter_code="", solution_code="",
            test_cases=[{"input": "1", "expected_output": "1"}],
        )

    def _make_submission(self, score=1.0, execution_time_ms=100, language="python"):
        sub = CodeSubmission.objects.create(
            student=self.student, exercise=self.exercise,
            code="print(1)", language=language,
            status="completed", score=score,
            execution_time_ms=execution_time_ms,
        )
        return sub

    def test_perfect_submission_increments_stats(self):
        sub = self._make_submission(score=1.0, execution_time_ms=100)
        update_coding_stats(self.student, sub)
        stats = CodingStats.objects.get(student=self.student)
        self.assertEqual(stats.total_submissions, 1)
        self.assertEqual(stats.perfect_submissions, 1)
        self.assertEqual(stats.current_streak, 1)
        self.assertEqual(stats.best_streak, 1)

    def test_failed_submission_resets_streak(self):
        sub1 = self._make_submission(score=1.0)
        update_coding_stats(self.student, sub1)
        sub2 = self._make_submission(score=0.5)
        update_coding_stats(self.student, sub2)
        stats = CodingStats.objects.get(student=self.student)
        self.assertEqual(stats.total_submissions, 2)
        self.assertEqual(stats.perfect_submissions, 1)
        self.assertEqual(stats.current_streak, 0)
        self.assertEqual(stats.best_streak, 1)

    def test_new_language_appended(self):
        sub1 = self._make_submission(language="python")
        update_coding_stats(self.student, sub1)
        # Create a JS exercise
        act2 = Activity.objects.create(
            activity_name="JS Ex", activity_type=self.activity_type,
            subject=self.subject, term=self.term, max_score=100,
        )
        ex2 = CodingExercise.objects.create(
            activity=act2, language="javascript",
            starter_code="", solution_code="",
            test_cases=[{"input": "", "expected_output": "hello"}],
        )
        sub2 = CodeSubmission.objects.create(
            student=self.student, exercise=ex2,
            code="console.log('hello')", language="javascript",
            status="completed", score=1.0, execution_time_ms=50,
        )
        update_coding_stats(self.student, sub2)
        stats = CodingStats.objects.get(student=self.student)
        self.assertEqual(sorted(stats.languages_used), ["javascript", "python"])

    def test_fast_perfect_detection(self):
        sub = self._make_submission(score=1.0, execution_time_ms=300)
        update_coding_stats(self.student, sub)
        stats = CodingStats.objects.get(student=self.student)
        self.assertEqual(stats.fast_perfects, 1)

    def test_slow_perfect_not_fast(self):
        sub = self._make_submission(score=1.0, execution_time_ms=600)
        update_coding_stats(self.student, sub)
        stats = CodingStats.objects.get(student=self.student)
        self.assertEqual(stats.fast_perfects, 0)


@override_settings(**_GAM_SETTINGS)
class UpdateCodingStatsKataTests(TestCase):
    def setUp(self):
        self.student = _create_test_user(username="kata_stu", role_name="student")
        self.teacher = _create_test_user(username="kata_teach", role_name="teacher")
        self.subject = _create_subject()

    def _make_kata_attempt(self, score=1.0):
        kata = SideActivity.objects.create(
            subject=self.subject, sub_type="code_kata",
            title="Kata 1", content_json={"test_cases": [{"input": "1", "expected": "1"}]},
            xp_reward=10, created_by=self.teacher,
        )
        attempt = SideActivityAttempt.objects.create(
            student=self.student, side_activity=kata,
            completed_at=timezone.now(), score=score,
            time_taken_seconds=30, xp_awarded=10,
        )
        return attempt

    def test_kata_completion_increments(self):
        attempt = self._make_kata_attempt(score=1.0)
        update_coding_stats_kata(self.student, attempt)
        stats = CodingStats.objects.get(student=self.student)
        self.assertEqual(stats.total_katas, 1)
        self.assertEqual(stats.perfect_katas, 1)
        self.assertEqual(stats.current_streak, 1)

    def test_failed_kata_resets_streak(self):
        a1 = self._make_kata_attempt(score=1.0)
        update_coding_stats_kata(self.student, a1)
        a2 = self._make_kata_attempt(score=0.3)
        update_coding_stats_kata(self.student, a2)
        stats = CodingStats.objects.get(student=self.student)
        self.assertEqual(stats.total_katas, 2)
        self.assertEqual(stats.perfect_katas, 1)
        self.assertEqual(stats.current_streak, 0)
        self.assertEqual(stats.best_streak, 1)
