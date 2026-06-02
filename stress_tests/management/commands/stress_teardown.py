"""Delete all data tagged by ``stress_seed``.

Dry-run by default. Pass ``--yes`` to actually delete.

Tagging convention enforced:
  * Users: email ends with ``@stresstest.local``
  * Named objects: name starts with ``[STRESS]``

NEVER touches a user/object that lacks the marker.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from ._stress_common import STRESS_EMAIL_DOMAIN, STRESS_NAME_PREFIX


class Command(BaseCommand):
    help = "Delete tagged stress test data. Dry-run unless --yes is passed."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Actually delete. Without this, prints counts only.",
        )

    def handle(self, *args, **opts):
        from accounts.models import CustomUser, LoginHistory, Profile
        from activity.models import Activity, ActivityQuestion, QuestionChoice
        from course.models import SubjectEnrollment
        from gamification.models import (
            BadgeDefinition,
            StudentBadge,
            StudentGamification,
            XPTransaction,
        )
        from module.models import Module
        from roles.models import Role
        from subject.models import Subject

        commit = opts["yes"]
        email_suffix = f"@{STRESS_EMAIL_DOMAIN}"

        stress_users_qs = CustomUser.objects.filter(email__endswith=email_suffix)
        stress_user_ids = list(stress_users_qs.values_list("id", flat=True))

        # Ordered by FK dependency (children first).
        plan = [
            ("XPTransaction", XPTransaction.objects.filter(student_id__in=stress_user_ids)),
            ("StudentBadge", StudentBadge.objects.filter(student_id__in=stress_user_ids)),
            ("StudentGamification", StudentGamification.objects.filter(student_id__in=stress_user_ids)),
            ("BadgeDefinition (tagged)", BadgeDefinition.objects.filter(name__startswith=STRESS_NAME_PREFIX)),
            ("LoginHistory", LoginHistory.objects.filter(user_id__in=stress_user_ids)),
            ("QuestionChoice (via tagged activity)",
                QuestionChoice.objects.filter(question__activity__activity_name__startswith=STRESS_NAME_PREFIX)),
            ("ActivityQuestion (via tagged activity)",
                ActivityQuestion.objects.filter(activity__activity_name__startswith=STRESS_NAME_PREFIX)),
            ("Activity ([STRESS])", Activity.objects.filter(activity_name__startswith=STRESS_NAME_PREFIX)),
            ("SubjectEnrollment (stress user OR tagged subject)",
                SubjectEnrollment.objects.filter(student_id__in=stress_user_ids)
                | SubjectEnrollment.objects.filter(subject__subject_name__startswith=STRESS_NAME_PREFIX)),
            ("Module ([STRESS])", Module.objects.filter(file_name__startswith=STRESS_NAME_PREFIX)),
            ("Subject ([STRESS])", Subject.objects.filter(subject_name__startswith=STRESS_NAME_PREFIX)),
            ("Profile (stress users)", Profile.objects.filter(user_id__in=stress_user_ids)),
            ("CustomUser (@stresstest.local)", stress_users_qs),
            ("Role ([STRESS])", Role.objects.filter(name__startswith=STRESS_NAME_PREFIX)),
        ]

        self.stdout.write(self.style.NOTICE("== stress_teardown plan =="))
        counts = []
        for label, qs in plan:
            try:
                c = qs.count()
            except Exception as exc:  # pragma: no cover — defensive
                c = -1
                self.stdout.write(self.style.ERROR(f"  {label}: count failed: {exc}"))
            counts.append((label, c))
            self.stdout.write(f"  {label}: {c}")

        if not commit:
            self.stdout.write(self.style.WARNING("DRY RUN — pass --yes to delete."))
            return

        self.stdout.write(self.style.NOTICE("== deleting =="))
        deleted_summary = []
        with transaction.atomic():
            for label, qs in plan:
                # Re-evaluate (some QuerySets had OR composition; that's fine here).
                try:
                    deleted, _by_model = qs.delete()
                except Exception as exc:
                    self.stdout.write(self.style.ERROR(f"  {label}: delete failed: {exc}"))
                    raise
                deleted_summary.append((label, deleted))
                self.stdout.write(f"  {label}: deleted {deleted}")
        self.stdout.write(self.style.SUCCESS("== stress_teardown done =="))
