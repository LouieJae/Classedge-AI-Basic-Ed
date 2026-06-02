# central_content/views/subjects.py
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render

from central_content.models import (
    AuditLogEntry,
    CentralActivity,
    CentralModule,
    CentralStaff,
    CentralSubject,
)
from central_content.permissions import central_role_required
from central_content.forms import CentralSubjectForm
from central_content import state_machine
from central_content.state_machine import IllegalTransition, UnresolvedChildren


_ALL_ROLES = (
    CentralStaff.Role.EDITOR,
    CentralStaff.Role.REVIEWER,
    CentralStaff.Role.PUBLISHER,
)


@central_role_required(*_ALL_ROLES)
def subject_list(request):
    qs = CentralSubject.objects.all().select_related("created_by")
    state = request.GET.get("state")
    if state in dict(CentralSubject.State.choices):
        qs = qs.filter(state=state)
    q = request.GET.get("q")
    if q:
        qs = qs.filter(subject_name__icontains=q)
    return render(
        request,
        "central_content/subjects/list.html",
        {"subjects": qs, "current_state": state, "q": q or ""},
    )


@central_role_required(*_ALL_ROLES)
def subject_detail(request, subject_id: int):
    subj = get_object_or_404(
        CentralSubject.objects.prefetch_related("modules", "activities", "textbooks"),
        pk=subject_id,
    )
    bindings = subj.school_bindings.select_related("target_school").all()
    return render(
        request,
        "central_content/subjects/detail.html",
        {
            "subject": subj,
            "modules": subj.modules.all(),
            "activities": subj.activities.all(),
            "textbooks": subj.textbooks.all(),
            "bindings": bindings,
        },
    )


@central_role_required(*_ALL_ROLES)
def subject_create(request):
    if request.method == "POST":
        form = CentralSubjectForm(request.POST)
        if form.is_valid():
            subj = form.save(commit=False)
            subj.created_by = request.user
            subj.save()
            return HttpResponseRedirect(f"/subjects/{subj.id}/")
    else:
        form = CentralSubjectForm()
    return render(
        request,
        "central_content/subjects/form.html",
        {"form": form, "subject": None},
    )


@central_role_required(*_ALL_ROLES)
def subject_edit(request, subject_id: int):
    subj = get_object_or_404(CentralSubject, pk=subject_id)
    if subj.state != CentralSubject.State.DRAFT:
        return HttpResponseBadRequest("Can only edit drafts")
    if request.method == "POST":
        form = CentralSubjectForm(request.POST, instance=subj)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(f"/subjects/{subj.id}/")
    else:
        form = CentralSubjectForm(instance=subj)
    return render(
        request,
        "central_content/subjects/form.html",
        {"form": form, "subject": subj},
    )


_REVIEW_ROLES = (CentralStaff.Role.REVIEWER, CentralStaff.Role.PUBLISHER)
_PUBLISHER_ONLY = (CentralStaff.Role.PUBLISHER,)


def _transition_response(request, subject_id, transition_fn, **kwargs):
    subj = get_object_or_404(CentralSubject, pk=subject_id)
    try:
        transition_fn(subj, actor=request.user, **kwargs)
    except (IllegalTransition, UnresolvedChildren) as exc:
        return HttpResponseBadRequest(str(exc))
    return HttpResponseRedirect(f"/subjects/{subj.id}/")


@central_role_required(*_ALL_ROLES)
def subject_submit(request, subject_id: int):
    return _transition_response(request, subject_id, state_machine.submit_for_review)


@central_role_required(*_REVIEW_ROLES)
def subject_approve(request, subject_id: int):
    return _transition_response(request, subject_id, state_machine.approve)


@central_role_required(*_REVIEW_ROLES)
def subject_request_changes(request, subject_id: int):
    notes = request.POST.get("notes", "")
    return _transition_response(
        request, subject_id, state_machine.request_changes, notes=notes,
    )


@central_role_required(*_PUBLISHER_ONLY)
def subject_reopen(request, subject_id: int):
    return _transition_response(request, subject_id, state_machine.reopen)


@central_role_required(*_ALL_ROLES)
def subject_history(request, subject_id: int):
    subj = get_object_or_404(CentralSubject, pk=subject_id)
    subj_ct = ContentType.objects.get_for_model(CentralSubject)
    mod_ct = ContentType.objects.get_for_model(CentralModule)
    act_ct = ContentType.objects.get_for_model(CentralActivity)

    module_ids = list(subj.modules.values_list("id", flat=True))
    activity_ids = list(subj.activities.values_list("id", flat=True))

    entries = AuditLogEntry.objects.filter(
        Q(content_type=subj_ct, object_id=subj.id)
        | Q(content_type=mod_ct, object_id__in=module_ids)
        | Q(content_type=act_ct, object_id__in=activity_ids)
    ).select_related("actor")

    return render(
        request, "central_content/subjects/history.html",
        {"subject": subj, "entries": entries},
    )
