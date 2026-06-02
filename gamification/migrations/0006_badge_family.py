from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gamification", "0005_quest_questattempt_questgenerationjob"),
    ]

    operations = [
        migrations.AddField(
            model_name="badgedefinition",
            name="family",
            field=models.CharField(blank=True, db_index=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="badgedefinition",
            name="family_rank",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="teacherbadgedefinition",
            name="family",
            field=models.CharField(blank=True, db_index=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="teacherbadgedefinition",
            name="family_rank",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
