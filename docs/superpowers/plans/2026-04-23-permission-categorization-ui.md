# Permission Categorization + Role-Picker UI Polish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the brittle app-label whitelist in `roles/views.py` with a dev-curated `PERMISSION_CATEGORIES` dict, restructure the role-CRUD picker into collapsible functional sections with per-section select-all, narrow the dept-head dropdown to Program Head / Principal roles, and add a CI guard against uncategorized permissions.

**Architecture:** A single module `roles/permission_categories.py` holds the `PERMISSION_CATEGORIES` dict (functional domain → list of `"app_label.codename"` strings), a `CATEGORY_ORDER` display order, and two helper functions that the role views call. Templates render each category as an HTML5 `<details>` accordion. A separate `roles/constants.py` stores `DEPARTMENT_HEAD_ROLE_NAMES`. No schema change, no data migration.

**Tech Stack:** Django 4.x, Python 3.12, native HTML5 `<details>`, vanilla JS (no new deps), Neon Postgres test DB.

**Spec reference:** `docs/superpowers/specs/2026-04-23-permission-categorization-ui-design.md` (committed 2026-04-23, sha `10884570`).

---

## Preamble — environment notes

- **venv:** `source ~/classedge/env/bin/activate` from any working directory.
- **Test DB:** Neon Postgres, shared. **Always** pass `--keepdb` to `manage.py test` unless deliberately rebuilding. Fresh rebuilds take ~5 minutes and lock the shared DB for others.
- **Settings module:** `lms.settings` (already the default in `manage.py`).
- **Remote for pushing:** `personal` (NOT `origin`). Classedge policy.
- **Function labeling convention:** every new function/method needs `[Classedge LMS]` at the start of its docstring (Classedge LMS vs. Classedge Content Generator disambiguation).
- **Correction to spec's category table:** There is no `studentgrade` model in the codebase (it's a dead app_label in the old whitelist). The Gradebook category will contain only the 5 real models from the `gradebookcomponent` app.
- **CLASSEDGE_APPS (for the CI guard test):** `["accounts", "activity", "calendars", "classroom", "course", "gradebookcomponent", "logs", "message", "module", "roles", "subject"]` — 11 apps that actually exist. (The old whitelist included `"attendance"` and `"studentgrade"` which are not real apps.)

---

## File Structure

**Create:**
- `roles/permission_categories.py` — `PERMISSION_CATEGORIES` dict, `CATEGORY_ORDER`, `EXPLICITLY_EXCLUDED_MODELS`, two helper functions.
- `roles/constants.py` — `DEPARTMENT_HEAD_ROLE_NAMES` tuple.
- `roles/tests/test_categorization.py` — CI guard tests.
- `roles/tests/test_picker_rendering.py` — picker rendering tests.
- `roles/tests/test_auth_smoke.py` — auth surface smoke tests.

**Modify:**
- `roles/views.py` — delete 5 duplicated whitelist blocks; call helpers instead.
- `roles/templates/role/addRole.html` — grouped `<details>` picker + per-section select-all.
- `roles/templates/role/updateRole.html` — same structure.
- `roles/templates/role/viewRole.html` — same structure, disabled checkboxes (read-only).
- `accounts/views/department_admin.py` — filter `candidate_heads` by role name.

**Not touched:** `roles/models.py`, role data, CSV format, `roles/urls.py`.

---

## Task 1: Bootstrap — branch, empty modules, imports

**Files:**
- Create: `roles/permission_categories.py`
- Create: `roles/constants.py`

- [ ] **Step 1: Cut a feature branch from `main`**

```bash
cd ~/classedge
git checkout main
git pull personal main
git checkout -b feat/permission-categorization-phase3
```

- [ ] **Step 2: Create empty `roles/constants.py`**

Contents:

```python
"""[Classedge LMS] Module-level constants for the roles app."""

# Roles whose users appear in the department-head dropdown on
# the department-settings page. Program Head covers colleges today;
# Principal is listed proactively so the filter picks it up as soon
# as IT Admin creates the Principal role row.
DEPARTMENT_HEAD_ROLE_NAMES: tuple[str, ...] = ("Program Head", "Principal")
```

- [ ] **Step 3: Create stub `roles/permission_categories.py`**

Contents (dict populated later — stubbed now so imports work):

```python
"""[Classedge LMS] Single source of truth for how Django permissions are
grouped in the role-CRUD picker UI.

Adding a new permission? Add its "app_label.codename" string to the
appropriate category below. The test_categorization.py CI guard will
fail if a permission from a Classedge-owned app is missing.
"""
from django.contrib.auth.models import Permission
from django.db.models import QuerySet

# Functional-domain categorization. Keys are display labels; values are
# "app_label.codename" strings. Ordering within a category doesn't matter;
# the picker groups by the 4 standard actions (add/view/change/delete).
PERMISSION_CATEGORIES: dict[str, list[str]] = {}

# Explicit display order for categories in the picker. Categories not
# listed here are appended alphabetically at the end (defensive default).
CATEGORY_ORDER: list[str] = []

# Models deliberately hidden from the picker (operational/system models
# that should never be assignable via role perms). Kept narrow — anything
# not in a category is already hidden; this set only documents *intent*.
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


def get_categorized_permissions() -> list[tuple[str, list[Permission]]]:
    """[Classedge LMS] Returns [(category_label, [Permission, ...]), ...]
    in CATEGORY_ORDER for the role-CRUD picker templates.

    Single DB query; resolves every "app_label.codename" string in
    PERMISSION_CATEGORIES to a live Permission row. Entries that don't
    resolve (e.g., stale after a model deletion) are skipped silently —
    the CI guard test_every_categorized_codename_resolves_to_a_real_permission
    catches these at test time.
    """
    return []


def get_all_categorized_permissions() -> QuerySet[Permission]:
    """[Classedge LMS] Flat QuerySet of every Permission appearing anywhere
    in PERMISSION_CATEGORIES. Used by the CSV import/export views.
    """
    return Permission.objects.none()
```

- [ ] **Step 4: Verify Python imports**

Run:

```bash
source ~/classedge/env/bin/activate
python -c "from roles.permission_categories import PERMISSION_CATEGORIES, CATEGORY_ORDER, EXPLICITLY_EXCLUDED_MODELS, get_categorized_permissions, get_all_categorized_permissions"
python -c "from roles.constants import DEPARTMENT_HEAD_ROLE_NAMES; print(DEPARTMENT_HEAD_ROLE_NAMES)"
```

Expected output:

```
('Program Head', 'Principal')
```

- [ ] **Step 5: Commit**

```bash
git add roles/permission_categories.py roles/constants.py
git commit -m "feat(roles): scaffold permission_categories module + dept-head constants"
```

---

## Task 2: Write the CI guard tests (TDD — failing first)

**Files:**
- Create: `roles/tests/test_categorization.py`

- [ ] **Step 1: Write the three CI guard tests**

