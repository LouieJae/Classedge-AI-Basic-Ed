from accounts.utils import paginate_queryset, search_queryset, get_pagination_context
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.db.models import Q

from accounts.models import Profile


# ── List-table presentation config ────────────────────────────────────────────
# Column entries declare both the header AND how each cell renders. The
# reusable shell `templates/includes/_list_table.html` consumes this; no
# per-entity row partial is needed.

_PROFILE_VIEW_ACTION = {
    "label": "View", "icon": "fa-eye",
    "url_name": "account_profile_view", "url_arg_attr": "user.id",
}

_EDIT_PROFILE_ACTION = {
    "label": "Update", "icon": "fa-edit",
    "onclick_template": "openEditModal({id})",
}

_TOGGLE_ACTIVE_ACTION = {
    "label": "Activate / Deactivate",
    "label_attr": "active_toggle_label",
    "icon": "fa-user-shield",
    "url_name": "toggle_user_active",
    "url_arg_attr": "id",
    "form_post": True,
    "confirm": "Are you sure you want to change this user's login access?",
}


TEACHER_LIST_TABLE_CTX = {
    "title": "Teacher Master Data",
    "icon": "fa-chalkboard-teacher",
    "search_placeholder": "Search teachers by name, email, or ID...",
    "empty_icon": "fa-chalkboard-teacher",
    "empty_label": "teachers",
    "columns": [
        {"label": "#", "width": "60px", "type": "index"},
        {"label": "Name", "type": "name", "photo_attr": "student_photo",
         "editable": True, "edit_endpoint_name": "rename-profile",
         "edit_url_arg_attr": "id",
         "edit_first_field": "first_name", "edit_last_field": "last_name",
         "edit_min": 1, "edit_max": 100},
        {"label": "Email", "type": "truncate", "attr": "user.email", "max": 220},
        {"label": "ID Number", "type": "pill", "attr": "id_number", "muted": True},
        {"label": "Action", "align": "right", "type": "actions", "items": [
            _PROFILE_VIEW_ACTION,
            _EDIT_PROFILE_ACTION,
            _TOGGLE_ACTIVE_ACTION,
        ]},
    ],
}

STUDENT_LIST_TABLE_CTX = {
    "title": "Student Master Data",
    "icon": "fa-user-graduate",
    "extra_filters_template": "accounts/user_list/_student_filters.html",
    "search_placeholder": "Search students by name, email, or ID...",
    "empty_icon": "fa-user-graduate",
    "empty_label": "students",
    "columns": [
        {"label": "#", "width": "60px", "type": "index"},
        {"label": "Name", "type": "name", "photo_attr": "student_photo",
         "editable": True, "edit_endpoint_name": "rename-profile",
         "edit_url_arg_attr": "id",
         "edit_first_field": "first_name", "edit_last_field": "last_name",
         "edit_min": 1, "edit_max": 100},
        {"label": "Program", "type": "pill", "attr": "course.name"},
        {"label": "Year Level", "type": "meta", "attr": "grade_year_level"},
        {"label": "Email", "type": "truncate", "attr": "user.email", "max": 200},
        {"label": "ID Number", "type": "pill", "attr": "id_number", "muted": True},
        {"label": "Action", "align": "right", "type": "actions", "items": [
            _PROFILE_VIEW_ACTION,
            _EDIT_PROFILE_ACTION,
            _TOGGLE_ACTIVE_ACTION,
            {"label": "Enrolled Subjects", "icon": "fa-book",
             "url_name": "enrollment-report", "url_arg_attr": "id"},
        ]},
    ],
}

STAFF_LIST_TABLE_CTX = {
    "title": "Admin & Staff Master Data",
    "icon": "fa-user-tie",
    "search_placeholder": "Search staff by name, email, or ID...",
    "empty_icon": "fa-user-tie",
    "empty_label": "staff",
    "columns": [
        {"label": "#", "width": "60px", "type": "index"},
        {"label": "Name", "type": "name", "photo_attr": "student_photo",
         "editable": True, "edit_endpoint_name": "rename-profile",
         "edit_url_arg_attr": "id",
         "edit_first_field": "first_name", "edit_last_field": "last_name",
         "edit_min": 1, "edit_max": 100},
        {"label": "Role", "type": "pill", "attr": "role.name"},
        {"label": "Email", "type": "truncate", "attr": "user.email", "max": 200},
        {"label": "ID Number", "type": "pill", "attr": "id_number", "muted": True},
        {"label": "Action", "align": "right", "type": "actions", "items": [
            _PROFILE_VIEW_ACTION,
            _EDIT_PROFILE_ACTION,
            _TOGGLE_ACTIVE_ACTION,
        ]},
    ],
}

