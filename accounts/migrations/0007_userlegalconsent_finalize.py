from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_userlegalconsent_data_migration"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="userlegalconsent",
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name="userlegalconsent",
            name="eula_version",
        ),
        migrations.RemoveField(
            model_name="userlegalconsent",
            name="privacy_policy_version",
        ),
        migrations.RemoveField(
            model_name="userlegalconsent",
            name="is_accepted",
        ),
        migrations.RemoveField(
            model_name="userlegalconsent",
            name="consent_timestamp",
        ),
        migrations.AlterField(
            model_name="userlegalconsent",
            name="document",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="acceptances",
                to="accounts.legaldocument",
            ),
        ),
        migrations.AlterField(
            model_name="userlegalconsent",
            name="accepted_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterUniqueTogether(
            name="userlegalconsent",
            unique_together={("user", "document")},
        ),
        migrations.AddIndex(
            model_name="userlegalconsent",
            index=models.Index(fields=["user", "document"], name="ulc_user_doc_idx"),
        ),
        migrations.AlterModelOptions(
            name="userlegalconsent",
            options={
                "verbose_name": "User Legal Consent",
                "verbose_name_plural": "User Legal Consents",
            },
        ),
    ]
