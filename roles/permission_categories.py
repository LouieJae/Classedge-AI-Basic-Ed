"""[Classedge LMS] Single source of truth for how Django permissions are
grouped in the role-CRUD picker UI.

Adding a new permission? Add its "app_label.codename" string to the
appropriate category below. The test_categorization.py CI guard will
fail if a permission from a Classedge-owned app is missing.

Apps deliberately absent from this module (and from CLASSEDGE_APPS in
the test): `gamification` and `ide`. Their permissions are managed by
code (XP awarded by gamification.views; coding exercises assigned per
assignment, not per role) and are not assignable through the role
picker. If a business need emerges for a "Gamification Moderator" or
"Code-Editor Reviewer" role, add those apps here and create matching
"Gamification" / "Code Editor" categories.
"""
from django.contrib.auth.models import Permission
from django.db.models import Q, QuerySet

# Functional-domain categorization. Keys are display labels; values are
# "app_label.codename" strings. Ordering within a category doesn't matter;
# the picker groups by the 4 standard actions (add/view/change/delete).
PERMISSION_CATEGORIES: dict[str, list[str]] = {
    "User Management": [
        "accounts.add_customuser",
        "accounts.view_customuser",
        "accounts.change_customuser",
        "accounts.delete_customuser",
        "accounts.add_profile",
        "accounts.view_profile",
        "accounts.change_profile",
        "accounts.delete_profile",
        "accounts.add_displayimage",
        "accounts.view_displayimage",
        "accounts.change_displayimage",
        "accounts.delete_displayimage",
        "accounts.add_apikey",
        "accounts.view_apikey",
        "accounts.change_apikey",
        "accounts.delete_apikey",
        "accounts.add_loginhistory",
        "accounts.view_loginhistory",
        "accounts.change_loginhistory",
        "accounts.delete_loginhistory",
        "accounts.add_userlegalconsent",
        "accounts.view_userlegalconsent",
        "accounts.change_userlegalconsent",
        "accounts.delete_userlegalconsent",
        "accounts.add_certificate",
        "accounts.view_certificate",
        "accounts.change_certificate",
        "accounts.delete_certificate",
        "accounts.add_studentsdg",
        "accounts.view_studentsdg",
        "accounts.change_studentsdg",
        "accounts.delete_studentsdg",
    ],
    "Roles & Permissions": [
        "roles.add_role",
        "roles.view_role",
        "roles.change_role",
        "roles.delete_role",
    ],
    "Departments & Programs": [
        "accounts.add_department",
        "accounts.view_department",
        "accounts.change_department",
        "accounts.delete_department",
        "accounts.add_schoolname",
        "accounts.view_schoolname",
        "accounts.change_schoolname",
        "accounts.delete_schoolname",
    ],
    "Academic Calendar": [
        "course.add_semester",
        "course.view_semester",
        "course.change_semester",
        "course.delete_semester",
        "course.add_term",
        "course.view_term",
        "course.change_term",
        "course.delete_term",
        "subject.add_schedule",
        "subject.view_schedule",
        "subject.change_schedule",
        "subject.delete_schedule",
        "course.add_retake",
        "course.view_retake",
        "course.change_retake",
        "course.delete_retake",
        "course.add_studentinvite",
        "course.view_studentinvite",
        "course.change_studentinvite",
        "course.delete_studentinvite",
        "course.add_subjectenrollment",
        "course.view_subjectenrollment",
        "course.change_subjectenrollment",
        "course.delete_subjectenrollment",
        "calendars.add_event",
        "calendars.view_event",
        "calendars.change_event",
        "calendars.delete_event",
        "calendars.add_holiday",
        "calendars.view_holiday",
        "calendars.change_holiday",
        "calendars.delete_holiday",
        "calendars.add_announcement",
        "calendars.view_announcement",
        "calendars.change_announcement",
        "calendars.delete_announcement",
    ],
    "Course Content": [
        "accounts.add_course",
        "accounts.view_course",
        "accounts.change_course",
        "accounts.delete_course",
        "subject.add_subject",
        "subject.view_subject",
        "subject.change_subject",
        "subject.delete_subject",
        "subject.add_subjectcollaborator",
        "subject.view_subjectcollaborator",
        "subject.change_subjectcollaborator",
        "subject.delete_subjectcollaborator",
        "module.add_module",
        "module.view_module",
        "module.change_module",
        "module.delete_module",
        "subject.add_subjectgradefinalization",
        "subject.view_subjectgradefinalization",
        "subject.change_subjectgradefinalization",
        "subject.delete_subjectgradefinalization",
        "subject.add_sdg",
        "subject.view_sdg",
        "subject.change_sdg",
        "subject.delete_sdg",
    ],
    "Activities & Quizzes": [
        "activity.add_activity",
        "activity.view_activity",
        "activity.change_activity",
        "activity.delete_activity",
        "activity.add_activitytype",
        "activity.view_activitytype",
        "activity.change_activitytype",
        "activity.delete_activitytype",
        "activity.add_activityquestion",
        "activity.view_activityquestion",
        "activity.change_activityquestion",
        "activity.delete_activityquestion",
        "activity.add_questionchoice",
        "activity.view_questionchoice",
        "activity.change_questionchoice",
        "activity.delete_questionchoice",
        "activity.add_quiztype",
        "activity.view_quiztype",
        "activity.change_quiztype",
        "activity.delete_quiztype",
        "activity.add_rubrics",
        "activity.view_rubrics",
        "activity.change_rubrics",
        "activity.delete_rubrics",
        "activity.add_rubricsitem",
        "activity.view_rubricsitem",
        "activity.change_rubricsitem",
        "activity.delete_rubricsitem",
        "activity.add_studentactivity",
        "activity.view_studentactivity",
        "activity.change_studentactivity",
        "activity.delete_studentactivity",
        "activity.add_studentquestion",
        "activity.view_studentquestion",
        "activity.change_studentquestion",
        "activity.delete_studentquestion",
        "activity.add_scorechangelog",
        "activity.view_scorechangelog",
        "activity.change_scorechangelog",
        "activity.delete_scorechangelog",
    ],
    "Gradebook": [
        "gradebookcomponent.add_gradebookcomponents",
        "gradebookcomponent.view_gradebookcomponents",
        "gradebookcomponent.change_gradebookcomponents",
        "gradebookcomponent.delete_gradebookcomponents",
        "gradebookcomponent.add_termgradebookcomponents",
        "gradebookcomponent.view_termgradebookcomponents",
        "gradebookcomponent.change_termgradebookcomponents",
        "gradebookcomponent.delete_termgradebookcomponents",
        "gradebookcomponent.add_activitytypepercentage",
        "gradebookcomponent.view_activitytypepercentage",
        "gradebookcomponent.change_activitytypepercentage",
        "gradebookcomponent.delete_activitytypepercentage",
        "gradebookcomponent.add_transmutationrule",
        "gradebookcomponent.view_transmutationrule",
        "gradebookcomponent.change_transmutationrule",
        "gradebookcomponent.delete_transmutationrule",
        "gradebookcomponent.add_gradevisibilitysettings",
        "gradebookcomponent.view_gradevisibilitysettings",
        "gradebookcomponent.change_gradevisibilitysettings",
        "gradebookcomponent.delete_gradevisibilitysettings",
    ],
    "Attendance": [
        "course.add_attendance",
        "course.view_attendance",
        "course.change_attendance",
        "course.delete_attendance",
        "course.add_attendancestatus",
        "course.view_attendancestatus",
        "course.change_attendancestatus",
        "course.delete_attendancestatus",
        "classroom.add_teacher_attendance",
        "classroom.view_teacher_attendance",
        "classroom.change_teacher_attendance",
        "classroom.delete_teacher_attendance",
        "course.add_teacherattendancepoints",
        "course.view_teacherattendancepoints",
        "course.change_teacherattendancepoints",
        "course.delete_teacherattendancepoints",
        "course.add_studentparticipationscore",
        "course.view_studentparticipationscore",
        "course.change_studentparticipationscore",
        "course.delete_studentparticipationscore",
    ],
    "Teacher Evaluations": [
        "subject.add_evaluationassignment",
        "subject.view_evaluationassignment",
        "subject.change_evaluationassignment",
        "subject.delete_evaluationassignment",
        "subject.add_evaluationquestion",
        "subject.view_evaluationquestion",
        "subject.change_evaluationquestion",
        "subject.delete_evaluationquestion",
        "subject.add_teacherevaluation",
        "subject.view_teacherevaluation",
        "subject.change_teacherevaluation",
        "subject.delete_teacherevaluation",
        "subject.add_teacherevaluationresponse",
        "subject.view_teacherevaluationresponse",
        "subject.change_teacherevaluationresponse",
        "subject.delete_teacherevaluationresponse",
    ],
    "Classroom Tools": [
        "classroom.add_classroom_mode",
        "classroom.view_classroom_mode",
        "classroom.change_classroom_mode",
        "classroom.delete_classroom_mode",
        "classroom.add_screenshot",
        "classroom.view_screenshot",
        "classroom.change_screenshot",
        "classroom.delete_screenshot",
    ],
    "Messaging": [
        "message.add_message",
        "message.view_message",
        "message.change_message",
        "message.delete_message",
        "message.add_friendrequest",
        "message.view_friendrequest",
        "message.change_friendrequest",
        "message.delete_friendrequest",
        "message.add_messagenotification",
        "message.view_messagenotification",
        "message.change_messagenotification",
        "message.delete_messagenotification",
    ],
    "Reports & Logs": [
        "logs.add_notification",
        "logs.view_notification",
        "logs.change_notification",
        "logs.delete_notification",
        "logs.add_studentactivitylog",
        "logs.view_studentactivitylog",
        "logs.change_studentactivitylog",
        "logs.delete_studentactivitylog",
        "logs.add_subjectlog",
        "logs.view_subjectlog",
        "logs.change_subjectlog",
        "logs.delete_subjectlog",
        "logs.add_usersubjectlog",
        "logs.view_usersubjectlog",
        "logs.change_usersubjectlog",
        "logs.delete_usersubjectlog",
    ],
}

