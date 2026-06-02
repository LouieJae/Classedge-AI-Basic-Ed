import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from activity.utils.authorization import check_subject_access
from rag_tutor.models import ChatMessage
from rag_tutor.query import ask_question
from subject.models.subject_model import Subject


@login_required
@require_POST
def ask(request, subject_id):
    subject = get_object_or_404(Subject, pk=subject_id)

    has_access, redirect_resp = check_subject_access(request, subject)
    if not has_access:
        return redirect_resp

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    question = body.get("question", "").strip()
    if not question:
        return JsonResponse({"error": "question is required"}, status=400)

    try:
        result = ask_question(subject_id, question, request.user)
    except Exception as exc:
        return JsonResponse({"error": str(exc)[:500]}, status=500)

    return JsonResponse(result)


@login_required
@require_GET
def history(request, subject_id):
    """Return the current student's prior Q&A for this subject, oldest first.
    Capped at the most recent 50 turns to keep the bubble payload small."""
    subject = get_object_or_404(Subject, pk=subject_id)
    has_access, redirect_resp = check_subject_access(request, subject)
    if not has_access:
        return redirect_resp

    qs = (
        ChatMessage.objects
        .filter(subject_id=subject_id, student=request.user)
        .order_by("-created_at")[:50]
    )
    messages = [
        {
            "question": m.question,
            "answer": m.answer,
            "sources": m.sources,
            "had_relevant_chunks": m.had_relevant_chunks,
            "created_at": m.created_at.isoformat(),
        }
        for m in reversed(list(qs))
    ]
    return JsonResponse({"messages": messages})
