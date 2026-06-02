from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from gamification.quest_autograde import grade
from gamification.quest_models import Quest, QuestAttempt


@login_required
def quest_play(request, module_id):
    quests = Quest.objects.filter(module_id=module_id, status="published").order_by("order")
    attempted = set(QuestAttempt.objects.filter(
        quest__in=quests, student=request.user, is_correct=True
    ).values_list("quest_id", flat=True))
    next_q = next((q for q in quests if q.id not in attempted), None)
    return render(request, "student/quests/play.html", {
        "quest": next_q, "module_id": module_id,
        "remaining": quests.count() - len(attempted),
    })


@login_required
@require_POST
def quest_play_submit(request, quest_id):
    quest = get_object_or_404(Quest, pk=quest_id, status="published")
    answer = request.POST.get("answer", "")
    ok, score = grade(quest, answer)
    QuestAttempt.objects.update_or_create(
        quest=quest, student=request.user,
        defaults={"submitted_answer": {"raw": answer}, "is_correct": ok, "score": score},
    )
    return redirect("quest_play", module_id=quest.module_id)
