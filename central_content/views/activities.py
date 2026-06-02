# central_content/views/activities.py
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render

from central_content import state_machine
from central_content.forms import CentralActivityForm
from central_content.models import CentralActivity, CentralStaff, CentralSubject
from central_content.permissions import central_role_required
from central_content.state_machine import IllegalTransition


_ALL = (CentralStaff.Role.EDITOR, CentralStaff.Role.REVIEWER, CentralStaff.Role.PUBLISHER)
_REVIEW = (CentralStaff.Role.REVIEWER, CentralStaff.Role.PUBLISHER)


def _get_subject(sid):
    return get_object_or_404(CentralSubject, pk=sid)


def _get_activity(sid, aid):
    return get_object_or_404(
        CentralActivity, pk=aid, central_subject_id=sid,
    )


@central_role_required(*_ALL)
def activity_create(request, subject_id: int):
    subject = _get_subject(subject_id)
    if request.method == "POST":
        form = CentralActivityForm(request.POST)
        if form.is_valid():
            act = form.save(commit=False)
            act.central_subject = subject
            act.created_by = request.user
            act.save()
            return HttpResponseRedirect(f"/subjects/{subject.id}/")
    else:
        form = CentralActivityForm()
    return render(
        request, "central_content/activities/form.html",
        {"form": form, "subject": subject, "activity": None},
    )


@central_role_required(*_ALL)
def activity_detail(request, subject_id: int, activity_id: int):
    subject = _get_subject(subject_id)
    activity = _get_activity(subject_id, activity_id)
    return render(
        request, "central_content/activities/detail.html",
        {"subject": subject, "activity": activity},
    )


@central_role_required(*_ALL)
def activity_edit(request, subject_id: int, activity_id: int):
    subject = _get_subject(subject_id)
    activity = _get_activity(subject_id, activity_id)
    if activity.state != CentralActivity.State.DRAFT:
        return HttpResponseBadRequest("Can only edit drafts")
    if request.method == "POST":
        form = CentralActivityForm(request.POST, instance=activity)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(
                f"/subjects/{subject.id}/activities/{activity.id}/"
            )
    else:
        form = CentralActivityForm(instance=activity)
    return render(
        request, "central_content/activities/form.html",
        {"form": form, "subject": subject, "activity": activity},
    )


def _transition(request, sid, aid, fn, **kw):
    activity = _get_activity(sid, aid)
    try:
        fn(activity, actor=request.user, **kw)
    except IllegalTransition as exc:
        return HttpResponseBadRequest(str(exc))
    return HttpResponseRedirect(f"/subjects/{sid}/activities/{activity.id}/")


@central_role_required(*_ALL)
def activity_submit(request, subject_id: int, activity_id: int):
    return _transition(request, subject_id, activity_id, state_machine.submit_for_review)


@central_role_required(*_REVIEW)
def activity_approve(request, subject_id: int, activity_id: int):
    return _transition(request, subject_id, activity_id, state_machine.approve)


@central_role_required(*_REVIEW)
def activity_request_changes(request, subject_id: int, activity_id: int):
    notes = request.POST.get("notes", "")
    return _transition(
        request, subject_id, activity_id,
        state_machine.request_changes, notes=notes,
    )