Contents of `roles/tests/test_categorization.py`:

```python
"""[Classedge LMS] CI guard — enforces PERMISSION_CATEGORIES completeness.

If any of these tests fail on a PR, the fix is to add the missing/fix the
broken entry in roles/permission_categories.py (usually one line).
"""
from django.contrib.auth.models import Permission
from django.test import TestCase

from roles.permission_categories import (
    CATEGORY_ORDER,
    EXPLICITLY_EXCLUDED_MODELS,
    PERMISSION_CATEGORIES,
)


# Apps whose permissions MUST appear in PERMISSION_CATEGORIES. Dead
# app_labels ("attendance", "studentgrade") from the pre-Phase-3 whitelist
# are NOT listed — they reference apps that don't exist in the project.
CLASSEDGE_APPS: list[str] = [
    "accounts",
    "activity",
    "calendars",
    "classroom",
    "course",
    "gradebookcomponent",
    "logs",
    "message",
    "module",
    "roles",
    "subject",
]


class CategorizationCompletenessTests(TestCase):
    def test_every_permission_from_our_apps_is_categorized(self):
        """Every Permission from a Classedge-owned app must appear in some
        category (unless its model is in EXPLICITLY_EXCLUDED_MODELS)."""
        all_categorized = {
            codename
            for perms in PERMISSION_CATEGORIES.values()
            for codename in perms
        }
        db_perms = Permission.objects.filter(
            content_type__app_label__in=CLASSEDGE_APPS
        ).exclude(content_type__model__in=EXPLICITLY_EXCLUDED_MODELS)
        missing = sorted(
            f"{p.content_type.app_label}.{p.codename}"
            for p in db_perms
            if f"{p.content_type.app_label}.{p.codename}" not in all_categorized
        )
        self.assertEqual(
            missing,
            [],
            f"Uncategorized permissions (add each to roles/permission_categories.py): {missing}",
        )

    def test_no_permission_is_in_two_categories(self):
        """A permission must live in exactly one category — enforces the
        single-source-of-truth invariant."""
        seen: dict[str, str] = {}
        duplicates: list[tuple[str, str, str]] = []
        for category, codenames in PERMISSION_CATEGORIES.items():
            for codename in codenames:
                if codename in seen:
                    duplicates.append((codename, seen[codename], category))
                seen[codename] = category
        self.assertEqual(
            duplicates,
            [],
            f"Permissions appearing in multiple categories: {duplicates}",
        )

    def test_every_categorized_codename_resolves_to_a_real_permission(self):
        """Typos ('gradebookcomponent.add_gradebok') and orphaned entries
        (categorized codename pointing at a deleted model) fail here."""
        unresolved: list[str] = []
        for codenames in PERMISSION_CATEGORIES.values():
            for codename_str in codenames:
                try:
                    app_label, codename = codename_str.split(".", 1)
                except ValueError:
                    unresolved.append(codename_str)
                    continue
                if not Permission.objects.filter(
                    content_type__app_label=app_label, codename=codename
                ).exists():
                    unresolved.append(codename_str)
        self.assertEqual(
            unresolved,
            [],
            f"Categorized codenames that don't resolve to real Permissions: {unresolved}",
        )


class CategoryOrderTests(TestCase):
    def test_category_order_matches_permission_categories_keys(self):
        """CATEGORY_ORDER must list every category defined in
        PERMISSION_CATEGORIES, with no extras."""
        self.assertEqual(
            sorted(CATEGORY_ORDER),
            sorted(PERMISSION_CATEGORIES.keys()),
            "CATEGORY_ORDER is out of sync with PERMISSION_CATEGORIES keys",
        )
```

- [ ] **Step 2: Run tests to verify they fail correctly**

Run:

```bash
source ~/classedge/env/bin/activate
cd ~/classedge
python manage.py test roles.tests.test_categorization --keepdb -v 2
```

Expected:
- `test_every_permission_from_our_apps_is_categorized` FAILS with a long list of missing codenames (~200+ entries) — because `PERMISSION_CATEGORIES` is empty.
- `test_no_permission_is_in_two_categories` PASSES (empty dict has no duplicates).
- `test_every_categorized_codename_resolves_to_a_real_permission` PASSES (empty dict has nothing to resolve).
- `test_category_order_matches_permission_categories_keys` PASSES (both empty).

Copy the long failure list from stdout — it is the exact to-do list for Task 3.

- [ ] **Step 3: Commit**

```bash
git add roles/tests/test_categorization.py
git commit -m "test(roles): add CI guard for permission categorization completeness"
```

---

## Task 3: Populate PERMISSION_CATEGORIES — make the CI guard pass

**Files:**
- Modify: `roles/permission_categories.py`

This task walks the 12 functional categories from the spec in order. Each sub-step adds one category; each commit is one category so bisecting on a categorization mistake is easy later.

**Strategy:** for each category, list every `"app_label.codename"` for the models the spec assigns to that category. The standard Django auto-permissions are `add_<model>`, `view_<model>`, `change_<model>`, `delete_<model>` — list all four unless noted.

- [ ] **Step 1: Print the authoritative codename list for each model**

Run this one-off script to get the ground truth:

```bash
source ~/classedge/env/bin/activate
cd ~/classedge
python manage.py shell -c "
from django.contrib.auth.models import Permission
from collections import defaultdict
apps_to_dump = ['accounts','activity','calendars','classroom','course','gradebookcomponent','logs','message','module','roles','subject']
by_model = defaultdict(list)
for p in Permission.objects.filter(content_type__app_label__in=apps_to_dump).order_by('content_type__app_label','content_type__model','codename'):
    key = (p.content_type.app_label, p.content_type.model)
    by_model[key].append(p.codename)
for (app, model), codes in sorted(by_model.items()):
    print(f'# {app}.{model}')
    for c in codes:
        print(f'    \"{app}.{c}\",')
    print()
"
```

Save this output to a scratch file (e.g. `/tmp/codenames.txt`) — you will copy-paste from it.

- [ ] **Step 2: Populate User Management category**

Open `roles/permission_categories.py` and replace the `PERMISSION_CATEGORIES: dict[str, list[str]] = {}` line with:

```python
PERMISSION_CATEGORIES: dict[str, list[str]] = {
    "User Management": [
        # accounts.customuser
        "accounts.add_customuser",
        "accounts.view_customuser",
        "accounts.change_customuser",
        "accounts.delete_customuser",
        # accounts.profile
        "accounts.add_profile",
        "accounts.view_profile",
        "accounts.change_profile",
        "accounts.delete_profile",
        # accounts.displayimage
        "accounts.add_displayimage",
        "accounts.view_displayimage",
        "accounts.change_displayimage",
        "accounts.delete_displayimage",
        # accounts.apikey
        "accounts.add_apikey",
        "accounts.view_apikey",
        "accounts.change_apikey",
        "accounts.delete_apikey",
        # accounts.loginhistory
        "accounts.add_loginhistory",
        "accounts.view_loginhistory",
        "accounts.change_loginhistory",
        "accounts.delete_loginhistory",
        # accounts.userlegalconsent
        "accounts.add_userlegalconsent",
        "accounts.view_userlegalconsent",
        "accounts.change_userlegalconsent",
        "accounts.delete_userlegalconsent",
        # accounts.certificate
        "accounts.add_certificate",
        "accounts.view_certificate",
        "accounts.change_certificate",
        "accounts.delete_certificate",
        # accounts.studentsdg
        "accounts.add_studentsdg",
        "accounts.view_studentsdg",
        "accounts.change_studentsdg",
        "accounts.delete_studentsdg",
    ],
}
```