PROGRAM_HEAD_LIST_TABLE_CTX = {
    "title": "Program Head Master Data",
    "icon": "fa-user-cog",
    "search_placeholder": "Search program heads by name, email, or ID...",
    "empty_icon": "fa-user-cog",
    "empty_label": "program heads",
    "columns": [
        {"label": "#", "width": "60px", "type": "index"},
        {"label": "Name", "type": "name", "photo_attr": "student_photo",
         "editable": True, "edit_endpoint_name": "rename-profile",
         "edit_url_arg_attr": "id",
         "edit_first_field": "first_name", "edit_last_field": "last_name",
         "edit_min": 1, "edit_max": 100},
        {"label": "Email", "type": "truncate", "attr": "user.email", "max": 220},
        {"label": "ID Number", "type": "pill", "attr": "id_number", "muted": True},
        {"label": "Action", "align": "right", "type": "actions", "items": [
            _PROFILE_VIEW_ACTION,
            _EDIT_PROFILE_ACTION,
            _TOGGLE_ACTIVE_ACTION,
        ]},
    ],
}


def _render_list(request, full_template, context):
    if request.GET.get("partial") == "1":
        return render(request, "includes/_list_table.html", context)
    return render(request, full_template, context)


@login_required
@permission_required('accounts.change_profile', raise_exception=True)
@require_POST
def toggle_user_active(request, profile_id):
    """[Classedge LMS] Flip the underlying CustomUser.is_active flag for a
    profile so the user can / cannot log in. Operational admins (frontend
    admins) cannot toggle Django superusers or staff; only an actual Django
    superuser can do that. Users also cannot toggle themselves."""
    profile = get_object_or_404(Profile.objects.select_related("user"), id=profile_id)
    target = profile.user
    actor = request.user

    if target == actor:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect(request.META.get("HTTP_REFERER") or reverse("admin-and-staff-list"))

    if (target.is_superuser or target.is_staff) and not actor.is_superuser:
        return HttpResponseForbidden("You cannot change a system administrator's login access.")

    target.is_active = not target.is_active
    target.save(update_fields=["is_active"])

    action_word = "activated" if target.is_active else "deactivated"
    messages.success(request, f"{profile.first_name or target.get_username()} has been {action_word}.")
    return redirect(request.META.get("HTTP_REFERER") or reverse("admin-and-staff-list"))


def _hide_superusers_from(qs, request):
    """[Classedge LMS] Strip system-level accounts from a Profile queryset
    unless the viewer is a superuser. Hides both Django superusers AND
    is_staff users — anyone who can reach /admin/ is a "system admin" and
    should be invisible to operational frontend admins."""
    if request.user.is_superuser:
        return qs
    return qs.filter(user__is_superuser=False, user__is_staff=False)


# Program head ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@login_required
@permission_required('accounts.view_profile', raise_exception=True)
def program_head_list(request):
    search_query = request.GET.get('search', '').strip()
    program_head = Profile.objects.filter(role__name__iexact='program head').select_related('user', 'role')
    program_head = _hide_superusers_from(program_head, request)
    search_fields = ['first_name', 'last_name', 'user__email', 'id_number', 'department_fields__name']
    program_head = search_queryset(program_head, search_query, search_fields)
    page_obj, _ = paginate_queryset(program_head, request, items_per_page=10)
    role = request.user.profile.role.name
    context = {
        'role': role,
        'search_query': search_query,
        **PROGRAM_HEAD_LIST_TABLE_CTX,
    }
    context.update(get_pagination_context(page_obj, request))
    return _render_list(request, 'accounts/user_list/program-head-list.html', context)


