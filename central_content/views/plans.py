import json

from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods, require_POST

from central_content.models import (
    CentralSubject, CurriculumPlan, ParsedTextbook, SchoolSubjectBinding,
)
from central_content.permissions import central_role_required
from central_content.tasks import generate_curriculum_plan, bulk_generate_plans


@central_role_required("publisher")
def plan_generate(request, subject_id, textbook_id):
    textbook = get_object_or_404(
        ParsedTextbook.objects.select_related("central_subject"),
        pk=textbook_id,
        central_subject_id=subject_id,
    )
    subject = textbook.central_subject
    bindings = SchoolSubjectBinding.objects.filter(
        central_subject=subject,
    ).select_related("target_school")
    model_keys = list(settings.CURRICULUM_PLANNER_MODELS.keys())

    if request.method == "POST":
        binding_id = request.POST.get("binding_id")
        model_key = request.POST.get("model_key", settings.CURRICULUM_PLANNER_DEFAULT_MODEL)
        if not binding_id:
            return HttpResponseBadRequest("binding_id is required")
        generate_curriculum_plan.delay(
            textbook.pk, int(binding_id), model_key, request.user.pk,
        )
        return HttpResponseRedirect(
            f"/subjects/{subject_id}/textbooks/{textbook_id}/"
        )

    return render(
        request,
        "central_content/plans/generate.html",
        {
            "subject": subject,
            "textbook": textbook,
            "bindings": bindings,
            "model_keys": model_keys,
        },
    )


@central_role_required("publisher", "reviewer", "editor")
def plan_detail(request, subject_id, textbook_id, plan_id):
    plan = get_object_or_404(
        CurriculumPlan.objects.select_related("textbook", "generated_by"),
        pk=plan_id,
        textbook_id=textbook_id,
        textbook__central_subject_id=subject_id,
    )
    chapters = {
        ch.chapter_number: ch.title
        for ch in plan.textbook.chapters.all()
    }
    for week in plan.plan_data:
        week["chapter_titles"] = [
            chapters.get(num, f"Chapter {num}") for num in week["chapters"]
        ]

    generation_jobs = plan.generation_jobs.select_related("triggered_by").all()
    model_keys = list(settings.CURRICULUM_PLANNER_MODELS.keys())

    return render(
        request,
        "central_content/plans/detail.html",
        {
            "subject": plan.textbook.central_subject,
            "textbook": plan.textbook,
            "plan": plan,
            "generation_jobs": generation_jobs,
            "model_keys": model_keys,
        },
    )


@central_role_required("publisher", "reviewer")
@require_POST
def plan_edit(request, subject_id, textbook_id, plan_id):
    plan = get_object_or_404(
        CurriculumPlan,
        pk=plan_id,
        textbook_id=textbook_id,
        textbook__central_subject_id=subject_id,
    )
    if plan.status != CurriculumPlan.Status.DRAFT:
        return HttpResponseBadRequest("Only draft plans can be edited.")

    try:
        new_data = json.loads(request.POST.get("plan_data", "[]"))
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON.")

    plan.plan_data = new_data
    try:
        plan._validate_plan_data()
    except Exception as exc:
        return HttpResponseBadRequest(str(exc))

    plan.save(update_fields=["plan_data", "updated_at"])
    return HttpResponseRedirect(
        f"/subjects/{subject_id}/textbooks/{textbook_id}/plans/{plan_id}/"
    )


@central_role_required("publisher", "reviewer")
@require_POST
def plan_approve(request, subject_id, textbook_id, plan_id):
    plan = get_object_or_404(
        CurriculumPlan,
        pk=plan_id,
        textbook_id=textbook_id,
        textbook__central_subject_id=subject_id,
    )
    if plan.status != CurriculumPlan.Status.DRAFT:
        return HttpResponseBadRequest("Only draft plans can be approved.")
    plan.status = CurriculumPlan.Status.APPROVED
    plan.save(update_fields=["status", "updated_at"])
    return HttpResponseRedirect(
        f"/subjects/{subject_id}/textbooks/{textbook_id}/plans/{plan_id}/"
    )


@central_role_required("publisher", "reviewer")
@require_POST
def plan_reject(request, subject_id, textbook_id, plan_id):
    plan = get_object_or_404(
        CurriculumPlan,
        pk=plan_id,
        textbook_id=textbook_id,
        textbook__central_subject_id=subject_id,
    )
    if plan.status != CurriculumPlan.Status.DRAFT:
        return HttpResponseBadRequest("Only draft plans can be rejected.")
    plan.status = CurriculumPlan.Status.REJECTED
    plan.save(update_fields=["status", "updated_at"])
    return HttpResponseRedirect(
        f"/subjects/{subject_id}/textbooks/{textbook_id}/plans/{plan_id}/"
    )


@central_role_required("publisher")
@require_POST
def bulk_generate(request, subject_id):
    subject = get_object_or_404(CentralSubject, pk=subject_id)
    binding_id = request.POST.get("binding_id")
    model_key = request.POST.get("model_key", settings.CURRICULUM_PLANNER_DEFAULT_MODEL)
    if not binding_id:
        return HttpResponseBadRequest("binding_id is required")
    bulk_generate_plans.delay(
        subject.pk, int(binding_id), model_key, request.user.pk,
    )
    return HttpResponseRedirect(f"/subjects/{subject_id}/")
