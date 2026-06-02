# central_content/urls.py
from django.urls import path

from central_content.views import auth as auth_views
from central_content.views import dashboard as dashboard_views
from central_content.views import subjects as subject_views
from central_content.views import modules as module_views
from central_content.views import activities as activity_views
from central_content.views import staff as staff_views
from central_content.views import schools as schools_views
from central_content.views import matching as matching_views
from central_content.views import push_history as push_history_views
from central_content.views import textbooks as textbook_views
from central_content.views import plans as plan_views
from central_content.views import generation as generation_views

urlpatterns = [
    path("", dashboard_views.dashboard, name="dashboard"),
    path("login", auth_views.login_view, name="central_login"),
    path("logout", auth_views.logout_view, name="central_logout"),

    path("subjects/", subject_views.subject_list, name="subject_list"),
    path("subjects/new", subject_views.subject_create, name="subject_create"),
    path("subjects/<int:subject_id>/", subject_views.subject_detail, name="subject_detail"),
    path("subjects/<int:subject_id>/edit", subject_views.subject_edit, name="subject_edit"),
    path("subjects/<int:subject_id>/submit", subject_views.subject_submit, name="subject_submit"),
    path("subjects/<int:subject_id>/approve", subject_views.subject_approve, name="subject_approve"),
    path("subjects/<int:subject_id>/request-changes", subject_views.subject_request_changes, name="subject_request_changes"),
    path("subjects/<int:subject_id>/reopen", subject_views.subject_reopen, name="subject_reopen"),
    path("subjects/<int:subject_id>/history", subject_views.subject_history, name="subject_history"),

    path("subjects/<int:subject_id>/modules/new", module_views.module_create, name="module_create"),
    path("subjects/<int:subject_id>/modules/<int:module_id>/", module_views.module_detail, name="module_detail"),
    path("subjects/<int:subject_id>/modules/<int:module_id>/edit", module_views.module_edit, name="module_edit"),
    path("subjects/<int:subject_id>/modules/<int:module_id>/submit", module_views.module_submit, name="module_submit"),
    path("subjects/<int:subject_id>/modules/<int:module_id>/approve", module_views.module_approve, name="module_approve"),
    path("subjects/<int:subject_id>/modules/<int:module_id>/request-changes", module_views.module_request_changes, name="module_request_changes"),

    path("subjects/<int:subject_id>/activities/new", activity_views.activity_create, name="activity_create"),
    path("subjects/<int:subject_id>/activities/<str:activity_id>/", activity_views.activity_detail, name="activity_detail"),
    path("subjects/<int:subject_id>/activities/<str:activity_id>/edit", activity_views.activity_edit, name="activity_edit"),
    path("subjects/<int:subject_id>/activities/<str:activity_id>/submit", activity_views.activity_submit, name="activity_submit"),
    path("subjects/<int:subject_id>/activities/<str:activity_id>/approve", activity_views.activity_approve, name="activity_approve"),
    path("subjects/<int:subject_id>/activities/<str:activity_id>/request-changes", activity_views.activity_request_changes, name="activity_request_changes"),

    path("staff/", staff_views.staff_list, name="staff_list"),
    path("staff/new", staff_views.staff_create, name="staff_create"),
    path("staff/<int:staff_id>/edit", staff_views.staff_edit, name="staff_edit"),

    path("schools/", schools_views.school_list, name="school_list"),
    path("schools/new", schools_views.school_create, name="school_create"),
    path("schools/<int:school_id>/edit", schools_views.school_edit, name="school_edit"),
    path("schools/<int:school_id>/regenerate-token", schools_views.school_regenerate_token, name="school_regenerate_token"),

    path("matching/", matching_views.matching_workspace, name="matching_workspace"),
    path("matching/bind", matching_views.binding_create, name="binding_create"),
    path("matching/unbind-confirm/<int:binding_id>", matching_views.binding_unbind_confirm, name="binding_unbind_confirm"),
    path("matching/unbind/<int:binding_id>", matching_views.binding_unbind, name="binding_unbind"),
    path("matching/push/<int:binding_id>", matching_views.binding_push, name="binding_push"),

    path("push-history/", push_history_views.push_history_list, name="push_history_list"),

    # Textbook URLs
    path("subjects/<int:subject_id>/textbooks/upload", textbook_views.textbook_upload, name="textbook_upload"),
    path("subjects/<int:subject_id>/textbooks/<int:textbook_id>/", textbook_views.textbook_detail, name="textbook_detail"),
    path("subjects/<int:subject_id>/textbooks/<int:textbook_id>/status", textbook_views.textbook_status_badge, name="textbook_status_badge"),

    # Plans
    path("subjects/<int:subject_id>/textbooks/<int:textbook_id>/plans/generate", plan_views.plan_generate, name="plan_generate"),
    path("subjects/<int:subject_id>/textbooks/<int:textbook_id>/plans/<int:plan_id>/", plan_views.plan_detail, name="plan_detail"),
    path("subjects/<int:subject_id>/textbooks/<int:textbook_id>/plans/<int:plan_id>/edit", plan_views.plan_edit, name="plan_edit"),
    path("subjects/<int:subject_id>/textbooks/<int:textbook_id>/plans/<int:plan_id>/approve", plan_views.plan_approve, name="plan_approve"),
    path("subjects/<int:subject_id>/textbooks/<int:textbook_id>/plans/<int:plan_id>/reject", plan_views.plan_reject, name="plan_reject"),
    path("subjects/<int:subject_id>/plans/bulk-generate", plan_views.bulk_generate, name="bulk_generate"),

    # Content generation
    path("subjects/<int:subject_id>/textbooks/<int:textbook_id>/plans/<int:plan_id>/generate-content", generation_views.trigger_generation, name="trigger_generation"),
    path("subjects/<int:subject_id>/textbooks/<int:textbook_id>/plans/<int:plan_id>/jobs/<int:job_id>/", generation_views.job_status, name="job_status"),
    path("subjects/<int:subject_id>/textbooks/<int:textbook_id>/plans/<int:plan_id>/jobs/<int:job_id>/status", generation_views.job_status_badge, name="job_status_badge"),
]
