# central_content/views/modules.py
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render

from central_content import state_machine
from central_content.forms import CentralModuleForm
from central_content.models import CentralModule, CentralStaff, CentralSubject
from central_content.permissions import central_role_required
from central_content.state_machine import IllegalTransition


_ALL = (CentralStaff.Role.EDITOR, CentralStaff.Role.REVIEWER, CentralStaff.Role.PUBLISHER)
_REVIEW = (CentralStaff.Role.REVIEWER, CentralStaff.Role.PUBLISHER)


def _get_subject(subject_id):
    return get_object_or_404(CentralSubject, pk=subject_id)


def _get_module(subject_id, module_id):
    return get_object_or_404(
        CentralModule, pk=module_id, central_subject_id=subject_id,
    )


@central_role_required(*_ALL)
def module_create(request, subject_id: int):
    subject = _get_subject(subject_id)
    if request.method == "POST":
        form = CentralModuleForm(request.POST, request.FILES)
        if form.is_valid():
            m = form.save(commit=False)
            m.central_subject = subject
            m.created_by = request.user
            m.save()
            return HttpResponseRedirect(f"/subjects/{subject.id}/")
    else:
        form = CentralModuleForm()
    return render(
        request, "central_content/modules/form.html",
        {"form": form, "subject": subject, "module": None},
    )


@central_role_required(*_ALL)
def module_detail(request, subject_id: int, module_id: int):
    subject = _get_subject(subject_id)
    module = _get_module(subject_id, module_id)
    return render(
        request, "central_content/modules/detail.html",
        {"subject": subject, "module": module},
    )


@central_role_required(*_ALL)
def module_edit(request, subject_id: int, module_id: int):
    subject = _get_subject(subject_id)
    module = _get_module(subject_id, module_id)
    if module.state != CentralModule.State.DRAFT:
        return HttpResponseBadRequest("Can only edit drafts")
    if request.method == "POST":
        form = CentralModuleForm(request.POST, request.FILES, instance=module)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(
                f"/subjects/{subject.id}/modules/{module.id}/"
            )
    else:
        form = CentralModuleForm(instance=module)
    return render(
        request, "central_content/modules/form.html",
        {"form": form, "subject": subject, "module": module},
    )


def _module_transition(request, subject_id, module_id, fn, **kwargs):
    module = _get_module(subject_id, module_id)
    try:
        fn(module, actor=request.user, **kwargs)
    except IllegalTransition as exc:
        return HttpResponseBadRequest(str(exc))
    return HttpResponseRedirect(f"/subjects/{subject_id}/modules/{module.id}/")


@central_role_required(*_ALL)
def module_submit(request, subject_id: int, module_id: int):
    return _module_transition(request, subject_id, module_id, state_machine.submit_for_review)


@central_role_required(*_REVIEW)
def module_approve(request, subject_id: int, module_id: int):
    return _module_transition(request, subject_id, module_id, state_machine.approve)


@central_role_required(*_REVIEW)
def module_request_changes(request, subject_id: int, module_id: int):
    notes = request.POST.get("notes", "")
    return _module_transition(
        request, subject_id, module_id,
        state_machine.request_changes, notes=notes,
    )
