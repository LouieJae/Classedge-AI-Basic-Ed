from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("migration", "0003_migrationsettings"),
    ]

    operations = [
        migrations.AddField(
            model_name="migrationjob",
            name="current_task_id",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
    ]