- [ ] **Step 3: Populate remaining categories (one dict key per category)**

Add the following keys **after** `"User Management"`. For each model, generate all four `add/view/change/delete` codenames unless the model doesn't have one (Step 1's dump is authoritative — if a model is missing an `add_`, don't include it).

Category → model list (from the spec):

- `"Roles & Permissions"` → `roles.role`
- `"Departments & Programs"` → `accounts.department`, `accounts.program`, `accounts.schoolname`, `accounts.legaldocument`, `accounts.termandagreement`
- `"Academic Calendar"` → `course.semester`, `course.term`, `subject.schedule`, `course.retake`, `course.studentinvite`, `course.subjectenrollment` (+ `calendars.*` — see note)
- `"Course Content"` → `course.course`, `subject.subject`, `subject.subjectcollaborator`, `module.module`, `subject.subjectgradefinalization`, `subject.sdg`
- `"Activities & Quizzes"` → `activity.activity`, `activity.activitytype`, `activity.activityquestion`, `activity.questionchoice`, `activity.quiztype`, `activity.rubrics`, `activity.rubricsitem`, `activity.studentactivity`, `activity.studentquestion`, `activity.scorechangelog`
- `"Gradebook"` → `gradebookcomponent.gradebookcomponents`, `gradebookcomponent.termgradebookcomponents`, `gradebookcomponent.activitytypepercentage`, `gradebookcomponent.transmutationrule`, `gradebookcomponent.gradevisibilitysettings`
- `"Attendance"` → `course.attendance`, `course.attendancestatus`, `classroom.teacher_attendance`, `course.teacherattendancepoints`, `course.studentparticipationscore`
- `"Teacher Evaluations"` → `subject.evaluationassignment`, `subject.evaluationquestion`, `subject.teacherevaluation`, `subject.teacherevaluationresponse`
- `"Messaging"` → `message.message`, `message.friendrequest`, `message.messagenotification`
- `"Classroom Tools"` → `classroom.classroom`, `classroom.classroom_mode`, `classroom.screenshot`
- `"Reports & Logs"` → `logs.notification`, `logs.studentactivitylog`, `logs.subjectlog`, `logs.useractivitylog`, `logs.usersubjectlog`, `accounts.badge`, `accounts.attachment`

**Note — `calendars.*` handling:** `calendars` is a Classedge-owned app (it houses Event/Holiday models introduced in the department-scoped-calendars PR). Use Step 1's dump to list its models and place them under `"Academic Calendar"` unless the model is obviously in a different functional domain.

Also set `CATEGORY_ORDER`:

```python
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
```

- [ ] **Step 4: Run the CI guard tests to check for gaps**

Run:

```bash
python manage.py test roles.tests.test_categorization --keepdb -v 2
```

Expected: all four tests PASS.

If `test_every_permission_from_our_apps_is_categorized` still fails, the failure message lists the exact codenames you missed. Add each to the most appropriate category and re-run.

If `test_no_permission_is_in_two_categories` fails, remove the duplicate.

If `test_every_categorized_codename_resolves_to_a_real_permission` fails, there's a typo — compare with Step 1's dump.

- [ ] **Step 5: Commit**

```bash
git add roles/permission_categories.py
git commit -m "feat(roles): populate PERMISSION_CATEGORIES with 12 functional categories"
```

---

## Task 4: Implement the two helper functions

**Files:**
- Modify: `roles/permission_categories.py`
- Modify: `roles/tests/test_categorization.py`

- [ ] **Step 1: Write tests for the helpers**

Append to `roles/tests/test_categorization.py`:

```python
class HelperFunctionTests(TestCase):
    def test_get_categorized_permissions_returns_categories_in_order(self):
        """Helper returns list[(label, list[Permission])] matching CATEGORY_ORDER."""
        from roles.permission_categories import get_categorized_permissions
        result = get_categorized_permissions()
        labels = [label for label, _ in result]
        self.assertEqual(labels, CATEGORY_ORDER)

    def test_get_categorized_permissions_each_bucket_is_nonempty(self):
        from roles.permission_categories import get_categorized_permissions
        for label, perms in get_categorized_permissions():
            self.assertGreater(
                len(perms), 0, f"Category {label!r} has no resolvable permissions"
            )

    def test_get_categorized_permissions_only_resolves_real_permissions(self):
        """Each returned Permission is a real DB row (not a mock)."""
        from roles.permission_categories import get_categorized_permissions
        for _, perms in get_categorized_permissions():
            for p in perms:
                self.assertIsNotNone(p.pk)

    def test_get_all_categorized_permissions_is_flat_superset(self):
        """get_all_categorized_permissions() returns every Permission that
        appears somewhere in the categorized list."""
        from roles.permission_categories import (
            get_all_categorized_permissions,
            get_categorized_permissions,
        )
        flat_ids = set(get_all_categorized_permissions().values_list("id", flat=True))
        grouped_ids = {
            p.id for _, perms in get_categorized_permissions() for p in perms
        }
        self.assertEqual(flat_ids, grouped_ids)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python manage.py test roles.tests.test_categorization.HelperFunctionTests --keepdb -v 2
```

Expected:
- `test_get_categorized_permissions_returns_categories_in_order` FAILS (helper returns empty list).
- `test_get_categorized_permissions_each_bucket_is_nonempty` FAILS.
- `test_get_categorized_permissions_only_resolves_real_permissions` PASSES vacuously (loop over empty list).
- `test_get_all_categorized_permissions_is_flat_superset` PASSES vacuously (both empty).

- [ ] **Step 3: Implement the helpers**

In `roles/permission_categories.py`, replace the two stub function bodies:

