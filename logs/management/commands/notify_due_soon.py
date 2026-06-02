"""Create "deadline approaching" notifications for upcoming activity due dates.

Run on a schedule (cron / Celery beat), e.g. hourly:

    python manage.py notify_due_soon --hours 48

For every Activity whose end_time falls inside the window, each enrolled
student who hasn't engaged yet (no StudentActivity row) gets a bell
notification linking to the assessment. Deduped per (student, activity) within
the window so repeated runs don't spam.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.urls import reverse, NoReverseMatch
from django.utils import timezone

from activity.models import Activity, StudentActivity
from course.models import SubjectEnrollment
from logs.notifications import notify


class Command(BaseCommand):
    help = "Notify enrolled students of activities due within the next N hours."

    def add_arguments(self, parser):
        parser.add_argument("--hours", type=int, default=48,
                            help="Look-ahead window in hours (default 48).")

    def handle(self, *args, **options):
        hours = options["hours"]
        now = timezone.now()
        window_end = now + timedelta(hours=hours)

        activities = Activity.objects.filter(
            end_time__gte=now, end_time__lte=window_end,
        ).select_related("subject")

        created = 0
        for act in activities:
            try:
                path = reverse("assessment-details", args=[act.local_id])
            except (NoReverseMatch, Exception):
                path = ""

            enrolled_ids = set(SubjectEnrollment.objects.filter(
                subject=act.subject, status="enrolled",
            ).values_list("student_id", flat=True))
            if not enrolled_ids:
                continue

            # Students who've already started/submitted this activity — skip them.
            engaged_ids = set(StudentActivity.objects.filter(
                activity=act, student_id__in=enrolled_ids,
            ).values_list("student_id", flat=True))

            from accounts.models import CustomUser
            todo = enrolled_ids - engaged_ids
            if not todo:
                continue
            due_str = timezone.localtime(act.end_time).strftime("%b %d, %I:%M %p")
            for student in CustomUser.objects.filter(id__in=todo):
                n = notify(
                    student,
                    f"“{act.activity_name}” is due {due_str}.",
                    name="Deadline approaching",
                    path=path,
                    entity_type="due_soon",
                    entity_id=act.local_id,
                    due_at=act.end_time,
                    dedupe_hours=hours,
                )
                if n:
                    created += 1

        self.stdout.write(self.style.SUCCESS(
            f"notify_due_soon: {created} reminder(s) created across "
            f"{activities.count()} activity(ies) due in the next {hours}h."
        ))
