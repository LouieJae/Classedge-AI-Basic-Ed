from django.db import migrations


def seed_badge_catalog(apps, schema_editor):
    from gamification.badge_catalog import seed_catalog

    seed_catalog(apps.get_model)


def unseed_badge_catalog(apps, schema_editor):
    from gamification.badge_catalog import all_codes

    BadgeDefinition = apps.get_model("gamification", "BadgeDefinition")
    TeacherBadgeDefinition = apps.get_model("gamification", "TeacherBadgeDefinition")
    codes = all_codes()
    BadgeDefinition.objects.filter(code__in=codes["student"] + codes["staff"]).delete()
    TeacherBadgeDefinition.objects.filter(code__in=codes["teacher"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("gamification", "0006_badge_family"),
    ]

    operations = [
        migrations.RunPython(seed_badge_catalog, reverse_code=unseed_badge_catalog),
    ]
