from datetime import date, timedelta
from django.test import TestCase, Client, override_settings
from django.utils import timezone

from ai_content.tests.test_models import _create_test_user, _create_subject
from course.models.semester_model import Semester
from course.models.subject_enrollment_model import SubjectEnrollment
from subject.models.subject_model import Subject
from gamification.teacher_models import (
    TeacherGamification, IPTransaction, TeacherBadgeDefinition, TeacherBadge,
    TeacherChallenge, TeacherChallengeProgress, TeacherRecognition, TeacherRating,
)

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
class AwardIPTests(TestCase):
    def setUp(self):
        self.teacher = _create_test_user(username="ip_teach", role_name="teacher")

    def test_award_ip_creates_transaction(self):
        from gamification.teacher_services import award_ip
        tx = award_ip(self.teacher, 10, "Test award", "test", source_id=1)
        self.assertIsNotNone(tx)
        self.assertEqual(tx.amount, 10)
        gam = TeacherGamification.objects.get(teacher=self.teacher)
        self.assertEqual(gam.total_ip, 10)

    def test_award_ip_dedup(self):
        from gamification.teacher_services import award_ip
        tx1 = award_ip(self.teacher, 10, "First", "test", source_id=99)
        tx2 = award_ip(self.teacher, 10, "Duplicate", "test", source_id=99)
        self.assertIsNotNone(tx1)
        self.assertIsNone(tx2)
        gam = TeacherGamification.objects.get(teacher=self.teacher)
        self.assertEqual(gam.total_ip, 10)

    def test_rank_progression(self):
        from gamification.teacher_services import award_ip
        award_ip(self.teacher, 100, "Rank up", "test", source_id=1)
        gam = TeacherGamification.objects.get(teacher=self.teacher)
        self.assertEqual(gam.rank_tier, "bronze")
        self.assertEqual(gam.rank_title, "Guide")
        self.assertEqual(gam.current_rank, "bronze_guide")

        award_ip(self.teacher, 200, "Rank up", "test", source_id=2)
        gam.refresh_from_db()
        self.assertEqual(gam.rank_tier, "silver")
        self.assertEqual(gam.rank_title, "Catalyst")

        award_ip(self.teacher, 900, "Rank up", "test", source_id=3)
        gam.refresh_from_db()
        self.assertEqual(gam.rank_tier, "gold")
        self.assertEqual(gam.rank_title, "Luminary")


@override_settings(**_GAM_SETTINGS)
class TeacherBadgeTests(TestCase):
    def setUp(self):
        self.teacher = _create_test_user(username="tb_teach", role_name="teacher")
        TeacherGamification.objects.create(teacher=self.teacher, total_ip=15)

    def test_teacher_badge_evaluation(self):
        badge = TeacherBadgeDefinition.objects.create(
            code="first_impact", name="First Impact", description="Earn 10 IP",
            tier="bronze", icon="⚡", criteria_json={"type": "teacher_ip_total", "threshold": 10},
        )
        from gamification.teacher_badges import evaluate_teacher_badges
        evaluate_teacher_badges(self.teacher)
        self.assertTrue(TeacherBadge.objects.filter(teacher=self.teacher, badge=badge).exists())

    def test_teacher_badge_not_awarded_twice(self):
        badge = TeacherBadgeDefinition.objects.create(
            code="first_impact_2", name="First Impact", description="Earn 10 IP",
            tier="bronze", icon="⚡", criteria_json={"type": "teacher_ip_total", "threshold": 10},
        )
        from gamification.teacher_badges import evaluate_teacher_badges
        evaluate_teacher_badges(self.teacher)
        evaluate_teacher_badges(self.teacher)
        self.assertEqual(TeacherBadge.objects.filter(teacher=self.teacher, badge=badge).count(), 1)

    def test_teacher_badge_progress(self):
        badge = TeacherBadgeDefinition.objects.create(
            code="first_impact_3", name="First Impact", description="Earn 100 IP",
            tier="bronze", icon="⚡", criteria_json={"type": "teacher_ip_total", "threshold": 100},
        )
        from gamification.teacher_badges import compute_teacher_badge_progress
        progress = compute_teacher_badge_progress(self.teacher, badge)
        self.assertEqual(progress, 15)