# Explicit display order for categories in the picker. Categories that
# appear in PERMISSION_CATEGORIES but are missing from this list are
# appended at the end in dict-insertion order (defensive default; the
# test_category_order_matches_permission_categories_keys CI guard will
# flag the omission at test time).
CATEGORY_ORDER: list[str] = [
    "User Management",
    "Roles & Permissions",
    "Departments & Programs",
    "Academic Calendar",
    "Course Content",
    "Activities & Quizzes",
    "Gradebook",
    "Attendance",
    "Teacher Evaluations",
    "Classroom Tools",
    "Messaging",
    "Reports & Logs",
]

# Models deliberately hidden from the picker — operational/system models
# that should never be assignable via role perms. With auto-discovery enabled
# (see _auto_categorized_perms below), this list is now load-bearing: any
# model in here is filtered out of the auto-generated "Other" buckets too.
EXPLICITLY_EXCLUDED_MODELS: set[str] = {
    "retakerecord",
    "retakerecorddetail",
    "messagereadstatus",
    "messagetrashstatus",
    "messageunreadstatus",
    "msteams",
    "scormpackage",
    "studentprogress",
    "day",
    "section",
}

# Apps whose permissions should never appear in the picker. These are Django
# internals, third-party libraries, and observability/audit tooling — admins
# don't grant or revoke these via the role picker.
EXCLUDED_APP_LABELS: set[str] = {
    # Django built-ins
    "auth",
    "admin",
    "contenttypes",
    "sessions",
    "sites",
    "flatpages",
    # Auth / OAuth / JWT third parties
    "account",
    "socialaccount",
    "allauth",
    "microsoft",
    "oauth2_provider",
    "rest_framework_simplejwt",
    "token_blacklist",
    "authtoken",
    # Misc third parties
    "captcha",
    "easyaudit",
    "django_celery_beat",
    "django_celery_results",
    "lti1p3_tool_config",
    # Internal observability
    "auditlog",
}

