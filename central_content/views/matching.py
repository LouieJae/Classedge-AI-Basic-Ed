import requests as http_requests

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from central_content.models import (
    CentralSubject, School, SchoolSubjectBinding,
)
from central_content.permissions import central_role_required
from central_content.push import delete_subject_from_school, push_subject_to_school


def _fetch_school_catalog(school):
    try:
        resp = http_requests.get(
            school.base_url.rstrip("/") + "/api/central/subjects/",
            headers={"Authorization": f"Bearer {school.api_token}"},
            timeout=30,
        )
        if resp.status_code != 200:
            return [], f"Unable to fetch school subject list (status {resp.status_code})."
        return resp.json(), None
    except http_requests.RequestException as e:
        return [], f"Unable to fetch school subject list ({e})."


@central_role_required("publisher", "reviewer")
def matching_workspace(request):
    can_bind = request.user.role == "publisher"

    schools = School.objects.filter(is_active=True).order_by("name")
    school_id = request.GET.get("school")
    selected_school = None
    if school_id:
        selected_school = schools.filter(pk=school_id).first()
    elif schools:
        selected_school = schools.first()

    catalog_rows, catalog_error = ([], None)
    bindings = []
    bound_school_subject_ids = set()
    bound_central_subject_ids = set()

    if selected_school:
        catalog_rows, catalog_error = _fetch_school_catalog(selected_school)
        bindings = list(
            SchoolSubjectBinding.objects
            .filter(target_school=selected_school)
            .select_related("central_subject")
        )
        bound_school_subject_ids = {b.school_subject_id for b in bindings}
        bound_central_subject_ids = {b.central_subject_id for b in bindings}

    central_subjects = list(
        CentralSubject.objects.filter(state="approved").order_by("subject_name")
    )

    return render(
        request,
        "central_content/matching/workspace.html",
        {
            "schools": schools,
            "selected_school": selected_school,
            "central_subjects": central_subjects,
            "catalog_rows": catalog_rows,
            "catalog_error": catalog_error,
            "bindings": bindings,
            "bound_school_subject_ids": bound_school_subject_ids,
            "bound_central_subject_ids": bound_central_subject_ids,
            "can_bind": can_bind,
        },
    )


@central_role_required("publisher")
@require_http_methods(["POST"])
def binding_create(request):
    school = get_object_or_404(School, pk=request.POST["school_id"])
    central_subject = get_object_or_404(
        CentralSubject, pk=request.POST["central_subject_id"], state="approved",
    )
    school_subject_id = int(request.POST["school_subject_id"])
    school_subject_name = request.POST.get("school_subject_name", "")
    school_subject_code = request.POST.get("school_subject_code", "")
    with transaction.atomic():
        SchoolSubjectBinding.objects.get_or_create(
            central_subject=central_subject,
            target_school=school,
            defaults={
                "school_subject_id": school_subject_id,
                "school_subject_name": school_subject_name,
                "school_subject_code": school_subject_code,
                "bound_by": request.user,
            },
        )
    return redirect(f"/matching/?school={school.pk}")


@central_role_required("publisher")
def binding_unbind_confirm(request, binding_id):
    binding = get_object_or_404(SchoolSubjectBinding, pk=binding_id)
    return render(
        request,
        "central_content/matching/unbind_confirm.html",
        {"binding": binding},
    )


@central_role_required("publisher")
@require_http_methods(["POST"])
def binding_unbind(request, binding_id):
    binding = get_object_or_404(SchoolSubjectBinding, pk=binding_id)
    confirm_name = request.POST.get("confirm_name", "")
    if confirm_name != binding.central_subject.subject_name:
        return HttpResponseBadRequest("Confirmation name did not match.")

    job = delete_subject_from_school(binding, triggered_by=request.user)
    if job.status == "success":
        school_id = binding.target_school_id
        binding.delete()
        return redirect(f"/matching/?school={school_id}")
    return render(
        request,
        "central_content/matching/unbind_confirm.html",
        {"binding": binding, "error": job.error_message or f"HTTP {job.http_status}"},
    )


@central_role_required("publisher")
@require_http_methods(["POST"])
def binding_push(request, binding_id):
    binding = get_object_or_404(SchoolSubjectBinding, pk=binding_id)
    job = push_subject_to_school(binding, triggered_by=request.user)
    if job.status == "success":
        messages.success(
            request,
            f"Pushed {binding.central_subject.subject_name} to {binding.target_school.name}.",
        )
    else:
        messages.error(
            request,
            f"Push failed ({job.http_status}): {job.error_message or job.response_body[:200]}",
        )
    return redirect(f"/matching/?school={binding.target_school_id}")