@override_settings(**_GAM_SETTINGS)
class TeacherChallengeTests(TestCase):
    def setUp(self):
        self.teacher = _create_test_user(username="tc_teach", role_name="teacher")
        self.challenge = TeacherChallenge.objects.create(
            code="test_challenge", name="Test Challenge",
            description="Test", challenge_type="milestone",
            criteria_json={"type": "ip_milestone", "threshold": 50},
            ip_reward=15,
        )

    def test_challenge_completion(self):
        from gamification.teacher_services import evaluate_teacher_challenges
        gam = TeacherGamification.objects.create(teacher=self.teacher, total_ip=0)
        progress = TeacherChallengeProgress.objects.create(
            teacher=self.teacher, challenge=self.challenge,
            current_value=50, target_value=50,
        )
        evaluate_teacher_challenges(self.teacher)
        progress.refresh_from_db()
        self.assertIsNotNone(progress.completed_at)
        gam.refresh_from_db()
        self.assertEqual(gam.total_ip, 15)

    def test_challenge_expiry(self):
        from gamification.teacher_services import evaluate_teacher_challenges
        TeacherGamification.objects.create(teacher=self.teacher, total_ip=0)
        progress = TeacherChallengeProgress.objects.create(
            teacher=self.teacher, challenge=self.challenge,
            current_value=50, target_value=50,
            expires_at=timezone.now() - timedelta(days=1),
        )
        evaluate_teacher_challenges(self.teacher)
        progress.refresh_from_db()
        self.assertIsNone(progress.completed_at)