# Auto-discovery toggle: when True (default) any Permission belonging to
# a Classedge-owned app that isn't already placed in PERMISSION_CATEGORIES
# is added to a fallback "Other · <App>" category, sorted by app_label.
AUTO_DISCOVER_UNCATEGORIZED: bool = True

# Pretty labels for the auto-generated category names. Falls back to title-case.
APP_LABEL_DISPLAY: dict[str, str] = {
    "accounts": "Accounts",
    "ai_content": "AI Content",
    "rag_tutor": "RAG Tutor",
    "received_central_content": "Central Content",
    "social_media": "Social Media",
    "ide": "Code Editor",
    "gamification": "Gamification",
    "coil": "COIL",
    "calendars": "Calendars",
    "logs": "Logs",
    "mobile": "Mobile",
    "module": "Modules",
    "subject": "Subjects",
    "course": "Courses",
    "classroom": "Classroom",
    "activity": "Activities",
    "gradebookcomponent": "Gradebook",
    "message": "Messaging",
    "rms": "Records & Payments",
}


def _humanize_app_label(app_label: str) -> str:
    return APP_LABEL_DISPLAY.get(app_label, app_label.replace("_", " ").title())


_ACTION_ORDER = {"view": 0, "add": 1, "change": 2, "delete": 3}


