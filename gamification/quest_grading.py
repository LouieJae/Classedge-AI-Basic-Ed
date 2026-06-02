"""[Classedge LMS] Compute student quest score (0..100 float, 2dp) for gradebook."""
from gamification.quest_models import Quest, QuestAttempt


def get_student_quest_score(student, subject, term) -> float:
    quests = Quest.objects.filter(
        module__subject=subject,
        module__term=term,
        status="published",
        counts_toward_grade=True,
    )
    total_quests = quests.count()
    if total_quests == 0:
        return 0.0
    attempts = {
        a.quest_id: a
        for a in QuestAttempt.objects.filter(quest__in=quests, student=student)
    }
    total = 0.0
    for q in quests:
        a = attempts.get(q.id)
        total += (a.score * 100.0) if a else 0.0
    return round(total / total_quests, 2)