```python
def get_categorized_permissions() -> list[tuple[str, list[Permission]]]:
    """[Classedge LMS] Returns [(category_label, [Permission, ...]), ...]
    in CATEGORY_ORDER for the role-CRUD picker templates.

    Single DB query; resolves every "app_label.codename" string in
    PERMISSION_CATEGORIES to a live Permission row. Entries that don't
    resolve are skipped silently — the CI guard
    test_every_categorized_codename_resolves_to_a_real_permission
    catches these at test time.
    """
    # One query for all codenames appearing in any category.
    all_codename_strs = [
        c for codenames in PERMISSION_CATEGORIES.values() for c in codenames
    ]
    # Split into (app_label, codename) pairs and build a lookup index.
    split = [c.split(".", 1) for c in all_codename_strs if "." in c]
    # Fetch once; index by (app_label, codename).
    fetched = Permission.objects.filter(
        content_type__app_label__in={pair[0] for pair in split}
    ).select_related("content_type")
    index: dict[tuple[str, str], Permission] = {
        (p.content_type.app_label, p.codename): p for p in fetched
    }

    # Assemble in CATEGORY_ORDER.
    ordered = list(CATEGORY_ORDER)
    # Defensive: append any category not in CATEGORY_ORDER (shouldn't happen
    # in practice — test_category_order_matches_permission_categories_keys
    # catches drift).
    for cat in PERMISSION_CATEGORIES:
        if cat not in ordered:
            ordered.append(cat)

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
        result.append((category, perms_in_cat))
    return result


def get_all_categorized_permissions() -> QuerySet[Permission]:
    """[Classedge LMS] Flat QuerySet of every Permission appearing anywhere
    in PERMISSION_CATEGORIES. Used by CSV import/export views — they need
    a flat collection, not grouped.
    """
    all_codename_strs = [
        c for codenames in PERMISSION_CATEGORIES.values() for c in codenames
    ]
    # Build a Q object matching each (app_label, codename) pair.
    from django.db.models import Q
    q = Q()
    for codename_str in all_codename_strs:
        if "." not in codename_str:
            continue
        app_label, codename = codename_str.split(".", 1)
        q |= Q(content_type__app_label=app_label, codename=codename)
    if not q:
        return Permission.objects.none()
    return Permission.objects.filter(q).select_related("content_type")
```

- [ ] **Step 4: Run helper tests to verify they pass**

Run:

```bash
python manage.py test roles.tests.test_categorization.HelperFunctionTests --keepdb -v 2
```

Expected: all 4 HelperFunctionTests PASS.

Also re-run the guard tests to confirm no regression:

```bash
python manage.py test roles.tests.test_categorization --keepdb -v 2
```

Expected: all 8 tests in the module PASS.

- [ ] **Step 5: Commit**

```bash
git add roles/permission_categories.py roles/tests/test_categorization.py
git commit -m "feat(roles): implement get_categorized_permissions + get_all_categorized_permissions helpers"
```

---

## Task 5: Refactor picker views to use the helper

**Files:**
- Modify: `roles/views.py`

Four views today each embed the same whitelist/exclude block: `roleList`, `viewRole`, `createRole` (duplicated inside the GET branch), `updateRole`. Replace each with a call to `get_categorized_permissions()`. The template contract changes from `structured_permissions: dict[model_name, {add,view,change,delete}]` to `categorized_permissions: list[tuple[category_label, list[Permission]]]`.

- [ ] **Step 1: Read the current state of `roles/views.py`**

```bash
wc -l ~/classedge/roles/views.py
```

Expected: ~375 lines. After this task ends: ~230 lines.

- [ ] **Step 2: Replace the `roleList` view**

Find (lines 17-40):

```python
@login_required
@admin_required
def roleList(request):
    form = roleForm()
    roles = Role.objects.all()
    excluded_models = [
        'retakerecord', 'retakerecorddetail', 'messagereadstatus', 'messagetrashstatus', 
        'messageunreadstatus', 'msteams', 'scormpackage', 'studentprogress', 'day','section',
    ]

    # Filter permissions based on existing models and exclude unwanted ones
    permissions = Permission.objects.filter(content_type__app_label__in=[
        'accounts', 'subject', 'course', 'activity', 'module', 'message', 'gradebookcomponent', 
        'studentgrade', 'roles', 'attendance', 'classroom', "StudentActivityLog", " SubjectLog"
    ]).exclude(content_type__model__in=excluded_models)

    structured_permissions = defaultdict(lambda: {'add': None, 'view': None, 'change': None, 'delete': None})
    for perm in permissions:
        action = perm.codename.split('_')[0]
        model = perm.content_type.model
        if action in ['add', 'view', 'change', 'delete']:
            structured_permissions[model][action] = perm

    return render(request, 'role/roleList.html', {'roles': roles, 'structured_permissions': dict(structured_permissions), 'form': form})
```

Replace with:

```python
@login_required
@admin_required
def roleList(request):
    """[Classedge LMS] IT-Admin list view of all roles; renders the add-role side modal."""
    form = roleForm()
    roles = Role.objects.all()
    return render(
        request,
        "role/roleList.html",
        {
            "roles": roles,
            "categorized_permissions": get_categorized_permissions(),
            "form": form,
        },
    )
```

- [ ] **Step 3: Replace the `viewRole` view**

Find the `viewRole` block (lines ~43-62) and replace with:

```python
@login_required
@admin_required
def viewRole(request, role_id):
    """[Classedge LMS] Read-only view of a single role's permission assignments."""
    role_obj = get_object_or_404(Role, id=role_id)
    return render(
        request,
        "role/viewRole.html",
        {
            "role": role_obj,
            "categorized_permissions": get_categorized_permissions(),
        },
    )
```

- [ ] **Step 4: Replace the `createRole` view**

Find the `createRole` block (lines ~65-121). Replace with:

```python
@login_required
@admin_required
def createRole(request):
    """[Classedge LMS] Create a new role with selected permissions, optionally
    copying permissions from an existing role."""
    if request.method == "POST":
        form = roleForm(request.POST)
        role_name = request.POST.get("name")

        if Role.objects.filter(name__iexact=role_name).exists():
            messages.error(
                request,
                f'The role "{role_name}" already exists. Please choose a different name.',
            )
            return redirect("roleList")

        if form.is_valid():
            role = form.save()
            selected_permissions = request.POST.getlist("permissions")
            permissions = Permission.objects.filter(id__in=selected_permissions)
            role.permissions.set(permissions)

            source_role_id = request.POST.get("source_role_id")
            if source_role_id:
                source_role = get_object_or_404(Role, id=source_role_id)
                role.permissions.set(source_role.permissions.all())

            messages.success(request, "Role created successfully!")
            return redirect("roleList")
        else:
            messages.error(
                request,
                "There was an error creating the role. Please check the form.",
            )
    else:
        form = roleForm()

    return render(
        request,
        "role/addRole.html",
        {
            "form": form,
            "categorized_permissions": get_categorized_permissions(),
        },
    )
```

- [ ] **Step 5: Replace the `updateRole` view**

Find the `updateRole` block (lines ~124-167). Replace with:

