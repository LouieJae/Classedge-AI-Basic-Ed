import sys

import cuid
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from activity.models import RetakeRecord, RetakeRecordDetail


class Command(BaseCommand):
    help = "Backfill RetakeRecord / RetakeRecordDetail rows with NULL or empty local_id."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--check",
            action="store_true",
            help="Exit 0 if zero gaps, 1 otherwise.",
        )

    def handle(self, *args, **opts):
        gap = Q(local_id__isnull=True) | Q(local_id="")
        rr_gaps = RetakeRecord.objects.filter(gap)
        d_gaps = RetakeRecordDetail.objects.filter(gap)
        rr_n, d_n = rr_gaps.count(), d_gaps.count()
        self.stdout.write(
            f"RetakeRecord gaps: {rr_n}; RetakeRecordDetail gaps: {d_n}"
        )

        if opts["check"]:
            sys.exit(0 if (rr_n == 0 and d_n == 0) else 1)
        if opts["dry_run"]:
            return

        with transaction.atomic():
            for rr in rr_gaps.only("pk"):
                RetakeRecord.objects.filter(pk=rr.pk).update(local_id=cuid.cuid())
            for d in d_gaps.only("pk"):
                RetakeRecordDetail.objects.filter(pk=d.pk).update(local_id=cuid.cuid())

        assert (
            RetakeRecord.objects.values("local_id").distinct().count()
            == RetakeRecord.objects.count()
        )
        assert (
            RetakeRecordDetail.objects.values("local_id").distinct().count()
            == RetakeRecordDetail.objects.count()
        )