def _humanize_model(model_name: str) -> str:
    """[Classedge LMS] Best-effort label for the model row inside a category.

    Examples: ``customuser`` -> ``Custom User``; ``apikey`` -> ``Api Key``;
    ``gradebookcomponents`` -> ``Gradebook Components``. Heuristic only —
    if a model needs a different label, override in MODEL_DISPLAY_OVERRIDES.
    """
    label = MODEL_DISPLAY_OVERRIDES.get(model_name)
    if label:
        return label
    # Insert spaces before capitals already present, then title-case ascii.
    return model_name.replace("_", " ").title()


# Curated overrides for model labels that don't title-case nicely.
MODEL_DISPLAY_OVERRIDES: dict[str, str] = {
    "customuser": "User Account",
    "apikey": "API Key",
    "userlegalconsent": "Legal Consent",
    "studentsdg": "Student SDG",
    "sdg": "SDG",
    "displayimage": "Display Image",
    "loginhistory": "Login History",
    "schoolname": "School",
    "studentinvite": "Student Invite",
    "subjectenrollment": "Subject Enrollment",
    "subjectcollaborator": "Subject Collaborator",
    "subjectgradefinalization": "Grade Finalization",
    "activitytype": "Activity Type",
    "activityquestion": "Activity Question",
    "questionchoice": "Question Choice",
    "quiztype": "Quiz Type",
    "rubricsitem": "Rubric Item",
    "studentactivity": "Student Activity",
    "studentquestion": "Student Question",
    "scorechangelog": "Score Change Log",
    "gradebookcomponents": "Gradebook Components",
    "termgradebookcomponents": "Term Gradebook Components",
    "activitytypepercentage": "Activity Type Percentage",
    "transmutationrule": "Transmutation Rule",
    "gradevisibilitysettings": "Grade Visibility",
    "attendancestatus": "Attendance Status",
    "teacher_attendance": "Teacher Attendance",
    "teacherattendancepoints": "Teacher Attendance Points",
    "studentparticipationscore": "Student Participation Score",
    "evaluationassignment": "Evaluation Assignment",
    "evaluationquestion": "Evaluation Question",
    "teacherevaluation": "Teacher Evaluation",
    "teacherevaluationresponse": "Teacher Evaluation Response",
    "classroom_mode": "Classroom Mode",
    "friendrequest": "Friend Request",
    "messagenotification": "Message Notification",
    "studentactivitylog": "Student Activity Log",
    "subjectlog": "Subject Log",
    "usersubjectlog": "User-Subject Log",
}


def get_categorized_permissions() -> list[tuple[str, list[Permission]]]:
    """[Classedge LMS] Returns [(category_label, [Permission, ...]), ...]
    in CATEGORY_ORDER for the role-CRUD picker templates.

    Single DB query; resolves every "app_label.codename" string in
    PERMISSION_CATEGORIES to a live Permission row. Entries that don't
    resolve (e.g., stale after a model deletion) are skipped silently —
    the CI guard test_every_categorized_codename_resolves_to_a_real_permission
    catches these at test time.
    """
    all_codename_strs = [
        c for codenames in PERMISSION_CATEGORIES.values() for c in codenames
    ]
    split = [c.split(".", 1) for c in all_codename_strs if "." in c]
    fetched = Permission.objects.filter(
        content_type__app_label__in={pair[0] for pair in split},
        codename__in={pair[1] for pair in split},
    ).select_related("content_type")
    index: dict[tuple[str, str], Permission] = {
        (p.content_type.app_label, p.codename): p for p in fetched
    }

    ordered = list(CATEGORY_ORDER)
    for cat in PERMISSION_CATEGORIES:
        if cat not in ordered:
            ordered.append(cat)

    already_placed_ids: set[int] = set()
    result: list[tuple[str, list[Permission]]] = []
    for category in ordered:
        perms_in_cat: list[Permission] = []
        for codename_str in PERMISSION_CATEGORIES.get(category, []):
            try:
                app_label, codename = codename_str.split(".", 1)
            except ValueError:
                continue
            perm = index.get((app_label, codename))
            if perm is not None:
                perms_in_cat.append(perm)
                already_placed_ids.add(perm.id)
        result.append((category, perms_in_cat))

    if AUTO_DISCOVER_UNCATEGORIZED:
        for category_label, perms in _auto_categorized_perms(already_placed_ids):
            result.append((category_label, perms))
    return result