# Student list ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@login_required
@permission_required('accounts.view_profile', raise_exception=True)
def student_list(request):
    search_query = request.GET.get('search', '').strip()
    selected_course = request.GET.get('course', '').strip()

    student = Profile.objects.filter(role__name__iexact='student').select_related('user', 'role', 'course')
    student = _hide_superusers_from(student, request)

    if selected_course:
        if selected_course == 'None':
            student = student.filter(course__isnull=True)
        else:
            student = student.filter(course__name=selected_course)

    search_fields = ['first_name', 'last_name', 'user__email', 'id_number', 'course__name']
    student = search_queryset(student, search_query, search_fields)

    page_obj, _ = paginate_queryset(student, request, items_per_page=10)
    role = request.user.profile.role.name

    courses = (
        Profile.objects.filter(role__name__iexact='student', course__isnull=False)
        .values_list('course__name', flat=True)
        .distinct()
        .order_by('course__name')
    )

    context = {
        'role': role,
        'search_query': search_query,
        'selected_course': selected_course,
        'courses': courses,
        **STUDENT_LIST_TABLE_CTX,
    }
    context.update(get_pagination_context(page_obj, request))
    return _render_list(request, 'accounts/user_list/student-list.html', context)


# Teacher ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@login_required
@permission_required('accounts.view_profile', raise_exception=True)
def teacher_list(request):
    search_query = request.GET.get('search', '').strip()
    teacher = Profile.objects.filter(role__name__iexact='teacher').select_related('user', 'role')
    teacher = _hide_superusers_from(teacher, request)
    search_fields = ['first_name', 'last_name', 'user__email', 'id_number']
    teacher = search_queryset(teacher, search_query, search_fields)
    page_obj, _ = paginate_queryset(teacher, request, items_per_page=10)
    role = request.user.profile.role.name
    context = {
        'role': role,
        'search_query': search_query,
        **TEACHER_LIST_TABLE_CTX,
    }
    context.update(get_pagination_context(page_obj, request))
    return _render_list(request, 'accounts/user_list/teacher-list.html', context)


# Admin & staff ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@permission_required('accounts.view_profile', raise_exception=True)
def admin_and_staff_list(request):
    search_query = request.GET.get('search', '').strip()
    admin_and_staff = Profile.objects.filter(
        ~Q(role__name__iexact='student')
        & ~Q(role__name__iexact='teacher')
        & ~Q(role__name__iexact='admin')
        & ~Q(role__name__iexact='program head')
    ).select_related('user', 'role')
    admin_and_staff = _hide_superusers_from(admin_and_staff, request)
    search_fields = ['first_name', 'last_name', 'user__email', 'id_number', 'department_fields__name']
    admin_and_staff = search_queryset(admin_and_staff, search_query, search_fields)
    page_obj, _ = paginate_queryset(admin_and_staff, request, items_per_page=10)
    role = request.user.profile.role.name
    context = {
        'role': role,
        'search_query': search_query,
        **STAFF_LIST_TABLE_CTX,
    }
    context.update(get_pagination_context(page_obj, request))
    return _render_list(request, 'accounts/user_list/staff-and-admin-list.html', context)


# ─── Click-to-edit endpoint ───────────────────────────────────────────
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

_PROFILE_PATCHABLE = {
    'first_name': {'min': 1, 'max': 255, 'label': 'First name'},
    'last_name':  {'min': 1, 'max': 255, 'label': 'Last name'},
}


@login_required
@permission_required('accounts.change_profile', raise_exception=True)
@require_http_methods(["PATCH"])
def rename_profile(request, pk):
    profile = get_object_or_404(Profile, pk=pk)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Malformed request body.'}, status=400)

    field = next((k for k in payload.keys() if k in _PROFILE_PATCHABLE), None)
    if not field:
        return JsonResponse({'ok': False, 'error': 'Field is not editable here.'}, status=400)

    rules = _PROFILE_PATCHABLE[field]
    value = (payload.get(field) or '').strip()

    if len(value) < rules['min']:
        return JsonResponse({
            'ok': False,
            'error': '%s cannot be empty.' % rules['label'],
        }, status=400)
    if len(value) > rules['max']:
        return JsonResponse({
            'ok': False,
            'error': '%s must be at most %d characters.' % (rules['label'], rules['max']),
        }, status=400)

    setattr(profile, field, value)
    profile.save(update_fields=[field])
    return JsonResponse({'ok': True, 'value': value})