```python
@login_required
@admin_required
def updateRole(request, pk):
    """[Classedge LMS] Edit an existing role's name + permission assignments."""
    role_obj = get_object_or_404(Role, pk=pk)

    if request.method == "POST":
        form = roleForm(request.POST, instance=role_obj)
        if form.is_valid():
            role = form.save()
            selected_permissions = request.POST.getlist("permissions")
            permissions = Permission.objects.filter(id__in=selected_permissions)
            role.permissions.set(permissions)
            messages.success(request, "Role updated successfully!")
            return redirect("roleList")
    else:
        form = roleForm(instance=role_obj)

    return render(
        request,
        "role/updateRole.html",
        {
            "form": form,
            "categorized_permissions": get_categorized_permissions(),
            "role": role_obj,
        },
    )
```

- [ ] **Step 6: Update the imports at the top of `roles/views.py`**

Replace the existing import block (lines 1-14) with:

```python
import csv
import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Permission
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .decorators import admin_required
from .forms import roleForm
from .models import Role
from .permission_categories import (
    get_all_categorized_permissions,
    get_categorized_permissions,
)
```

(The `defaultdict` and `ContentType` imports drop out; they were only used by the removed whitelist code.)

- [ ] **Step 7: Django sanity check**

Run:

```bash
python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 8: Commit**

```bash
git add roles/views.py
git commit -m "refactor(roles): picker views call get_categorized_permissions helper"
```

---

## Task 6: Refactor CSV views to use the flat helper

**Files:**
- Modify: `roles/views.py`

Three CSV views (`import_roles_csv`, `export_roles_csv`, `download_roles_template`) still embed the old whitelist. Replace with `get_all_categorized_permissions()`.

- [ ] **Step 1: Replace inline whitelist in `import_roles_csv`**

Find in `import_roles_csv` (around lines 204-214):

```python
            # Get all permissions for reference
            excluded_models = [
                'retakerecord', 'retakerecorddetail', 'messagereadstatus', 'messagetrashstatus', 
                'messageunreadstatus', 'msteams', 'scormpackage', 'studentprogress', 'day', 'section',
            ]
            
            all_permissions = Permission.objects.filter(
                content_type__app_label__in=[
                    'accounts', 'subject', 'course', 'activity', 'module', 'message', 'gradebookcomponent', 
                    'studentgrade', 'roles', 'attendance', 'classroom', 'logs'
                ]
            ).exclude(content_type__model__in=excluded_models)
```

Replace with:

```python
            all_permissions = get_all_categorized_permissions()
```

- [ ] **Step 2: Replace inline whitelist in `export_roles_csv`**

Find the analogous block in `export_roles_csv` (around lines 330-340):

```python
    excluded_models = [
        'retakerecord', 'retakerecorddetail', 'messagereadstatus', 'messagetrashstatus', 
        'messageunreadstatus', 'msteams', 'scormpackage', 'studentprogress', 'day', 'section',
    ]
    
    all_permissions = Permission.objects.filter(
        content_type__app_label__in=[
            'accounts', 'subject', 'course', 'activity', 'module', 'message', 'gradebookcomponent', 
            'studentgrade', 'roles', 'attendance', 'classroom', 'logs'
        ]
    ).exclude(content_type__model__in=excluded_models)
```

Replace with:

```python
    all_permissions = get_all_categorized_permissions()
```

- [ ] **Step 3: Leave `download_roles_template` alone**

The `download_roles_template` view uses a hand-written `permission_patterns` list to emit column headers — it has no whitelist and doesn't need changes here. Verify by reading its code and confirming `Permission.objects.filter` doesn't appear.

- [ ] **Step 4: Manual smoke test CSV export**

Run the dev server and confirm the export still contains every permission you'd expect (IT Admin visits `/export_roles_csv/`):

```bash
python manage.py runserver
# Then in browser, log in as IT Admin and GET /export_roles_csv/
# Verify the downloaded file includes columns for every category's permissions.
```

Or scripted:

```bash
python manage.py shell -c "
from django.test import Client
from django.contrib.auth import get_user_model
from accounts.models.account_models import Profile
from roles.models import Role
# Use an existing IT Admin user — or skip if unsure
user = get_user_model().objects.filter(is_superuser=True).first()
if not user:
    print('No superuser to test with — skip manual smoke')
else:
    c = Client()
    c.force_login(user)
    r = c.get('/export_roles_csv/')
    print('status', r.status_code, 'bytes', len(r.content))
"
```

Expected: status 200, content > 1000 bytes with `Can view customuser`, `Can view gradebookcomponents` etc. in the header row.

- [ ] **Step 5: Run full roles test suite to check nothing broke**

```bash
python manage.py test roles --keepdb -v 2
```

Expected: all existing Phase 1/2 tests + new test_categorization tests PASS.

- [ ] **Step 6: Commit**

```bash
git add roles/views.py
git commit -m "refactor(roles): CSV views use get_all_categorized_permissions helper"
```

---

## Task 7: Rewrite `addRole.html` with grouped collapsible picker

**Files:**
- Modify: `roles/templates/role/addRole.html`

- [ ] **Step 1: Replace the flat permissions table**

Find the block from `<div class="form-group"><label for="permissions">Permissions:</label>` through `</table>` and `</div>` (lines ~148-199 in current file). Replace with:

```html
                <div class="form-group">
                    <label for="permissions">Permissions:</label>
                    <div>
                        <input type="checkbox" id="checkAll"> Check All
                    </div>

                    {% for category, perms in categorized_permissions %}
                        <details class="perm-category" open>
                            <summary>
                                <label class="cat-select-label">
                                    <input type="checkbox"
                                           class="select-all-category"
                                           data-cat-index="{{ forloop.counter }}">
                                    <strong>{{ category }}</strong>
                                    <span class="cat-count">({{ perms|length }})</span>
                                </label>
                            </summary>
                            <table class="table table-bordered perm-table">
                                <thead>
                                    <tr>
                                        <th>Permission</th>
                                        <th>Grant</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for perm in perms %}
                                        <tr>
                                            <td>{{ perm.name }}</td>
                                            <td>
                                                <input type="checkbox"
                                                       name="permissions"
                                                       class="permission-checkbox cat-{{ forloop.parentloop.counter }}"
                                                       value="{{ perm.id }}">
                                            </td>
                                        </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </details>
                    {% endfor %}
                </div>
