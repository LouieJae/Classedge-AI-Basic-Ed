from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_alter_profile_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='share_token',
            field=models.CharField(blank=True, db_index=True, default='', max_length=43),
        ),
        migrations.AddField(
            model_name='profile',
            name='share_enabled',
            field=models.BooleanField(default=False),
        ),
    ]
