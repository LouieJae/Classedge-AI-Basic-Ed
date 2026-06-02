from django.core.management.base import BaseCommand
from gamification.teacher_models import TeacherChallenge

CHALLENGES = [
    {"code": "quick_grader", "name": "Quick Grader", "description": "Grade all pending activities this week", "challenge_type": "rotating", "criteria_json": {"type": "grade_all_pending"}, "ip_reward": 10, "duration_days": 7},
    {"code": "streak_builder", "name": "Streak Builder", "description": "Get 5 students to start a login streak this week", "challenge_type": "rotating", "criteria_json": {"type": "student_streaks_started", "count": 5}, "ip_reward": 8, "duration_days": 7},
    {"code": "recognition_week", "name": "Recognition Week", "description": "Send 5 recognition shoutouts this week", "challenge_type": "rotating", "criteria_json": {"type": "recognitions_sent", "count": 5}, "ip_reward": 6, "duration_days": 7},
    {"code": "full_house", "name": "Full House", "description": "Reach 90%+ completion rate across all your subjects this month", "challenge_type": "rotating", "criteria_json": {"type": "completion_rate", "threshold": 90}, "ip_reward": 20, "duration_days": 30},
    {"code": "risk_rescue", "name": "Risk Rescue", "description": "Move 3 at-risk students down a risk level this month", "challenge_type": "rotating", "criteria_json": {"type": "at_risk_recoveries", "count": 3}, "ip_reward": 25, "duration_days": 30},
    {"code": "first_steps", "name": "First Steps", "description": "Earn your first 50 Impact Points", "challenge_type": "milestone", "criteria_json": {"type": "ip_milestone", "threshold": 50}, "ip_reward": 15, "duration_days": None},
    {"code": "badge_collector", "name": "Badge Collector", "description": "Earn 5 teacher badges", "challenge_type": "milestone", "criteria_json": {"type": "teacher_badges_earned", "count": 5}, "ip_reward": 20, "duration_days": None},
    {"code": "perfect_term", "name": "Perfect Term", "description": "Achieve 100% activity completion rate for a full term", "challenge_type": "milestone", "criteria_json": {"type": "perfect_term_completion"}, "ip_reward": 30, "duration_days": None},
    {"code": "honor_roll", "name": "Honor Roll", "description": "All your subjects above 80% class average simultaneously", "challenge_type": "milestone", "criteria_json": {"type": "all_subjects_above", "threshold": 80}, "ip_reward": 40, "duration_days": None},
    {"code": "century_club", "name": "Century Club", "description": "Send 100 recognitions to students", "challenge_type": "milestone", "criteria_json": {"type": "recognitions_sent", "count": 100}, "ip_reward": 50, "duration_days": None},
]

class Command(BaseCommand):
    help = "Seed the 10 teacher challenge definitions"

    def handle(self, *args, **options):
        created_count = 0
        for ch_data in CHALLENGES:
            _, created = TeacherChallenge.objects.get_or_create(code=ch_data["code"], defaults=ch_data)
            if created:
                created_count += 1
        self.stdout.write(f"Teacher challenges: {created_count} created, {len(CHALLENGES) - created_count} already existed.")