```

- [ ] **Step 2: Update the inline JS for per-category select-all**

Find the existing `<script>` block with `checkAll` logic (bottom of the file). Replace both script blocks with:

```html
<script>
    // Global "Check All" — unchanged semantics.
    document.getElementById('checkAll').addEventListener('change', function () {
        document.querySelectorAll('.permission-checkbox').forEach(cb => {
            cb.checked = this.checked;
        });
    });

    // Per-category "Select all in this category".
    document.querySelectorAll('.select-all-category').forEach(master => {
        master.addEventListener('change', function (ev) {
            ev.stopPropagation(); // don't toggle the <details> open/close
            const cat = this.dataset.catIndex;
            document.querySelectorAll('.cat-' + cat).forEach(cb => {
                cb.checked = this.checked;
            });
        });
    });

    // Clicking the summary toggles collapse; clicking the master checkbox or
    // its label should NOT toggle. Handled via stopPropagation on change AND
    // a click guard on the label itself.
    document.querySelectorAll('.cat-select-label').forEach(label => {
        label.addEventListener('click', function (ev) {
            // Let the checkbox receive the click naturally; prevent summary toggle.
            ev.stopPropagation();
        });
    });

    // Source-role permission copy — unchanged, just targets .permission-checkbox.
    document.getElementById('source_role_id').addEventListener('change', function () {
        const roleId = this.value;
        if (!roleId) {
            document.querySelectorAll('.permission-checkbox').forEach(cb => cb.checked = false);
            return;
        }
        fetch(`/get_role_permissions/${roleId}/`)
            .then(r => r.json())
            .then(data => {
                document.querySelectorAll('.permission-checkbox').forEach(cb => cb.checked = false);
                data.permissions.forEach(p => {
                    const cb = document.querySelector(`input[value="${p.id}"]`);
                    if (cb) cb.checked = true;
                });
            })
            .catch(() => {});
    });
</script>
```

- [ ] **Step 3: Add minimal CSS for the category styling**

Inside the existing `<style>` block at the top, append:

```css
        .perm-category {
            margin-bottom: 12px;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            padding: 4px 8px;
        }
        .perm-category > summary {
            cursor: pointer;
            padding: 6px 4px;
            user-select: none;
        }
        .cat-select-label {
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .cat-count {
            color: #888;
            font-weight: normal;
            font-size: 0.9em;
        }
        .perm-table {
            margin-top: 6px;
            margin-bottom: 0;
        }
```

- [ ] **Step 4: Django sanity check**

```bash
python manage.py check
```

Expected: no issues.

- [ ] **Step 5: Manual browser smoke test**

```bash
python manage.py runserver
```

Log in as IT Admin, visit `/roleList/`, click "Add Role", verify:
1. The modal opens.
2. Each category renders as an open `<details>` section.
3. Clicking a category header collapses/expands it.
4. Ticking a per-category master checkbox ticks every checkbox in that category.
5. Ticking the global "Check All" ticks everything everywhere.
6. Selecting a source role from the copy dropdown updates the right checkboxes.

- [ ] **Step 6: Commit**

```bash
git add roles/templates/role/addRole.html
git commit -m "feat(roles): grouped collapsible picker in addRole.html with per-section select-all"
```

---

## Task 8: Apply same structure to `updateRole.html` and `viewRole.html`

**Files:**
- Modify: `roles/templates/role/updateRole.html`
- Modify: `roles/templates/role/viewRole.html`

- [ ] **Step 1: Read current `updateRole.html`**

```bash
wc -l ~/classedge/roles/templates/role/updateRole.html
```

Note where the permissions table is.

- [ ] **Step 2: Replace the flat table in `updateRole.html` with the grouped structure**

Same structure as Task 7 Step 1, but each checkbox needs the preselected-state logic. Replace the permissions table with:

```html
                <div class="form-group">
                    <label for="permissions">Permissions:</label>
                    <div>
                        <input type="checkbox" id="checkAll"> Check All
                    </div>

                    {% for category, perms in categorized_permissions %}
                        <details class="perm-category" open>
                            <summary>
                                <label class="cat-select-label">
                                    <input type="checkbox"
                                           class="select-all-category"
                                           data-cat-index="{{ forloop.counter }}">
                                    <strong>{{ category }}</strong>
                                    <span class="cat-count">({{ perms|length }})</span>
                                </label>
                            </summary>
                            <table class="table table-bordered perm-table">
                                <thead>
                                    <tr>
                                        <th>Permission</th>
                                        <th>Grant</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for perm in perms %}
                                        <tr>
                                            <td>{{ perm.name }}</td>
                                            <td>
                                                <input type="checkbox"
                                                       name="permissions"
                                                       class="permission-checkbox cat-{{ forloop.parentloop.counter }}"
                                                       value="{{ perm.id }}"
                                                       {% if perm in role.permissions.all %}checked{% endif %}>
                                            </td>
                                        </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </details>
                    {% endfor %}
                </div>
```

Use the same `<style>` CSS block additions from Task 7 Step 3 (copy verbatim into `updateRole.html`'s `<style>` block).

Use the same `<script>` block from Task 7 Step 2 — **minus** the `source_role_id` copy logic (update doesn't have a source-role dropdown). Copy verbatim, deleting only the `source_role_id` event listener.

- [ ] **Step 3: Replace the flat table in `viewRole.html` (read-only)**

`viewRole.html` has no form — it just displays the current state. Read it first to find where permissions render.

Replace the permission-display section with:

```html
<div class="form-group">
    <label>Permissions for {{ role.name }}:</label>
    {% for category, perms in categorized_permissions %}
        <details class="perm-category" open>
            <summary>
                <strong>{{ category }}</strong>
                <span class="cat-count">({{ perms|length }})</span>
            </summary>
            <table class="table table-bordered perm-table">
                <thead>
                    <tr>
                        <th>Permission</th>
                        <th>Granted</th>
                    </tr>
                </thead>
                <tbody>
                    {% for perm in perms %}
                        <tr>
                            <td>{{ perm.name }}</td>
                            <td>
                                <input type="checkbox" disabled
                                       {% if perm in role.permissions.all %}checked{% endif %}>
                            </td>
                        </tr>
                    {% endfor %}
                </tbody>
            </table>
        </details>
    {% endfor %}
</div>
```

Add the same CSS block from Task 7 Step 3. No JS needed (read-only, no select-all).

- [ ] **Step 4: Django sanity check**

```bash
python manage.py check
```

- [ ] **Step 5: Manual browser smoke test**

With dev server running:
- Visit `/updateRole/<id>/` for an existing role — verify correct checkboxes are pre-checked and the collapse/per-section-select-all work.
- Visit `/viewRole/<id>/` — verify checkboxes are disabled and reflect current permission state.

- [ ] **Step 6: Commit**

```bash
git add roles/templates/role/updateRole.html roles/templates/role/viewRole.html
git commit -m "feat(roles): grouped picker in updateRole.html + viewRole.html"
```

---

## Task 9: Picker rendering tests

**Files:**
- Create: `roles/tests/test_picker_rendering.py`

- [ ] **Step 1: Write the picker rendering tests**

Contents of `roles/tests/test_picker_rendering.py`:

```python
"""[Classedge LMS] Tests that the role CRUD templates render the grouped
picker with the right content and pre-selected state."""
from django.test import Client, TestCase
from django.urls import reverse

from roles.models import Role
from roles.permission_categories import CATEGORY_ORDER, PERMISSION_CATEGORIES
from roles.tests.helpers import make_it_admin


