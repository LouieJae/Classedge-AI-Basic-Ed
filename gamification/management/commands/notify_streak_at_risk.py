"""Nudge students whose login streak will break unless they log in today.

Run once daily (cron / Celery beat), ideally in the afternoon/evening so the
reminder lands while there's still time to act:

    python manage.py notify_streak_at_risk

Mirrors the streak math in gamification/streaks.py::update_login_streak —
a streak survives a login today when:
  * last active yesterday (gap 1)                          → normal continue, or
  * last active 2 days ago AND a streak freeze is left     → freeze-saved continue.
Students already active today are fine; students 3+ days stale (or 2 days stale
with no freeze) have already lost the streak and can't save it today, so neither
group is notified. Deduped per student per day via the notify() dedupe window.
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.urls import reverse, NoReverseMatch

from gamification.models import StudentGamification
from logs.notifications import notify


class Command(BaseCommand):
    help = "Notify students whose login streak will break unless they log in today."

    def handle(self, *args, **options):
        today = date.today()
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)

        try:
            path = reverse("student_dashboard")
        except NoReverseMatch:
            path = ""

        # Active streak, not yet logged in today, still saveable by a login today.
        at_risk = StudentGamification.objects.filter(login_streak__gt=0).filter(
            Q(last_active_date=yesterday)
            | Q(last_active_date=two_days_ago, streak_freezes_available__gt=0)
        ).select_related("student")

        created = 0
        for gam in at_risk:
            days = gam.login_streak
            msg = (
                f"Your {days}-day login streak is about to break — "
                f"log in today to keep it alive."
            )
            n = notify(
                gam.student,
                msg,
                name="Streak at risk",
                path=path,
                entity_type="streak_risk",
                entity_id=gam.student_id,
                dedupe_hours=20,
            )
            if n:
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f"notify_streak_at_risk: {created} reminder(s) created "
            f"({at_risk.count()} student(s) at risk)."
        ))