@override_settings(**_GAM_SETTINGS)
class RecognitionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = _create_test_user(username="rec_teach", role_name="teacher")
        self.student = _create_test_user(username="rec_stu", role_name="student")

    def test_recognition_creates_and_awards(self):
        self.client.login(username="rec_teach", password="testpass")
        resp = self.client.post("/gamification/recognition/send/", {
            "student_id": self.student.pk,
            "message": "Great work on the quiz!",
            "xp_amount": 25,
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(TeacherRecognition.objects.filter(
            teacher=self.teacher, student=self.student,
        ).exists())
        self.assertEqual(
            IPTransaction.objects.filter(teacher=self.teacher, source_type="recognition_sent").count(), 1,
        )
        from gamification.models import XPTransaction
        self.assertTrue(XPTransaction.objects.filter(
            student=self.student, source_type="recognition",
        ).exists())


@override_settings(**_GAM_SETTINGS)
class RatingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = _create_test_user(username="rat_teach", role_name="teacher")
        self.student = _create_test_user(username="rat_stu", role_name="student")
        self.semester = Semester.objects.create(
            semester_name="Rating Sem",
            start_date=date(2026, 1, 1), end_date=date(2027, 12, 31),
        )

    def test_rating_creates_and_awards_ip(self):
        self.client.login(username="rat_stu", password="testpass")
        resp = self.client.post("/gamification/rating/submit/", {
            "teacher_id": self.teacher.pk,
            "stars": 5,
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(TeacherRating.objects.filter(
            teacher=self.teacher, student=self.student,
        ).exists())
        self.assertEqual(
            IPTransaction.objects.filter(teacher=self.teacher, source_type="star_rating_5").count(), 1,
        )

    def test_rating_unique_per_semester(self):
        self.client.login(username="rat_stu", password="testpass")
        self.client.post("/gamification/rating/submit/", {
            "teacher_id": self.teacher.pk, "stars": 4,
        }, content_type="application/json")
        self.client.post("/gamification/rating/submit/", {
            "teacher_id": self.teacher.pk, "stars": 5,
        }, content_type="application/json")
        self.assertEqual(
            TeacherRating.objects.filter(teacher=self.teacher, student=self.student).count(), 1,
        )
        rating = TeacherRating.objects.get(teacher=self.teacher, student=self.student)
        self.assertEqual(rating.stars, 5)

    def test_rating_aggregate(self):
        from django.db.models import Avg
        stu2 = _create_test_user(username="rat_stu2", role_name="student")
        TeacherRating.objects.create(
            teacher=self.teacher, student=self.student,
            stars=5, semester=self.semester,
        )
        TeacherRating.objects.create(
            teacher=self.teacher, student=stu2,
            stars=3, semester=self.semester,
        )
        avg = TeacherRating.objects.filter(teacher=self.teacher).aggregate(
            avg=Avg("stars"),
        )["avg"]
        self.assertAlmostEqual(avg, 4.0)


@override_settings(**_GAM_SETTINGS)
class SignalTests(TestCase):
    def setUp(self):
        self.teacher = _create_test_user(username="sig_teach", role_name="teacher")
        self.student = _create_test_user(username="sig_stu", role_name="student")
        self.subject = _create_subject()
        Subject.objects.filter(pk=self.subject.pk).update(assign_teacher=self.teacher)
        self.semester = Semester.objects.create(
            semester_name="Sig Sem",
            start_date=date(2026, 1, 1), end_date=date(2027, 12, 31),
        )
        SubjectEnrollment.objects.create(
            student=self.student, subject=self.subject,
            semester=self.semester, status="enrolled",
        )

    def test_signal_student_badge_awards_ip(self):
        from gamification.models import BadgeDefinition, StudentBadge
        badge = BadgeDefinition.objects.create(
            code="sig_test", name="Test Badge", description="Test",
            tier="bronze", icon="🏅", target_role="student",
        )
        StudentBadge.objects.create(student=self.student, badge=badge)
        self.assertTrue(
            IPTransaction.objects.filter(
                teacher=self.teacher, source_type="student_badge_earned",
            ).exists(),
        )


from django.core.management import call_command


@override_settings(**_GAM_SETTINGS)
class ManagementCommandTests(TestCase):
    def test_seed_teacher_badges_command(self):
        call_command("seed_teacher_badges")
        self.assertEqual(TeacherBadgeDefinition.objects.count(), 8)
        call_command("seed_teacher_badges")
        self.assertEqual(TeacherBadgeDefinition.objects.count(), 8)

    def test_seed_teacher_challenges_command(self):
        call_command("seed_teacher_challenges")
        self.assertEqual(TeacherChallenge.objects.count(), 10)
        call_command("seed_teacher_challenges")
        self.assertEqual(TeacherChallenge.objects.count(), 10)


@override_settings(**_GAM_SETTINGS)
class DashboardIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = _create_test_user(username="di_teach", role_name="teacher")
        self.subject = _create_subject()
        Subject.objects.filter(pk=self.subject.pk).update(assign_teacher=self.teacher)
        self.semester = Semester.objects.create(
            semester_name="DI Sem",
            start_date=date(2026, 1, 1), end_date=date(2027, 12, 31),
        )

    def test_dashboard_shows_rank(self):
        TeacherGamification.objects.create(
            teacher=self.teacher, total_ip=150,
            current_rank="bronze_guide", rank_tier="bronze", rank_title="Guide",
        )
        self.client.login(username="di_teach", password="testpass")
        resp = self.client.get("/dashboard/")
        self.assertEqual(resp.context["rank_tier"], "bronze")
        self.assertEqual(resp.context["rank_title"], "Guide")
        self.assertEqual(resp.context["total_ip"], 150)

    def test_dashboard_shows_challenges(self):
        TeacherGamification.objects.create(teacher=self.teacher)
        challenge = TeacherChallenge.objects.create(
            code="di_test", name="Test", description="Test",
            challenge_type="milestone", criteria_json={},
            ip_reward=10,
        )
        TeacherChallengeProgress.objects.create(
            teacher=self.teacher, challenge=challenge,
            current_value=3, target_value=5,
        )
        self.client.login(username="di_teach", password="testpass")
        resp = self.client.get("/dashboard/")
        self.assertIn("challenges", resp.context)
        self.assertEqual(len(resp.context["challenges"]), 1)

    def test_dashboard_shows_badges(self):
        TeacherGamification.objects.create(teacher=self.teacher)
        badge_def = TeacherBadgeDefinition.objects.create(
            code="di_badge", name="Test Badge", description="Test",
            tier="bronze", icon="\u26a1",
        )
        TeacherBadge.objects.create(teacher=self.teacher, badge=badge_def)
        self.client.login(username="di_teach", password="testpass")
        resp = self.client.get("/dashboard/")
        self.assertIn("teacher_badges", resp.context)
        self.assertEqual(len(resp.context["teacher_badges"]), 1)
