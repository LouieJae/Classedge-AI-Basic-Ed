from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0004_alter_customuser_otp_created_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="legal_update_required",
            field=models.BooleanField(blank=True, default=True, null=True),
        ),
        migrations.CreateModel(
            name="LegalDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("doc_type", models.CharField(choices=[("EULA", "End User License Agreement"), ("PRIVACY", "Privacy Policy"), ("NDA", "Non-Disclosure Agreement")], max_length=10)),
                ("version", models.CharField(max_length=10)),
                ("title", models.CharField(max_length=255)),
                ("content", models.TextField()),
                ("is_active", models.BooleanField(default=False)),
                ("effective_date", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="authored_legal_documents", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Legal Document",
                "verbose_name_plural": "Legal Documents",
                "ordering": ["doc_type", "-effective_date"],
                "unique_together": {("doc_type", "version")},
            },
        ),
        migrations.AddField(
            model_name="userlegalconsent",
            name="document",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="acceptances",
                to="accounts.legaldocument",
            ),
        ),
        migrations.AddField(
            model_name="userlegalconsent",
            name="accepted_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="userlegalconsent",
            name="ip_address",
            field=models.GenericIPAddressField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="userlegalconsent",
            name="user_agent",
            field=models.TextField(null=True, blank=True),
        ),
    ]
