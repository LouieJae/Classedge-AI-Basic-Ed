from django.db import migrations


def relabel_forward(apps, schema_editor):
    QuizType = apps.get_model("activity", "QuizType")
    ActivityType = apps.get_model("activity", "ActivityType")
    QuizType.objects.filter(name="Participation").update(display_name="Major Assessment")
    ActivityType.objects.filter(name="Participation").update(display_name="Major Assessment")


def relabel_backward(apps, schema_editor):
    QuizType = apps.get_model("activity", "QuizType")
    ActivityType = apps.get_model("activity", "ActivityType")
    QuizType.objects.filter(name="Participation").update(display_name=None)
    ActivityType.objects.filter(name="Participation").update(display_name=None)


class Migration(migrations.Migration):

    dependencies = [
        ("activity", "0003_activitytype_display_name_quiztype_display_name"),
    ]

    operations = [
        migrations.RunPython(relabel_forward, relabel_backward),
    ]
