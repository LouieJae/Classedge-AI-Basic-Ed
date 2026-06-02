from django.test import TestCase
from ai_content.tests.test_models import _create_test_user
from gamification.badges import evaluate_badges, compute_badge_progress
from gamification.models import BadgeDefinition, CodingStats, StudentBadge, StudentGamification, XPTransaction


class BadgeEvaluatorTests(TestCase):
    def setUp(self):
        self.student = _create_test_user(username="badge_eval", role_name="student")
        self.gam = StudentGamification.objects.create(student=self.student, total_xp=0, current_level=1)

    def test_xp_total_awards_badge(self):
        badge = BadgeDefinition.objects.create(
            code="xp_test", name="XP Test", description="desc", tier="bronze", icon="🏅",
            criteria_json={"type": "xp_total", "threshold": 100},
        )
        self.gam.total_xp = 150
        self.gam.save()
        evaluate_badges(self.student)
        self.assertTrue(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_xp_total_not_met(self):
        badge = BadgeDefinition.objects.create(
            code="xp_not_met", name="Not Met", description="desc", tier="bronze", icon="🏅",
            criteria_json={"type": "xp_total", "threshold": 1000},
        )
        self.gam.total_xp = 50
        self.gam.save()
        evaluate_badges(self.student)
        self.assertFalse(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_streak_evaluator(self):
        badge = BadgeDefinition.objects.create(
            code="streak_test", name="Streak Test", description="desc", tier="silver", icon="🔥",
            criteria_json={"type": "streak", "streak": "login", "threshold": 7},
        )
        self.gam.login_streak = 10
        self.gam.save()
        evaluate_badges(self.student)
        self.assertTrue(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_level_evaluator(self):
        badge = BadgeDefinition.objects.create(
            code="level_test", name="Level Test", description="desc", tier="gold", icon="⭐",
            criteria_json={"type": "level", "threshold": 5},
        )
        self.gam.current_level = 7
        self.gam.save()
        evaluate_badges(self.student)
        self.assertTrue(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_badges_earned_evaluator(self):
        for i in range(3):
            b = BadgeDefinition.objects.create(
                code=f"filler_{i}", name=f"Filler {i}", description="desc",
                tier="bronze", icon="🏅", criteria_json={},
            )
            StudentBadge.objects.create(student=self.student, badge=b)
        collector = BadgeDefinition.objects.create(
            code="collector_test", name="Collector", description="desc",
            tier="silver", icon="💎",
            criteria_json={"type": "badges_earned", "threshold": 3},
        )
        evaluate_badges(self.student)
        self.assertTrue(StudentBadge.objects.filter(student=self.student, badge=collector).exists())

    def test_activity_score_evaluator(self):
        from activity.models.activity_model import Activity, ActivityType
        from activity.models.student_activity_model import StudentActivity
        from course.models.semester_model import Semester
        from course.models.term_model import Term
        from ai_content.tests.test_models import _create_subject
        from datetime import date

        subject = _create_subject()
        semester = Semester.objects.create(
            semester_name="Sem", start_date=date(2026, 1, 1), end_date=date(2027, 12, 31),
        )
        term = Term.objects.create(
            term_name="Prelim", semester=semester,
            start_date=date(2026, 8, 15), end_date=date(2026, 10, 15),
        )
        quiz_type, _ = ActivityType.objects.get_or_create(name="Quiz")
        for i in range(3):
            act = Activity.objects.create(
                activity_name=f"Quiz {i}", activity_type=quiz_type,
                subject=subject, term=term, max_score=100, is_graded=True,
            )
            StudentActivity.objects.create(
                student=self.student, activity=act, subject=subject, term=term, total_score=95,
            )
        badge = BadgeDefinition.objects.create(
            code="score_test", name="Sharpshooter", description="desc", tier="silver", icon="🎯",
            criteria_json={"type": "activity_score", "min_pct": 90, "count": 3},
        )
        evaluate_badges(self.student)
        self.assertTrue(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_already_earned_not_re_evaluated(self):
        badge = BadgeDefinition.objects.create(
            code="already_earned", name="Already", description="desc", tier="bronze", icon="🏅",
            criteria_json={"type": "xp_total", "threshold": 10},
        )
        self.gam.total_xp = 100
        self.gam.save()
        StudentBadge.objects.create(student=self.student, badge=badge)
        evaluate_badges(self.student)
        self.assertEqual(StudentBadge.objects.filter(student=self.student, badge=badge).count(), 1)

    def test_empty_criteria_not_auto_awarded(self):
        BadgeDefinition.objects.create(
            code="teacher_only", name="Honor Roll", description="desc",
            tier="platinum", icon="🏆", criteria_json={},
        )
        evaluate_badges(self.student)
        self.assertEqual(StudentBadge.objects.filter(badge__code="teacher_only").count(), 0)


class SeedBadgesTests(TestCase):
    def test_starter_badges_exist(self):
        # The seed migration runs during test DB setup
        # 15 starter + 10 side activity + 9 coding = 34
        self.assertEqual(BadgeDefinition.objects.count(), 34)

    def test_all_codes_unique(self):
        codes = list(BadgeDefinition.objects.values_list("code", flat=True))
        self.assertEqual(len(codes), len(set(codes)))


class CodingBadgeEvaluatorTests(TestCase):
    def setUp(self):
        self.student = _create_test_user(username="coding_eval", role_name="student")
        self.gam = StudentGamification.objects.create(student=self.student, total_xp=0, current_level=1)

    def test_coding_first_badge(self):
        badge = BadgeDefinition.objects.create(
            code="t_first", name="First", description="d", tier="bronze", icon="x",
            criteria_json={"type": "coding_first"},
        )
        CodingStats.objects.create(student=self.student, total_submissions=1)
        evaluate_badges(self.student)
        self.assertTrue(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_coding_first_not_met(self):
        badge = BadgeDefinition.objects.create(
            code="t_first_no", name="First No", description="d", tier="bronze", icon="x",
            criteria_json={"type": "coding_first"},
        )
        CodingStats.objects.create(student=self.student, total_submissions=0, total_katas=0)
        evaluate_badges(self.student)
        self.assertFalse(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_coding_perfect_count_at_threshold(self):
        badge = BadgeDefinition.objects.create(
            code="t_perf5", name="Perf5", description="d", tier="bronze", icon="x",
            criteria_json={"type": "coding_perfect_count", "threshold": 5},
        )
        CodingStats.objects.create(student=self.student, perfect_submissions=5)
        evaluate_badges(self.student)
        self.assertTrue(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_coding_perfect_count_below_threshold(self):
        badge = BadgeDefinition.objects.create(
            code="t_perf5_no", name="Perf5 No", description="d", tier="bronze", icon="x",
            criteria_json={"type": "coding_perfect_count", "threshold": 5},
        )
        CodingStats.objects.create(student=self.student, perfect_submissions=4)
        evaluate_badges(self.student)
        self.assertFalse(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_coding_kata_count(self):
        badge = BadgeDefinition.objects.create(
            code="t_kata25", name="Kata25", description="d", tier="silver", icon="x",
            criteria_json={"type": "coding_kata_count", "threshold": 25},
        )
        CodingStats.objects.create(student=self.student, total_katas=25)
        evaluate_badges(self.student)
        self.assertTrue(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_coding_polyglot(self):
        badge = BadgeDefinition.objects.create(
            code="t_poly", name="Poly", description="d", tier="silver", icon="x",
            criteria_json={"type": "coding_polyglot"},
        )
        CodingStats.objects.create(student=self.student, languages_used=["python", "javascript"])
        evaluate_badges(self.student)
        self.assertTrue(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_coding_polyglot_one_lang(self):
        badge = BadgeDefinition.objects.create(
            code="t_poly_no", name="Poly No", description="d", tier="silver", icon="x",
            criteria_json={"type": "coding_polyglot"},
        )
        CodingStats.objects.create(student=self.student, languages_used=["python"])
        evaluate_badges(self.student)
        self.assertFalse(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_coding_fast_perfect(self):
        badge = BadgeDefinition.objects.create(
            code="t_fast3", name="Fast3", description="d", tier="silver", icon="x",
            criteria_json={"type": "coding_fast_perfect", "threshold": 3},
        )
        CodingStats.objects.create(student=self.student, fast_perfects=3)
        evaluate_badges(self.student)
        self.assertTrue(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_coding_streak(self):
        badge = BadgeDefinition.objects.create(
            code="t_streak10", name="Streak10", description="d", tier="gold", icon="x",
            criteria_json={"type": "coding_streak", "threshold": 10},
        )
        CodingStats.objects.create(student=self.student, best_streak=10)
        evaluate_badges(self.student)
        self.assertTrue(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_coding_total(self):
        badge = BadgeDefinition.objects.create(
            code="t_total100", name="Total100", description="d", tier="gold", icon="x",
            criteria_json={"type": "coding_total", "threshold": 100},
        )
        CodingStats.objects.create(student=self.student, total_submissions=60, total_katas=40)
        evaluate_badges(self.student)
        self.assertTrue(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_coding_legend_both_met(self):
        badge = BadgeDefinition.objects.create(
            code="t_legend", name="Legend", description="d", tier="platinum", icon="x",
            criteria_json={"type": "coding_legend", "perfect_threshold": 50, "kata_threshold": 100},
        )
        CodingStats.objects.create(student=self.student, perfect_submissions=50, total_katas=100)
        evaluate_badges(self.student)
        self.assertTrue(StudentBadge.objects.filter(student=self.student, badge=badge).exists())

    def test_coding_legend_only_one_met(self):
        badge = BadgeDefinition.objects.create(
            code="t_legend_no", name="Legend No", description="d", tier="platinum", icon="x",
            criteria_json={"type": "coding_legend", "perfect_threshold": 50, "kata_threshold": 100},
        )
        CodingStats.objects.create(student=self.student, perfect_submissions=50, total_katas=10)
        evaluate_badges(self.student)
        self.assertFalse(StudentBadge.objects.filter(student=self.student, badge=badge).exists())


class BadgeProgressTests(TestCase):
    def setUp(self):
        self.student = _create_test_user(username="prog_stu", role_name="student")
        self.gam = StudentGamification.objects.create(student=self.student, total_xp=0, current_level=1)

    def test_progress_partial_xp(self):
        badge = BadgeDefinition.objects.create(
            code="p_xp", name="XP", description="d", tier="bronze", icon="x",
            criteria_json={"type": "xp_total", "threshold": 100},
        )
        self.gam.total_xp = 50
        self.gam.save()
        self.assertEqual(compute_badge_progress(self.student, badge), 50)

    def test_progress_caps_at_100(self):
        badge = BadgeDefinition.objects.create(
            code="p_xp_cap", name="XP Cap", description="d", tier="bronze", icon="x",
            criteria_json={"type": "xp_total", "threshold": 100},
        )
        self.gam.total_xp = 200
        self.gam.save()
        self.assertEqual(compute_badge_progress(self.student, badge), 100)

    def test_progress_coding_perfect(self):
        badge = BadgeDefinition.objects.create(
            code="p_perf", name="Perf", description="d", tier="bronze", icon="x",
            criteria_json={"type": "coding_perfect_count", "threshold": 10},
        )
        CodingStats.objects.create(student=self.student, perfect_submissions=3)
        self.assertEqual(compute_badge_progress(self.student, badge), 30)

    def test_progress_coding_legend_compound(self):
        badge = BadgeDefinition.objects.create(
            code="p_legend", name="Legend", description="d", tier="platinum", icon="x",
            criteria_json={"type": "coding_legend", "perfect_threshold": 50, "kata_threshold": 100},
        )
        CodingStats.objects.create(student=self.student, perfect_submissions=25, total_katas=50)
        # 25/50 = 50% of first half (25 pts) + 50/100 = 50% of second half (25 pts) = 50
        self.assertEqual(compute_badge_progress(self.student, badge), 50)

    def test_progress_empty_criteria(self):
        badge = BadgeDefinition.objects.create(
            code="p_empty", name="Empty", description="d", tier="platinum", icon="x",
            criteria_json={},
        )
        self.assertEqual(compute_badge_progress(self.student, badge), 0)

    def test_progress_streak(self):
        badge = BadgeDefinition.objects.create(
            code="p_streak", name="Streak", description="d", tier="silver", icon="x",
            criteria_json={"type": "streak", "streak": "login", "threshold": 7},
        )
        self.gam.login_streak = 3
        self.gam.save()
        self.assertEqual(compute_badge_progress(self.student, badge), 42)  # 3/7 = 42%

    def test_progress_level(self):
        badge = BadgeDefinition.objects.create(
            code="p_level", name="Level", description="d", tier="gold", icon="x",
            criteria_json={"type": "level", "threshold": 10},
        )
        self.gam.current_level = 4
        self.gam.save()
        self.assertEqual(compute_badge_progress(self.student, badge), 40)
