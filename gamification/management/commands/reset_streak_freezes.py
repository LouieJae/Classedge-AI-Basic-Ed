from django.conf import settings
from django.core.management.base import BaseCommand
from gamification.models import StudentGamification


class Command(BaseCommand):
    help = "Reset streak freezes to the monthly allowance for all students."

    def handle(self, *args, **options):
        monthly = getattr(settings, "GAMIFICATION_STREAK_FREEZE_MONTHLY", 1)
        updated = StudentGamification.objects.update(streak_freezes_available=monthly)
        self.stdout.write(
            self.style.SUCCESS(f"Reset streak freezes to {monthly} for {updated} students.")
        )
