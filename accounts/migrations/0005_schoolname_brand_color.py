# Generated for the per-tenant theme customizer (Classedge LMS).

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_alter_customuser_otp_created_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="schoolname",
            name="brand_color",
            field=models.CharField(
                default="#1b4332",
                max_length=7,
                help_text="Hex code (#RRGGBB). Drives the brand-primary token across every page.",
                validators=[
                    django.core.validators.RegexValidator(
                        r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$",
                        "Enter a valid hex color (#RRGGBB or #RGB).",
                    )
                ],
            ),
        ),
    ]
