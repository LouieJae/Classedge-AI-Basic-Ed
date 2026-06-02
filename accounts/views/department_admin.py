from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.models.department_models import Department
from accounts.utils import get_pagination_context, paginate_queryset, search_queryset
from roles.decorators import admin_required


@admin_required
def department_list(request):
    """[Classedge LMS] Admin list of all departments with term count.

    Supports backend search + pagination + ?partial=1 for the
    cl-async-table.js no-reload pattern.
    """

    search_query = request.GET.get("search", "").strip()
    departments_qs = (
        Department.objects
        .annotate(term_count=Count("semesters__term"))
        .order_by("name")
    )
    departments_qs = search_queryset(departments_qs, search_query, ["name"])
    page_obj, _ = paginate_queryset(departments_qs, request, items_per_page=10)
    context = {
        "search_query": search_query,
        "title": "Departments",
        "icon": "fa-building",
        "search_placeholder": "Search departments by name...",
        "empty_icon": "fa-building",
        "empty_label": "departments",
        "columns": [
            {"label": "Department", "type": "name", "name_attr": "name"},
            {"label": "Created", "type": "date", "attr": "created_at"},
            {"label": "Action", "align": "right", "type": "actions", "items": [
                {"label": "Update", "icon": "fa-edit",
                 "onclick_template": "openDepartmentEditModal({id})"},
                {"divider": True},
                {"label": "Delete", "icon": "fa-trash", "danger": True,
                 "url_name": "department_delete", "url_arg_attr": "id"},
            ]},
        ],
    }
    context.update(get_pagination_context(page_obj, request))

    if request.GET.get("partial") == "1":
        return render(request, "includes/_list_table.html", context)
    return render(request, "accounts/departments/department_list.html", context)


@admin_required
def department_create(request):
    """[Classedge LMS] Create a new Department (name only). Modal-driven from department_list."""
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        if not name:
            messages.error(request, "Department name is required.")
            return redirect("department_list")
        if Department.objects.filter(name__iexact=name).exists():
            messages.error(request, f'A department named "{name}" already exists.')
            return redirect("department_list")
        Department.objects.create(name=name)
        messages.success(request, f'Department "{name}" created.')
        return redirect("department_list")
    return redirect("department_list")


@admin_required
def department_settings(request, dept_id):
    """[Classedge LMS] Rename a Department. GET returns the partial form for the edit modal."""
    dept = get_object_or_404(Department, pk=dept_id)
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        if not name:
            messages.error(request, "Department name is required.")
            return redirect("department_list")
        name_clash = (
            Department.objects
            .filter(name__iexact=name)
            .exclude(pk=dept.pk)
            .exists()
        )
        if name_clash:
            messages.error(request, f'A department named "{name}" already exists.')
            return redirect("department_list")
        dept.name = name
        dept.save()
        messages.success(request, f'"{dept.name}" updated.')
        return redirect("department_list")
    return render(
        request,
        "accounts/departments/_dept_form.html",
        {"dept": dept},
    )


@admin_required
@require_http_methods(["GET", "POST"])
def department_delete(request, dept_id):
    """[Classedge LMS] Delete a Department. Related rows (semesters, events, profiles) use SET_NULL."""
    dept = get_object_or_404(Department, pk=dept_id)
    if request.method == "POST":
        name = dept.name
        dept.delete()
        messages.success(request, f'Department "{name}" deleted.')
        return redirect("department_list")
    impact = {
        "semesters": dept.semesters.count(),
        "events": dept.events.count(),
        "holidays": dept.holidays.count(),
        "announcements": dept.announcements.count(),
    }
    return render(
        request,
        "accounts/departments/department_delete_confirm.html",
        {"dept": dept, "impact": impact},
    )
