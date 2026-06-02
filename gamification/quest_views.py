"""[Classedge LMS] Teacher views for quest authoring (AI / manual / upload)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from module.models.module import Module
from gamification.quest_generation import start_generation
from gamification.quest_import import import_quests, ImportError as QuestImportError
from gamification.quest_models import Quest, QuestGenerationJob
from gamification.quest_settings_models import OrganizationQuestSettings


def _settings():
    return OrganizationQuestSettings.load()


@login_required
def quest_mode_select(request, module_id):
    module = get_object_or_404(Module, pk=module_id)
    s = _settings()
    existing = Quest.objects.filter(module=module).exists()
    return render(request, "teacher/quests/mode_select.html", {
        "module": module, "settings": s, "has_quests": existing,
    })


@login_required
@require_POST
def quest_generate(request, module_id):
    if not _settings().ai_mode_enabled:
        return HttpResponseForbidden("AI mode is disabled by the administrator.")
    module = get_object_or_404(Module, pk=module_id)
    try:
        job = start_generation(module)
    except RuntimeError as e:
        messages.error(request, str(e))
        return redirect("quest_mode_select", module_id=module.id)
    return redirect("quest_review", module_id=module.id)


@login_required
def quest_job_status(request, job_id):
    job = get_object_or_404(QuestGenerationJob, pk=job_id)
    return JsonResponse({"status": job.status, "error": job.error})


@login_required
@require_POST
def quest_manual_init(request, module_id):
    if not _settings().manual_mode_enabled:
        return HttpResponseForbidden("Manual mode is disabled.")
    module = get_object_or_404(Module, pk=module_id)
    return redirect("quest_review", module_id=module.id)


@login_required
def quest_upload(request, module_id):
    if not _settings().upload_mode_enabled:
        return HttpResponseForbidden("Upload mode is disabled.")
    module = get_object_or_404(Module, pk=module_id)
    if request.method == "POST" and request.FILES.get("file"):
        try:
            n = import_quests(module, request.FILES["file"])
        except QuestImportError as e:
            messages.error(request, str(e))
        else:
            messages.success(request, f"Imported {n} quests as drafts.")
            return redirect("quest_review", module_id=module.id)
    return render(request, "teacher/quests/upload.html", {"module": module})


@login_required
def quest_review(request, module_id):
    module = get_object_or_404(Module, pk=module_id)
    drafts = Quest.objects.filter(module=module, status="draft").order_by("order")
    published = Quest.objects.filter(module=module, status="published").order_by("order")
    return render(request, "teacher/quests/review.html", {
        "module": module, "drafts": drafts, "published": published,
    })


@login_required
@require_POST
def quest_publish_all(request, module_id):
    module = get_object_or_404(Module, pk=module_id)
    Quest.objects.filter(module=module, status="draft").update(status="published")
    messages.success(request, "Drafts published.")
    return redirect("quest_review", module_id=module.id)


@login_required
@require_POST
def quest_toggle_grade(request, quest_id):
    q = get_object_or_404(Quest, pk=quest_id)
    q.counts_toward_grade = not q.counts_toward_grade
    q.save(update_fields=["counts_toward_grade"])
    return redirect("quest_review", module_id=q.module_id)


@login_required
@require_POST
def quest_delete(request, quest_id):
    q = get_object_or_404(Quest, pk=quest_id)
    mid = q.module_id
    q.delete()
    return redirect("quest_review", module_id=mid)
