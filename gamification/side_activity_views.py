import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from activity.utils.authorization import check_subject_access
from gamification.models import SideActivity, SideActivityAttempt
from gamification.scoring import score_activity
from gamification.services import award_xp
from gamification.coding_stats_service import update_coding_stats_kata

FORM_TYPES = {
    "daily_challenge",
    "practice_quiz",
    "fill_blank",
    "word_scramble",
    "equation_balance",
    "reading_mini",
}

JS_TYPES = {
    "flashcard",
    "speed_round",
    "match_pair",
    "drag_order",
    "timeline_sort",
    "math_drill",
    "geo_map",
    "code_kata",
    "typing_drill",
}


@login_required
def side_activity_list(request, subject_id):
    from subject.models.subject_model import Subject

    subject = get_object_or_404(Subject, pk=subject_id)
    activities = SideActivity.objects.filter(subject=subject, is_active=True).order_by("-created_at")

    completed_ids = set(
        SideActivityAttempt.objects.filter(
            student=request.user,
            side_activity__in=activities,
            completed_at__isnull=False,
        ).values_list("side_activity_id", flat=True)
    )

    activity_list = []
    for a in activities:
        activity_list.append({
            "activity": a,
            "completed": a.pk in completed_ids,
        })

    return render(request, "student/gamification/side_activity_list.html", {
        "subject": subject,
        "activity_list": activity_list,
    })


@login_required
def side_activity_play(request, activity_id):
    activity = get_object_or_404(SideActivity, pk=activity_id, is_active=True)
    is_js_type = activity.sub_type in JS_TYPES
    type_template = f"gamification/types/_{activity.sub_type}.html"

    if request.method == "POST" and activity.sub_type in FORM_TYPES:
        submitted_data = _build_submitted_data(request.POST, activity.sub_type)
        score = score_activity(activity.sub_type, activity.content_json, submitted_data)
        xp = activity.xp_reward if score >= 0.5 else activity.xp_reward // 2

        first_completion = not SideActivityAttempt.objects.filter(
            student=request.user,
            side_activity=activity,
            completed_at__isnull=False,
        ).exists()

        SideActivityAttempt.objects.create(
            student=request.user,
            side_activity=activity,
            completed_at=timezone.now(),
            score=score,
            xp_awarded=xp if first_completion else 0,
            details_json=submitted_data,
        )

        if first_completion:
            award_xp(
                request.user, xp,
                reason=f"Side activity: {activity.title}",
                source_type="side_activity",
                source_id=activity.pk,
            )

        # Update coding stats for code_kata type
        if activity.sub_type == "code_kata":
            update_coding_stats_kata(request.user, SideActivityAttempt.objects.filter(
                student=request.user, side_activity=activity,
            ).order_by("-started_at").first())

        return render(request, "student/gamification/side_activity_result.html", {
            "activity": activity,
            "score": score,
            "score_pct": int(score * 100),
            "xp_awarded": xp if first_completion else 0,
            "first_completion": first_completion,
        })

    content_js = (
        json.dumps(activity.content_json or {})
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )

    return render(request, "student/gamification/side_activity_play.html", {
        "activity": activity,
        "content": activity.content_json,
        "content_js": content_js,
        "type_template": type_template,
        "is_js_type": is_js_type,
    })


@require_POST
@login_required
def side_activity_submit(request, activity_id):
    activity = get_object_or_404(SideActivity, pk=activity_id, is_active=True)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    score = min(1.0, max(0.0, float(body.get("score", 0))))
    time_taken = body.get("time_taken_seconds")
    details = body.get("details", {})

    xp = activity.xp_reward if score >= 0.5 else activity.xp_reward // 2

    first_completion = not SideActivityAttempt.objects.filter(
        student=request.user,
        side_activity=activity,
        completed_at__isnull=False,
    ).exists()

    SideActivityAttempt.objects.create(
        student=request.user,
        side_activity=activity,
        completed_at=timezone.now(),
        score=score,
        time_taken_seconds=time_taken,
        xp_awarded=xp if first_completion else 0,
        details_json=details,
    )

    if first_completion:
        award_xp(
            request.user, xp,
            reason=f"Side activity: {activity.title}",
            source_type="side_activity",
            source_id=activity.pk,
        )

    # Update coding stats for code_kata type
    if activity.sub_type == "code_kata":
        attempt = SideActivityAttempt.objects.filter(
            student=request.user, side_activity=activity,
        ).order_by("-started_at").first()
        if attempt:
            update_coding_stats_kata(request.user, attempt)

    return JsonResponse({
        "score": score,
        "score_pct": int(score * 100),
        "xp_awarded": xp if first_completion else 0,
        "first_completion": first_completion,
    })


def _build_submitted_data(post, sub_type):
    """Extract submitted answers from POST data based on activity type."""
    if sub_type == "daily_challenge":
        return {"answer": post.get("answer", "")}

    if sub_type == "equation_balance":
        coeffs = []
        i = 0
        while f"coeff_{i}" in post:
            coeffs.append(post[f"coeff_{i}"])
            i += 1
        return {"coefficients": coeffs}

    # Multi-answer types: practice_quiz, fill_blank, word_scramble, reading_mini
    answers = []
    i = 0
    while f"answer_{i}" in post:
        answers.append(post[f"answer_{i}"])
        i += 1
    return {"answers": answers}


# ---------------------------------------------------------------------------
# Teacher CRUD
# ---------------------------------------------------------------------------

@login_required
def side_activity_create(request, subject_id):
    from subject.models.subject_model import Subject

    from gamification.side_activity_forms import SideActivityForm

    subject = get_object_or_404(Subject, pk=subject_id)
    has_access, resp = check_subject_access(request, subject, require_teacher=True)
    if not has_access:
        return resp

    if request.method == "POST":
        form = SideActivityForm(request.POST)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.subject = subject
            activity.created_by = request.user
            activity.save()
            return redirect("side_activity_list", subject_id=subject.pk)
    else:
        form = SideActivityForm()

    return render(request, "teacher/gamification/side_activity_create.html", {
        "form": form,
        "subject": subject,
    })


@login_required
def side_activity_edit(request, activity_id):
    from gamification.side_activity_forms import SideActivityForm

    sa = get_object_or_404(SideActivity, pk=activity_id)
    has_access, resp = check_subject_access(request, sa.subject, require_teacher=True)
    if not has_access:
        return resp

    if request.method == "POST":
        form = SideActivityForm(request.POST, instance=sa)
        if form.is_valid():
            form.save()
            return redirect("side_activity_list", subject_id=sa.subject_id)
    else:
        form = SideActivityForm(instance=sa, initial={
            "content_text": json.dumps(sa.content_json, indent=2),
        })

    return render(request, "teacher/gamification/side_activity_edit.html", {
        "form": form,
        "activity": sa,
        "subject": sa.subject,
    })


@require_POST
@login_required
def side_activity_delete(request, activity_id):
    sa = get_object_or_404(SideActivity, pk=activity_id)
    has_access, resp = check_subject_access(request, sa.subject, require_teacher=True)
    if not has_access:
        return resp

    subject_id = sa.subject_id
    sa.delete()
    return redirect("side_activity_list", subject_id=subject_id)
