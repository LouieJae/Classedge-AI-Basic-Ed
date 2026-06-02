from datetime import date, timedelta
from django.db import transaction
from gamification.models import StudentGamification


def update_login_streak(student):
    """Update login streak for the student. Call on each login."""
    with transaction.atomic():
        gam = StudentGamification.objects.select_for_update().get(student=student)
        today = date.today()

        if gam.last_active_date == today:
            return

        if gam.last_active_date == today - timedelta(days=1):
            gam.login_streak += 1
        elif (
            gam.last_active_date == today - timedelta(days=2)
            and gam.streak_freezes_available > 0
        ):
            gam.login_streak += 1
            gam.streak_freezes_available -= 1
        else:
            gam.login_streak = 1

        gam.last_active_date = today
        gam.save(update_fields=["login_streak", "last_active_date", "streak_freezes_available"])


def update_submission_streak(student, is_on_time):
    """Update submission streak. Call on each activity submission."""
    gam, _ = StudentGamification.objects.get_or_create(student=student)
    if is_on_time:
        gam.submission_streak += 1
    else:
        gam.submission_streak = 0
    gam.save(update_fields=["submission_streak"])


def update_accuracy_streak(student, score_pct):
    """Update accuracy streak. Call after each graded activity score."""
    gam, _ = StudentGamification.objects.get_or_create(student=student)
    if score_pct >= 80:
        gam.accuracy_streak += 1
    else:
        gam.accuracy_streak = 0
    gam.save(update_fields=["accuracy_streak"])