class PickerRenderingTests(TestCase):
    def setUp(self):
        self.admin = make_it_admin(username="picker_admin")
        self.client = Client()
        self.client.force_login(self.admin)

    def test_add_role_modal_renders_all_categories_in_order(self):
        """GET /roleList/ includes each category header; categories appear in CATEGORY_ORDER."""
        resp = self.client.get(reverse("roleList"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        positions = []
        for category in CATEGORY_ORDER:
            idx = html.find(category)
            self.assertNotEqual(idx, -1, f"Category {category!r} not rendered")
            positions.append(idx)
        self.assertEqual(
            positions, sorted(positions),
            "Categories rendered out of CATEGORY_ORDER",
        )

    def test_update_role_preselects_current_permissions(self):
        """Existing permissions appear as checked="" in the HTML."""
        from django.contrib.auth.models import Permission
        role = Role.objects.create(name="PickerTest")
        # Assign the first permission from each of 2 categories.
        some_codename_strs = (
            PERMISSION_CATEGORIES["Messaging"][:1]
            + PERMISSION_CATEGORIES["Gradebook"][:1]
        )
        perms_to_assign = []
        for s in some_codename_strs:
            app, code = s.split(".", 1)
            perms_to_assign.append(
                Permission.objects.get(content_type__app_label=app, codename=code)
            )
        role.permissions.set(perms_to_assign)

        resp = self.client.get(reverse("updateRole", args=[role.pk]))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        for p in perms_to_assign:
            # A checked permissions input carries value="<perm.id>" and is checked.
            marker = f'value="{p.id}"\n                                                       checked'
            # Template may render differently; fall back to a looser check.
            self.assertIn(f'value="{p.id}"', html)
            # Look for 'checked' anywhere in the 200 chars around the value attr.
            vloc = html.find(f'value="{p.id}"')
            window = html[max(0, vloc - 200):vloc + 200]
            self.assertIn("checked", window, f"perm {p.codename} not pre-checked")

    def test_picker_hides_django_internal_permissions(self):
        """Permissions like auth.session, admin logentries, etc. don't leak
        into the picker."""
        resp = self.client.get(reverse("roleList"))
        html = resp.content.decode()
        forbidden_codenames = [
            "add_session",
            "change_session",
            "add_logentry",
            "view_logentry",
            "add_contenttype",
            "add_group",  # auth.group — not in our categories
        ]
        for code in forbidden_codenames:
            self.assertNotIn(
                f'value="', html_for_code := html,  # noqa: F841
            )
            self.assertNotIn(
                code, html, f"Unexpected Django-internal permission leaked: {code}"
            )
```

(If the `view_logentry` string happens to appear in a non-checkbox context in the rendered HTML, replace that codename with one that truly shouldn't appear — e.g., `add_permission`.)

- [ ] **Step 2: Run the tests**

```bash
source ~/classedge/env/bin/activate
python manage.py test roles.tests.test_picker_rendering --keepdb -v 2
```

Expected: all three tests PASS.

- [ ] **Step 3: Commit**

```bash
git add roles/tests/test_picker_rendering.py
git commit -m "test(roles): picker rendering tests (ordering, preselection, no-leak)"
```

---

## Task 10: Filter `candidate_heads` by role name

**Files:**
- Modify: `accounts/views/department_admin.py`

- [ ] **Step 1: Write the dept-head filter test**

Create or append to `roles/tests/test_auth_smoke.py` (we'll expand this file in Task 11; starting it here):

```python
"""[Classedge LMS] End-to-end smoke tests for the auth surface Phase 3 touches."""
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models.department_models import Department
from roles.tests.helpers import make_it_admin, make_user_with_role


class DepartmentHeadDropdownTests(TestCase):
    def setUp(self):
        self.admin = make_it_admin(username="dept_head_admin")
        self.program_head = make_user_with_role(
            "ph_user", "Program Head", grant_phase2=False,
        )
        self.teacher = make_user_with_role(
            "t_user", "Teacher", grant_phase2=False,
        )
        self.dept = Department.objects.create(name="Test Dept")
        self.client = Client()
        self.client.force_login(self.admin)

    def test_candidate_heads_dropdown_excludes_teachers(self):
        """The department-settings page should only list Program Head (and
        eventually Principal) users in the candidate_heads dropdown."""
        resp = self.client.get(
            reverse("department_settings", args=[self.dept.pk])
        )
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn(self.program_head.username, html)
        self.assertNotIn(self.teacher.username, html)

    def test_candidate_heads_dropdown_includes_principal_when_role_exists(self):
        """Principal role is already listed in DEPARTMENT_HEAD_ROLE_NAMES;
        creating a Principal user should surface them in the dropdown."""
        principal = make_user_with_role(
            "principal_user", "Principal", grant_phase2=False,
        )
        resp = self.client.get(
            reverse("department_settings", args=[self.dept.pk])
        )
        html = resp.content.decode()
        self.assertIn(principal.username, html)
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
python manage.py test roles.tests.test_auth_smoke.DepartmentHeadDropdownTests --keepdb -v 2
```

Expected: `test_candidate_heads_dropdown_excludes_teachers` FAILS (teacher currently appears because filter is unrestricted). Other test likely also fails.

- [ ] **Step 3: Update `accounts/views/department_admin.py:64`**

Find the `candidate_heads` line (~line 64):

```python
    candidate_heads = CustomUser.objects.filter(is_active=True).order_by("username")
```

Replace with:

```python
    from roles.constants import DEPARTMENT_HEAD_ROLE_NAMES
    candidate_heads = (
        CustomUser.objects
        .filter(is_active=True, profile__role__name__in=DEPARTMENT_HEAD_ROLE_NAMES)
        .order_by("username")
    )
```

(Prefer a top-of-file import in practice — but keep the import local if it avoids a circular import risk with `roles`. Verify by running `python manage.py check`.)

- [ ] **Step 4: Re-run the tests**

```bash
python manage.py test roles.tests.test_auth_smoke.DepartmentHeadDropdownTests --keepdb -v 2
```

Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add accounts/views/department_admin.py roles/tests/test_auth_smoke.py
git commit -m "feat(accounts): filter candidate_heads to DEPARTMENT_HEAD_ROLE_NAMES"
```

---

## Task 11: Auth smoke tests (register, login, role CRUD)

**Files:**
- Modify: `roles/tests/test_auth_smoke.py`

- [ ] **Step 1: Append the register/login + role CRUD smoke tests**

Append to `roles/tests/test_auth_smoke.py`:

```python
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from roles.models import Role


User = get_user_model()


class AuthFlowSmokeTests(TestCase):
    def test_login_logout_roundtrip(self):
        """IT Admin logs in via the login URL, hits a protected page, logs out."""
        admin = make_it_admin(username="login_admin")
        c = Client()
        # Use Django's test-client login which wraps the auth backend.
        ok = c.login(username="login_admin", password="Test@1234")
        self.assertTrue(ok, "IT Admin could not log in")
        protected = c.get(reverse("roleList"))
        self.assertEqual(protected.status_code, 200)
        c.logout()
        after_logout = c.get(reverse("roleList"))
        # Protected view should redirect to login after logout.
        self.assertIn(after_logout.status_code, (301, 302))


class RoleCRUDSmokeTests(TestCase):
    def setUp(self):
        self.admin = make_it_admin(username="crud_admin")
        self.client = Client()
        self.client.force_login(self.admin)

    def test_create_update_view_delete_role_roundtrip(self):
        # CREATE
        some_perm = Permission.objects.filter(codename="view_customuser").first()
        self.assertIsNotNone(some_perm)
        resp = self.client.post(
            reverse("createRole"),
            {"name": "SmokeRole", "permissions": [some_perm.id]},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        role = Role.objects.get(name="SmokeRole")
        self.assertIn(some_perm, role.permissions.all())

        # UPDATE — add a second permission
        other_perm = Permission.objects.filter(codename="add_customuser").first()
        self.assertIsNotNone(other_perm)
        resp = self.client.post(
            reverse("updateRole", args=[role.pk]),
            {"name": "SmokeRole", "permissions": [some_perm.id, other_perm.id]},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        role.refresh_from_db()
        self.assertSetEqual(
            set(role.permissions.values_list("id", flat=True)),
            {some_perm.id, other_perm.id},
        )

        # VIEW
        resp = self.client.get(reverse("viewRole", args=[role.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "SmokeRole")

        # DELETE
        resp = self.client.post(reverse("deleteRole", args=[role.pk]), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Role.objects.filter(pk=role.pk).exists())
```

- [ ] **Step 2: Run the full smoke file**

```bash
python manage.py test roles.tests.test_auth_smoke --keepdb -v 2
```

Expected: all tests PASS (including the two dept-head tests from Task 10).

- [ ] **Step 3: Run the entire roles test suite**

```bash
python manage.py test roles accounts --keepdb -v 2
```

Expected: every test (Phase 1 + Phase 2 + Phase 3) PASSES.

- [ ] **Step 4: Commit**

```bash
git add roles/tests/test_auth_smoke.py
git commit -m "test(roles): auth smoke tests — login/logout + role CRUD roundtrip"
```

---

## Task 12: Manual QA and final verification

**Files:** (no code changes — verification only)

- [ ] **Step 1: Fresh test DB sanity run**

If time permits and no one else is using the shared Neon test DB, do one fresh run **without** `--keepdb` to flush any stale state:

```bash
python manage.py test roles accounts -v 2
```

Expected: all tests PASS, takes ~5-7 min.

If someone else is using the DB (you'll see `database "test_neondb" is being accessed by other users`), skip this step — `--keepdb` runs already validated correctness.

- [ ] **Step 2: Dev-server manual QA checklist**

Start the dev server and walk through every role-picker surface:

```bash
python manage.py runserver
```

1. **Log in as IT Admin**, visit `/dashboard/` — should redirect to `/it-admin/`.
2. From the IT Admin sidebar, click **Roles** → should land on `/roleList/`.
3. Click **Add Role**:
   - [ ] Modal opens.
   - [ ] All 12 categories appear in `CATEGORY_ORDER`, each rendered as an open `<details>` section with a `(N)` perm count.
   - [ ] Per-category master checkbox toggles every checkbox in that category.
   - [ ] Global "Check All" toggles everything.
   - [ ] Clicking the summary (category header) collapses/expands the section.
   - [ ] Selecting a source role from "Copy Permissions From" correctly pre-ticks the target role's perms.
   - [ ] Submit → role appears in list.
4. Click **edit** on an existing role:
   - [ ] updateRole page loads.
   - [ ] Currently-granted permissions are pre-checked.
   - [ ] Changes save and persist (refresh the page to confirm).
5. Click **view** on a role:
   - [ ] viewRole page loads.
   - [ ] All checkboxes are disabled.
   - [ ] Granted permissions appear checked, others unchecked.
6. Visit `/departments/` (IT Admin sidebar → Departments if available, or hit `/departments/<dept_id>/settings/` directly):
   - [ ] The "Head" dropdown contains only Program Head users.
   - [ ] No teachers, students, or registrars in the dropdown.

- [ ] **Step 3: CSV import/export sanity check**

Visit `/export_roles_csv/` and confirm the downloaded CSV header row contains columns for categorized permissions (e.g. `Can view customuser`, `Can add gradebookcomponents`) and does NOT contain `Can add session`, `Can add logentry`, etc.

- [ ] **Step 4: Push the branch**

```bash
git push personal feat/permission-categorization-phase3
```

- [ ] **Step 5: Open PR to `personal/main`**

```bash
gh pr create --base main --head feat/permission-categorization-phase3 \
  --title "Phase 3: permission categorization + role-picker UI polish" \
  --body "$(cat <<'EOF'
## Summary
- Introduces `roles/permission_categories.py` as the single source of truth for what permissions the role picker shows and how they're grouped.
- Role CRUD picker now renders as 12 collapsible functional categories with per-section select-all.
- `candidate_heads` dropdown on the department-settings page now filters to users whose role is `Program Head` or `Principal`.
- Deletes 5 duplicated app_label whitelist blocks from `roles/views.py` (including pre-existing typos like `'gradebookcomponent','logs'` concatenated into one string).
- CI guard test_categorization fails if any Classedge-owned-app permission is missing from PERMISSION_CATEGORIES.

## Test plan
- [ ] CI green (roles + accounts suites + new Phase 3 tests)
- [ ] Manual QA of role CRUD on dev server
- [ ] CSV export sanity
- [ ] Dept-head dropdown filters correctly

Closes Phase 3 of the 2026-04-22 auth refactor plan. No schema or data migration.
EOF
)"
```

- [ ] **Step 6: Merge and update memory**

After review + merge:

```bash
git checkout main
git pull personal main
```

Update `project_classedge_it_admin_refactor.md` to move Phase 3 from "NOT STARTED" to "MERGED YYYY-MM-DD" with the merge-commit SHA.

---

## Self-review checklist

Completed before handoff:

- **Spec coverage:** Every section of the spec has a task. Categorization decision → Task 3. Helper functions → Task 4. View refactor → Tasks 5 + 6. Template rewrite → Tasks 7 + 8. Dept-head filter → Task 10. CI guard → Task 2. Auth smoke → Task 11.
- **Placeholder scan:** No TBDs, TODOs, "similar to task N" references without repeating the code, or "add appropriate error handling" hand-waves.
- **Type consistency:** `PERMISSION_CATEGORIES: dict[str, list[str]]`, helper returns `list[tuple[str, list[Permission]]]` and `QuerySet[Permission]` — consistent across tasks.
- **Scope:** One PR, one plan, ~2 days. Consistent with memory's Phase 3 estimate.
- **Correction noted:** Spec lists `studentgrade` under Gradebook — this model doesn't exist. Plan's Task 3 Step 3 drops it from the Gradebook category and documents the correction in the preamble.
