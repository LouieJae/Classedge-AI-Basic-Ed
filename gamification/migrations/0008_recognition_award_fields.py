from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gamification', '0007_seed_badge_catalog'),
    ]

    operations = [
        migrations.AddField(
            model_name='teacherrecognition',
            name='award_type',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
        migrations.AddField(
            model_name='teacherrecognition',
            name='icon',
            field=models.CharField(blank=True, default='', max_length=80),
        ),
    ]
