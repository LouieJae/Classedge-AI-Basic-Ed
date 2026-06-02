import secrets

from django.db import migrations, models

import gamification.models


def backfill_tokens(apps, schema_editor):
    """Give every existing StudentBadge a fresh unique share_token.

    Done in Python rather than via a column default because SQLite's
    AddField rebuild evaluates the default callable a single time and
    reuses that one value for every row, which violates UNIQUE.
    """
    StudentBadge = apps.get_model("gamification", "StudentBadge")
    used = set(
        StudentBadge.objects.exclude(share_token__isnull=True)
        .exclude(share_token="")
        .values_list("share_token", flat=True)
    )
    for sb in StudentBadge.objects.filter(
        models.Q(share_token__isnull=True) | models.Q(share_token="")
    ).only("pk"):
        token = secrets.token_urlsafe(16)
        while token in used:
            token = secrets.token_urlsafe(16)
        used.add(token)
        sb.share_token = token
        sb.save(update_fields=["share_token"])


def clear_tokens(apps, schema_editor):
    StudentBadge = apps.get_model("gamification", "StudentBadge")
    StudentBadge.objects.update(share_token=None)


class Migration(migrations.Migration):

    dependencies = [
        ("gamification", "0002_alter_xptransaction_source_id"),
    ]

    operations = [
        # Step 1 — add the column as plain nullable (no unique yet, no
        # default callable), so SQLite's table rebuild can populate every
        # row with NULL without conflicting on UNIQUE.
        migrations.AddField(
            model_name="studentbadge",
            name="share_token",
            field=models.CharField(
                blank=True,
                max_length=32,
                null=True,
            ),
        ),
        # Step 2 — backfill: one fresh token per existing row.
        migrations.RunPython(backfill_tokens, clear_tokens),
        # Step 3 — bring the column to its final shape with unique=True
        # and the per-instance default that the model declares.
        migrations.AlterField(
            model_name="studentbadge",
            name="share_token",
            field=models.CharField(
                blank=True,
                default=gamification.models._generate_share_token,
                max_length=32,
                null=True,
                unique=True,
            ),
        ),
    ]
