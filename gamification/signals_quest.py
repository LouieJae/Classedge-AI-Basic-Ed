"""[Classedge LMS] Recompute StudentProgress.completed when quest attempts change."""
from django.db.models.signals import post_save
from django.dispatch import receiver
from gamification.quest_models import Quest, QuestAttempt
from module.models.student_progress import StudentProgress


@receiver(post_save, sender=QuestAttempt)
def recompute_module_progress(sender, instance, **kwargs):
    module = instance.quest.module
    student = instance.student
    published = Quest.objects.filter(module=module, status="published")
    if not published.exists():
        return
    correct_ids = set(QuestAttempt.objects.filter(
        quest__in=published, student=student, is_correct=True
    ).values_list("quest_id", flat=True))
    all_done = set(published.values_list("id", flat=True)) == correct_ids
    sp, _ = StudentProgress.objects.get_or_create(student=student, module=module)
    if sp.completed != all_done:
        sp.completed = all_done
        sp.save(update_fields=["completed"])