def _auto_categorized_perms(already_placed_ids: set[int]):
    """[Classedge LMS] Yield ``(category_label, [Permission...])`` for every
    permission belonging to a Classedge-owned app that isn't already placed
    in PERMISSION_CATEGORIES. Filters out Django/3rd-party internals via
    ``EXCLUDED_APP_LABELS`` and operational system models via
    ``EXPLICITLY_EXCLUDED_MODELS``. Each remaining app becomes its own
    auto-category named ``"Other · <App>"`` so categorized perms still
    sit at the top of the picker.
    """
    leftover = (
        Permission.objects
        .exclude(id__in=already_placed_ids)
        .exclude(content_type__app_label__in=EXCLUDED_APP_LABELS)
        .exclude(content_type__model__in=EXPLICITLY_EXCLUDED_MODELS)
        .select_related("content_type")
        .order_by("content_type__app_label", "content_type__model", "codename")
    )
    by_app: dict[str, list[Permission]] = {}
    for perm in leftover:
        by_app.setdefault(perm.content_type.app_label, []).append(perm)
    for app_label in sorted(by_app):
        yield (f"Other · {_humanize_app_label(app_label)}", by_app[app_label])


def get_categorized_permissions_grouped() -> list[
    tuple[str, list[tuple[str, list[tuple[str, Permission]]]]]
]:
    """[Classedge LMS] Same data as ``get_categorized_permissions`` but each
    category is further sub-grouped by model so the picker UI can render
    one row per model with its 4 actions, instead of a flat list of dozens
    of "Can add X / Can view X / Can change X / Can delete X" rows.

    Shape: ``[(category_label, [(model_label, [(action_label, Permission), ...]), ...]), ...]``
    Within each model the actions are ordered view → add → change → delete and
    each entry is paired with a short human action label ("View", "Create",
    "Edit", "Delete") so templates don't need to parse codenames.
    """
    grouped: list[
        tuple[str, list[tuple[str, list[tuple[str, Permission]]]]]
    ] = []
    action_label_map = {"view": "View", "add": "Create", "change": "Edit", "delete": "Delete"}
    for category, perms in get_categorized_permissions():
        by_model: dict[str, list[Permission]] = {}
        for perm in perms:
            by_model.setdefault(perm.content_type.model, []).append(perm)
        models_in_order: list[tuple[str, list[tuple[str, Permission]]]] = []
        for model_name, items in by_model.items():
            items.sort(
                key=lambda p: _ACTION_ORDER.get(p.codename.split("_", 1)[0], 99)
            )
            labeled = [
                (action_label_map.get(p.codename.split("_", 1)[0], p.codename), p)
                for p in items
            ]
            models_in_order.append((_humanize_model(model_name), labeled))
        grouped.append((category, models_in_order))
    return grouped


def get_all_categorized_permissions() -> QuerySet[Permission]:
    """[Classedge LMS] Flat QuerySet of every Permission visible in the role
    picker — both curated entries (PERMISSION_CATEGORIES) and the
    auto-discovered tail. Used by CSV import/export views — they need a
    flat collection, not grouped.
    """
    if AUTO_DISCOVER_UNCATEGORIZED:
        return (
            Permission.objects
            .exclude(content_type__app_label__in=EXCLUDED_APP_LABELS)
            .exclude(content_type__model__in=EXPLICITLY_EXCLUDED_MODELS)
            .select_related("content_type")
        )
    all_codename_strs = [
        c for codenames in PERMISSION_CATEGORIES.values() for c in codenames
    ]
    q = Q()
    for codename_str in all_codename_strs:
        if "." not in codename_str:
            continue
        app_label, codename = codename_str.split(".", 1)
        q |= Q(content_type__app_label=app_label, codename=codename)
    if not q:
        return Permission.objects.none()
    return Permission.objects.filter(q).select_related("content_type")
