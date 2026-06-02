import secrets

from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from central_content.forms import SchoolForm
from central_content.models import School
from central_content.permissions import central_role_required


@central_role_required("publisher", "reviewer")
def school_list(request):
    can_edit = request.user.role == "publisher"
    schools = School.objects.all().order_by("name")
    return render(
        request,
        "central_content/schools/list.html",
        {"schools": schools, "can_edit": can_edit},
    )


@central_role_required("publisher")
def school_create(request):
    if request.method == "POST":
        form = SchoolForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                school = form.save(commit=False)
                school.api_token = secrets.token_hex(20)
                school.created_by = request.user
                school.save()
            return render(
                request,
                "central_content/schools/token_reveal.html",
                {"school": school},
            )
    else:
        form = SchoolForm()
    return render(
        request,
        "central_content/schools/form.html",
        {"form": form, "mode": "create"},
    )


@central_role_required("publisher")
def school_edit(request, school_id):
    school = get_object_or_404(School, pk=school_id)
    if request.method == "POST":
        form = SchoolForm(request.POST, instance=school)
        if form.is_valid():
            form.save()
            return redirect("school_list")
    else:
        form = SchoolForm(instance=school)
    return render(
        request,
        "central_content/schools/form.html",
        {"form": form, "mode": "edit", "school": school},
    )


@central_role_required("publisher")
@require_http_methods(["POST"])
def school_regenerate_token(request, school_id):
    school = get_object_or_404(School, pk=school_id)
    school.api_token = secrets.token_hex(20)
    school.save(update_fields=["api_token", "updated_at"])
    return render(
        request,
        "central_content/schools/token_reveal.html",
        {"school": school, "regenerated": True},
    )
