"""Sync Django state with the cross-app FK type change done in activity/0007.

The DDL for mobile_attachment.record_details_id (bigint -> varchar(36)) is
performed inside activity/0007_swap_retake_pk.py in a single transaction with
the parent PK swap, mirroring the LMS source-of-truth. This migration carries
only the matching Django state mutation so the autodetector stops flagging
drift on mobile.Attachment.record_details.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mobile', '0002_attachment_activity_question_and_more'),
        ('activity', '0007_swap_retake_pk'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='attachment',
                    name='record_details',
                    field=models.ForeignKey(
                        on_delete=models.deletion.PROTECT,
                        related_name='attachments',
                        null=True, blank=True,
                        to='activity.retakerecorddetail',
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
