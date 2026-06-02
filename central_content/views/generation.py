from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from central_content.models import ContentGenerationJob, CurriculumPlan
from central_content.content_tasks import run_content_generation
from central_content.permissions import central_role_required


@central_role_required("publisher")
@require_POST
def trigger_generation(request, subject_id, textbook_id, plan_id):
    plan = get_object_or_404(
        CurriculumPlan.objects.select_related("textbook"),
        pk=plan_id,
        textbook_id=textbook_id,
        textbook__central_subject_id=subject_id,
    )
    if plan.status != CurriculumPlan.Status.APPROVED:
        return HttpResponseBadRequest("Only approved plans can generate content.")

    model_key = request.POST.get(
        "model_key", settings.CURRICULUM_PLANNER_DEFAULT_MODEL,
    )

    job = ContentGenerationJob.objects.create(
        curriculum_plan=plan,
        model_key=model_key,
        total_weeks=len(plan.plan_data),
        week_results=[
            {"week": entry["week"], "status": "pending"}
            for entry in plan.plan_data
        ],
        triggered_by=request.user,
    )

    run_content_generation.delay(job.pk)

    return HttpResponseRedirect(
        f"/subjects/{subject_id}/textbooks/{textbook_id}/plans/{plan_id}/jobs/{job.pk}/"
    )


@central_role_required("publisher", "reviewer", "editor")
def job_status(request, subject_id, textbook_id, plan_id, job_id):
    job = get_object_or_404(
        ContentGenerationJob.objects.select_related(
            "curriculum_plan__textbook__central_subject",
            "triggered_by",
        ),
        pk=job_id,
        curriculum_plan_id=plan_id,
        curriculum_plan__textbook_id=textbook_id,
        curriculum_plan__textbook__central_subject_id=subject_id,
    )
    return render(
        request,
        "central_content/generation/status.html",
        {
            "job": job,
            "plan": job.curriculum_plan,
            "textbook": job.curriculum_plan.textbook,
            "subject": job.curriculum_plan.textbook.central_subject,
        },
    )


@central_role_required("publisher", "reviewer", "editor")
def job_status_badge(request, subject_id, textbook_id, plan_id, job_id):
    job = get_object_or_404(
        ContentGenerationJob,
        pk=job_id,
        curriculum_plan_id=plan_id,
    )
    return render(
        request,
        "central_content/generation/status_badge.html",
        {"job": job},
    )
