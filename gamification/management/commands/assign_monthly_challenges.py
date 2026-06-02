import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Profile
from gamification.teacher_models import TeacherChallenge, TeacherChallengeProgress
from roles.models import Role


class Command(BaseCommand):
    help = "Assign 1 random monthly challenge to each teacher"

    def handle(self, *args, **options):
        now = timezone.now()
        monthly = list(TeacherChallenge.objects.filter(
            is_active=True, challenge_type="rotating", duration_days=30,
        ))
        if not monthly:
            self.stdout.write("No active monthly challenges found.")
            return

        teacher_role = Role.objects.filter(name__iexact="teacher").first()
        if not teacher_role:
            self.stdout.write("No teacher role found.")
            return

        teacher_ids = Profile.objects.filter(role=teacher_role).values_list("user_id", flat=True)
        assigned_count = 0

        for teacher_id in teacher_ids:
            active_challenge_ids = set(
                TeacherChallengeProgress.objects.filter(
                    teacher_id=teacher_id, completed_at__isnull=True, expires_at__gt=now,
                ).values_list("challenge_id", flat=True)
            )
            available = [c for c in monthly if c.pk not in active_challenge_ids]
            if not available:
                continue

            challenge = random.choice(available)
            target = challenge.criteria_json.get("count", 1)
            TeacherChallengeProgress.objects.create(
                teacher_id=teacher_id, challenge=challenge,
                expires_at=now + timedelta(days=30),
                current_value=0, target_value=target,
            )
            assigned_count += 1

        self.stdout.write(f"Assigned {assigned_count} monthly challenges.")
