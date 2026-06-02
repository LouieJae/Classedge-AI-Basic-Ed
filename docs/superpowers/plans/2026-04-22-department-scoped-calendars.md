# Department-Scoped Calendars Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give each Department its own term dates and let it optionally scope calendar Events, Holidays, and Announcements to its own members, with a department-head admin UI and calendar-API filtering.

**Architecture:** Add `Department.head` + `Department.cadence`; attach `Semester.department` and nullable `department` FKs to `Holiday`/`Event`/`Announcement`; enforce term-window integrity via `Term.clean()`; gate department-head views with a new `authorize_department_head` helper; filter `calendar_api` output by a `visible_department_ids` service. Ship a data migration that backfills a "General" Department so existing Semesters stop being orphans.

**Tech Stack:** Django 5, PostgreSQL (neondb), Django templates + HTMX for the head/admin UI, DRF for calendar API. Label every new function/view with `[Classedge LMS]`.

---

## File Structure

### New files (create)

| Path | Responsibility |
|---|---|
| `accounts/services/__init__.py` | Package marker (create only if missing) |
| `accounts/services/department_access.py` | `authorize_department_head(user, department)` helper |
| `accounts/views/department_admin.py` | All 9 department admin views (list / calendar / settings / semester+term CRUD / event+holiday create) |
| `accounts/context_processors.py` | `department_context(request)` exposing `headed_department` to templates |
| `accounts/templates/accounts/departments/department_list.html` | Admin list table |
| `accounts/templates/accounts/departments/department_calendar.html` | Head/admin 3-section landing page |
| `accounts/templates/accounts/departments/department_settings.html` | Head + cadence form |
| `accounts/templates/accounts/departments/_term_row.html` | HTMX fragment (read or edit mode) |
| `accounts/templates/accounts/departments/_semester_block.html` | HTMX fragment (semester + nested terms) |
| `accounts/tests/__init__.py` | Package marker (if missing) |
| `accounts/tests/helpers.py` | `make_department`, `make_semester`, `make_profile_for` |
| `accounts/tests/test_department_access.py` | `authorize_department_head` matrix |
| `accounts/tests/test_department_admin.py` | List/calendar/settings views |
| `accounts/tests/test_semester_term_crud.py` | Semester & term CRUD views |
| `accounts/tests/test_term_date_validation.py` | `Term.clean()` edge cases |
| `accounts/tests/test_department_migration.py` | "General" backfill migration |
| `accounts/tests/test_function_labels.py` | `[Classedge LMS]` label enforcement |
| `calendars/services/__init__.py` | Package marker |
| `calendars/services/department_filter.py` | `visible_department_ids(user)` |
| `calendars/tests/__init__.py` | Package marker (if missing) |
| `calendars/tests/test_department_filter.py` | `visible_department_ids` matrix |
| `calendars/tests/test_calendar_api_scoping.py` | `calendar_api` filters events per user |

### Modified files

| Path | Change |
|---|---|
| `accounts/models/department_models.py` | Add `head` FK + `cadence` CharField |
| `course/models/semester_model.py` | Add `department` FK |
| `course/models/term_model.py` | Add `clean()` method |
| `calendars/models.py` | Add `department` FK to `Holiday`, `Event`, `Announcement` |
| `accounts/urls.py` | Register 9 new URL patterns |
| `accounts/views/__init__.py` | Re-export department views |
| `classedge/settings.py` | Append `accounts.context_processors.department_context` to TEMPLATES[0]['OPTIONS']['context_processors'] |
| `calendars/views.py` | Import service, filter `Event`/`Holiday`/`Announcement` querysets in `calendar_api` |
| Admin base sidebar template (find via grep) | Add "Departments" link |
| `gamification/templates/.../teacher_base.html` (find via grep) | Add "My Department" shortcut |

### New migrations

| Migration | App | Purpose |
|---|---|---|
| `accounts/migrations/00NN_department_head_cadence.py` | accounts | Add Department.head + cadence |
| `course/migrations/00NN_semester_department.py` | course | Add Semester.department |
| `calendars/migrations/00NN_department_fk.py` | calendars | Add department FK to 3 models |
| `course/migrations/00NN_seed_general_department.py` | course | Data migration: create "General", attach orphan Semesters |

---

## Conventions used throughout this plan

- **Run tests with:** `cd ~/classedge && source env/bin/activate && python manage.py test <path> --keepdb -v 2`
- **Make migrations with:** `python manage.py makemigrations <app> -n <descriptive_name>`
- **Apply migrations with:** `python manage.py migrate`
- **Every new public function/view gets `[Classedge LMS]` in its docstring** (global convention — memory `feedback_classedge_function_labels`).
- **Commits are frequent and small** — one per task unless stated otherwise.
- **Preserve HTMX patterns** — server returns partial fragments; the client swaps them in. No JSON for admin CRUD (only for `calendar_api`).

---

## Task 1: Add `Department.head` + `Department.cadence`

**Files:**
- Modify: `accounts/models/department_models.py`
- Create migration: `accounts/migrations/00NN_department_head_cadence.py`

- [ ] **Step 1: Update the model**

Replace `accounts/models/department_models.py` with:

```python
from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=100)
    head = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_departments",
    )
    # [Classedge LMS] Single authoritative department head — Principal / Dean / Program Head.

    CADENCE_CHOICES = [
        ("semester", "Semester"),
        ("school_year", "School Year"),
        ("trimester", "Trimester"),
        ("quarter", "Quarter"),
    ]
    cadence = models.CharField(
        max_length=20, null=True, blank=True, choices=CADENCE_CHOICES,
    )
    # [Classedge LMS] Rhythm hint — drives term-name UI suggestions and future report grouping.

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
```

- [ ] **Step 2: Generate the migration**

Run: `cd ~/classedge && source env/bin/activate && python manage.py makemigrations accounts -n department_head_cadence`
Expected: creates `accounts/migrations/00NN_department_head_cadence.py` with two `AddField` operations.

- [ ] **Step 3: Apply the migration**

Run: `python manage.py migrate accounts`
Expected: `Applying accounts.00NN_department_head_cadence... OK`

- [ ] **Step 4: Smoke-check the shell**

Run: `python manage.py shell -c "from accounts.models.department_models import Department; d = Department.objects.first(); print(d, getattr(d, 'head_id', None), getattr(d, 'cadence', None))"`
Expected: prints the first department (or `None`) without error.

- [ ] **Step 5: Commit**

```bash
git add accounts/models/department_models.py accounts/migrations/
git commit -m "feat(accounts): add Department.head and Department.cadence fields"
```

---

## Task 2: `authorize_department_head` helper + tests

**Files:**
- Create: `accounts/services/__init__.py` (if missing)
- Create: `accounts/services/department_access.py`
- Create: `accounts/tests/__init__.py` (if missing)
- Create: `accounts/tests/helpers.py`
- Create: `accounts/tests/test_department_access.py`

- [ ] **Step 1: Write the failing test file first (TDD)**

Create `accounts/tests/helpers.py`:

```python
from accounts.models.department_models import Department
from accounts.models.account_models import CustomUser, Profile
from course.models.semester_model import Semester
from roles.models import Role


def make_department(name="Math", head=None, cadence="semester"):
    """[Classedge LMS] Create a Department for tests."""
    return Department.objects.create(name=name, head=head, cadence=cadence)


def make_semester(department, name="First Semester", start=None, end=None):
    """[Classedge LMS] Create a Semester owned by a department."""
    from datetime import date
    return Semester.objects.create(
        semester_name=name,
        start_date=start or date(2026, 6, 1),
        end_date=end or date(2026, 10, 31),
        department=department,
    )


def make_profile_for(user, role_name, department=None):
    """[Classedge LMS] Attach a Profile + Role (+ optional department_fields) to a user."""
    role, _ = Role.objects.get_or_create(name=role_name)
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.role = role
    profile.department_fields = department
    profile.save()
    return profile
```

> **Note:** If `Role` lives in a different module, grep for `class Role` under `roles/` and adjust the import. Same for `Profile`: if its canonical path differs, correct the import. Run `python manage.py shell -c "from accounts.models.account_models import Profile; from roles.models import Role"` to verify.

Create `accounts/tests/test_department_access.py`:

```python
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from accounts.models.account_models import CustomUser
from accounts.services.department_access import authorize_department_head
from accounts.tests.helpers import make_department, make_profile_for


class AuthorizeDepartmentHeadTests(TestCase):
    def setUp(self):
        self.dept = make_department(name="Math")
        self.head = CustomUser.objects.create_user(
            username="head", email="head@test.io", password="x",
        )
        self.dept.head = self.head
        self.dept.save()
        make_profile_for(self.head, "teacher")

    def test_superuser_allowed(self):
        su = CustomUser.objects.create_superuser(
            username="su", email="su@test.io", password="x",
        )
        make_profile_for(su, "admin")
        authorize_department_head(su, self.dept)  # no raise

    def test_admin_allowed(self):
        admin = CustomUser.objects.create_user(
            username="adm", email="adm@test.io", password="x",
        )
        make_profile_for(admin, "admin")
        authorize_department_head(admin, self.dept)

    def test_head_allowed(self):
        authorize_department_head(self.head, self.dept)

    def test_random_teacher_denied(self):
        other = CustomUser.objects.create_user(
            username="t2", email="t2@test.io", password="x",
        )
        make_profile_for(other, "teacher")
        with self.assertRaises(PermissionDenied):
            authorize_department_head(other, self.dept)
```

- [ ] **Step 2: Run the test, confirm it fails**

Run: `cd ~/classedge && source env/bin/activate && python manage.py test accounts.tests.test_department_access --keepdb -v 2`
Expected: FAIL with `ModuleNotFoundError: No module named 'accounts.services.department_access'`.

- [ ] **Step 3: Create the service package & module**

Create `accounts/services/__init__.py` if it does not already exist (empty file).

Create `accounts/services/department_access.py`:

```python
from django.core.exceptions import PermissionDenied


def authorize_department_head(user, department):
    """[Classedge LMS] Allow superusers, admins, or the department's head; else PermissionDenied."""
    if user.is_superuser:
        return
    role = getattr(getattr(user, "profile", None), "role", None)
    role_name = role.name.lower() if role else ""
    if role_name == "admin":
        return
    if department.head_id == user.id:
        return
    raise PermissionDenied("Not authorized for this department.")
```

- [ ] **Step 4: Run the test, confirm it passes**

Run: `python manage.py test accounts.tests.test_department_access --keepdb -v 2`
Expected: `OK` with 4 passing tests.

- [ ] **Step 5: Commit**

```bash
git add accounts/services/ accounts/tests/__init__.py accounts/tests/helpers.py accounts/tests/test_department_access.py
git commit -m "feat(accounts): add authorize_department_head helper and tests"
```

---

## Task 3: Add `Semester.department` field

**Files:**
- Modify: `course/models/semester_model.py`
- Create migration: `course/migrations/00NN_semester_department.py`

- [ ] **Step 1: Add the field**

Open `course/models/semester_model.py` and add the FK after `create_at`:

```python
    create_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    department = models.ForeignKey(
        "accounts.Department",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="semesters",
    )
    # [Classedge LMS] Department that owns this semester's dates. Nullable to tolerate
    # legacy rows; backfilled to "General" in a follow-up data migration and tightened
    # to null=False later.
```

- [ ] **Step 2: Generate + apply migration**

Run: `python manage.py makemigrations course -n semester_department && python manage.py migrate course`
Expected: migration created + applied OK.

- [ ] **Step 3: Shell smoke**

Run: `python manage.py shell -c "from course.models.semester_model import Semester; s = Semester.objects.first(); print(s, getattr(s, 'department_id', None))"`
Expected: prints a Semester (or None) with `department_id = None`.

- [ ] **Step 4: Commit**

```bash
git add course/models/semester_model.py course/migrations/
git commit -m "feat(course): add Semester.department FK"
```

---

## Task 4: Add `department` FK to `Holiday`, `Event`, `Announcement`

**Files:**
- Modify: `calendars/models.py`
- Create migration: `calendars/migrations/00NN_department_fk.py`

- [ ] **Step 1: Edit the models**

In `calendars/models.py`, add `department` to **each** of `Holiday`, `Event`, `Announcement`:

```python
    department = models.ForeignKey(
        "accounts.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)ss",
    )
    # [Classedge LMS] Null => institution-wide (visible to all).
    # Non-null => scoped to members of that department only.
```

- [ ] **Step 2: Generate + apply migration**

Run: `python manage.py makemigrations calendars -n department_fk && python manage.py migrate calendars`
Expected: 3 `AddField` operations, applied OK.

- [ ] **Step 3: Smoke check**

Run: `python manage.py shell -c "from calendars.models import Event, Holiday, Announcement; print(Event._meta.get_field('department'), Holiday._meta.get_field('department'), Announcement._meta.get_field('department'))"`
Expected: three ForeignKey repr lines printed, no error.

- [ ] **Step 4: Commit**

```bash
git add calendars/models.py calendars/migrations/
git commit -m "feat(calendars): scope Event/Holiday/Announcement to Department (nullable)"
```

---

## Task 5: `Term.clean()` validator + tests

**Files:**
- Modify: `course/models/term_model.py`
- Create: `accounts/tests/test_term_date_validation.py`

- [ ] **Step 1: Write the failing tests first**

Create `accounts/tests/test_term_date_validation.py`:

```python
from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.tests.helpers import make_department, make_semester
from course.models.term_model import Term


class TermCleanTests(TestCase):
    def setUp(self):
        self.dept = make_department()
        self.sem = make_semester(
            self.dept,
            name="First Semester",
            start=date(2026, 6, 1),
            end=date(2026, 10, 31),
        )

    def _term(self, start, end):
        return Term(
            term_name="Prelim",
            semester=self.sem,
            start_date=start,
            end_date=end,
        )

    def test_in_range_passes(self):
        self._term(date(2026, 6, 15), date(2026, 7, 15)).full_clean()

    def test_start_before_semester_start_rejects(self):
        with self.assertRaisesMessage(ValidationError, "before semester start_date"):
            self._term(date(2026, 5, 31), date(2026, 7, 15)).full_clean()

    def test_end_after_semester_end_rejects(self):
        with self.assertRaisesMessage(ValidationError, "after semester end_date"):
            self._term(date(2026, 6, 15), date(2026, 11, 15)).full_clean()

    def test_end_before_start_rejects(self):
        with self.assertRaisesMessage(ValidationError, "before start_date"):
            self._term(date(2026, 7, 15), date(2026, 7, 1)).full_clean()

    def test_missing_dates_ok(self):
        self._term(None, None).full_clean()
```

- [ ] **Step 2: Run tests — expect failures (no `clean`)**

Run: `python manage.py test accounts.tests.test_term_date_validation --keepdb -v 2`
Expected: the three "rejects" tests fail (no ValidationError raised). `test_in_range_passes` and `test_missing_dates_ok` pass.

- [ ] **Step 3: Add `clean()` to `Term`**

Edit `course/models/term_model.py`:

```python
from django.core.exceptions import ValidationError
from django.db import models


class Term(models.Model):
    TERM_CHOICES = [
        ('Prelim', 'Prelim'),
        ('Midterm', 'Midterm'),
        ('Pre-Final', 'Pre-Final'),
        ('Final Term', 'Final Term'),
    ]

    term_name = models.CharField(max_length=50, choices=TERM_CHOICES)
    semester = models.ForeignKey('course.Semester', on_delete=models.PROTECT, null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, null=True, blank=True)

    def clean(self):
        """[Classedge LMS] Ensure Term dates fall within the Semester window when set."""
        if not self.semester_id:
            return
        sem = self.semester
        if self.start_date and sem.start_date and self.start_date < sem.start_date:
            raise ValidationError("Term start_date is before semester start_date.")
        if self.end_date and sem.end_date and self.end_date > sem.end_date:
            raise ValidationError("Term end_date is after semester end_date.")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError("Term end_date is before start_date.")

    def __str__(self):
        return f"{self.term_name} - {self.start_date} - {self.end_date}"
```

- [ ] **Step 4: Run tests — expect all pass**

Run: `python manage.py test accounts.tests.test_term_date_validation --keepdb -v 2`
Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add course/models/term_model.py accounts/tests/test_term_date_validation.py
git commit -m "feat(course): validate Term dates fall within parent Semester window"
```

---

## Task 6: Data migration seeding the "General" Department

**Files:**
- Create migration: `course/migrations/00NN_seed_general_department.py`
- Create: `accounts/tests/test_department_migration.py`

- [ ] **Step 1: Identify exact migration dependency filenames**

Run: `ls course/migrations/ | tail -3; ls accounts/migrations/ | tail -3`
Record the latest `course` migration (the one from Task 3, e.g. `0007_semester_department.py`) and latest `accounts` migration (from Task 1). You'll reference them as `("course", "0007_semester_department")` etc.

- [ ] **Step 2: Create an empty migration file**

Run: `python manage.py makemigrations course -n seed_general_department --empty`
Expected: new empty migration file in `course/migrations/`.

- [ ] **Step 3: Fill the migration**

Replace its body with (keep the auto-generated `dependencies` list if present; add the accounts dependency):

```python
from django.db import migrations


def seed_general_department(apps, schema_editor):
    """[Classedge LMS] Backfill: attach all orphan Semesters to a 'General' Department."""
    Department = apps.get_model("accounts", "Department")
    Semester = apps.get_model("course", "Semester")
    general, _ = Department.objects.get_or_create(
        name="General", defaults={"cadence": None},
    )
    Semester.objects.filter(department__isnull=True).update(department=general)


def unseed(apps, schema_editor):
    """[Classedge LMS] Reverse: unlink; keep the Department row for safety."""
    Department = apps.get_model("accounts", "Department")
    Semester = apps.get_model("course", "Semester")
    general = Department.objects.filter(name="General").first()
    if general:
        Semester.objects.filter(department=general).update(department=None)


class Migration(migrations.Migration):
    dependencies = [
        ("course", "<filename-from-task-3-without-.py>"),
        ("accounts", "<filename-from-task-1-without-.py>"),
    ]
    operations = [migrations.RunPython(seed_general_department, unseed)]
```

- [ ] **Step 4: Apply and confirm idempotency**

```bash
python manage.py migrate
python manage.py migrate course 0000  # roll back (reverses unseed then schema down — stop at the new data migration)
# Then re-run:
python manage.py migrate
```

> **Shortcut:** Simpler — just `migrate`, then re-run `migrate` (no-op). If you prefer, verify idempotency inside the test in Step 5 instead of rolling back migrations.

Run: `python manage.py shell -c "from accounts.models.department_models import Department; from course.models.semester_model import Semester; print('General count:', Department.objects.filter(name='General').count()); print('Orphans:', Semester.objects.filter(department__isnull=True).count())"`
Expected: `General count: 1` and `Orphans: 0`.

- [ ] **Step 5: Write the migration test**

Create `accounts/tests/test_department_migration.py`:

```python
from django.test import TestCase

from accounts.models.department_models import Department
from course.models.semester_model import Semester


class SeedGeneralDepartmentTests(TestCase):
    """Post-migrate state: the fixture runs the data migration automatically."""

    def test_general_department_exists_exactly_once(self):
        self.assertEqual(Department.objects.filter(name="General").count(), 1)

    def test_no_orphan_semesters(self):
        self.assertEqual(Semester.objects.filter(department__isnull=True).count(), 0)
```

- [ ] **Step 6: Run the test**

Run: `python manage.py test accounts.tests.test_department_migration --keepdb -v 2`
Expected: 2 tests PASS (Django applies all migrations when the test DB is set up).

- [ ] **Step 7: Commit**

```bash
git add course/migrations/ accounts/tests/test_department_migration.py
git commit -m "feat(course): seed 'General' Department and backfill orphan Semesters"
```

---

## Task 7: `department_list` view + template + admin nav entry

**Files:**
- Create: `accounts/views/department_admin.py`
- Create: `accounts/templates/accounts/departments/department_list.html`
- Modify: `accounts/views/__init__.py`
- Modify: `accounts/urls.py`
- Modify: the admin base sidebar template (grep to find)
- Create: `accounts/tests/test_department_admin.py`

- [ ] **Step 1: Write the failing view test**

Create `accounts/tests/test_department_admin.py`:

```python
from django.test import TestCase
from django.urls import reverse

from accounts.models.account_models import CustomUser
from accounts.tests.helpers import make_department, make_profile_for


class DepartmentListViewTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username="adm", email="adm@test.io", password="x",
        )
        make_profile_for(self.admin, "admin")
        self.teacher = CustomUser.objects.create_user(
            username="t", email="t@test.io", password="x",
        )
        make_profile_for(self.teacher, "teacher")
        self.math = make_department(name="Math")

    def test_anonymous_denied(self):
        resp = self.client.get(reverse("department_list"))
        self.assertIn(resp.status_code, (302, 403))

    def test_teacher_denied(self):
        self.client.force_login(self.teacher)
        resp = self.client.get(reverse("department_list"))
        self.assertEqual(resp.status_code, 403)

    def test_admin_lists_departments(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("department_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Math")
```

- [ ] **Step 2: Run tests — expect reverse() failure (URL not registered)**

Run: `python manage.py test accounts.tests.test_department_admin --keepdb -v 2`
Expected: `NoReverseMatch: Reverse for 'department_list' not found`.

- [ ] **Step 3: Create the view module**

Create `accounts/views/department_admin.py`:

```python
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render

from accounts.models.department_models import Department
from roles.decorators import admin_required


@admin_required
def department_list(request):
    """[Classedge LMS] Admin list of all departments with head + cadence + term count."""
    departments = (
        Department.objects
        .select_related("head")
        .annotate(term_count=Count("semesters__term"))
        .order_by("name")
    )
    return render(
        request,
        "accounts/departments/department_list.html",
        {"departments": departments},
    )
```

> **Note:** If the reverse relation from `Semester` to `Term` is not named `term` (Django default: `<model>_set`), adjust `semesters__term` to `semesters__term_set` — the reverse accessor Django generates when no `related_name` is set. Verify by `python manage.py shell -c "from course.models.semester_model import Semester; print([f.name for f in Semester._meta.get_fields()])"`.

- [ ] **Step 4: Re-export from the views package**

In `accounts/views/__init__.py`, append:

```python
from accounts.views.department_admin import *  # noqa: F401,F403
```

- [ ] **Step 5: Create the template**

Create `accounts/templates/accounts/departments/department_list.html`:

```django
{% extends "layouts/admin_base.html" %}
{% load static %}

{% block title %}Departments{% endblock %}

{% block content %}
<style>
  .dept-page { background: #faf7f2; padding: 24px 32px; font-family: "Inter Tight", sans-serif; }
  .dept-page h1 { font-family: "Fraunces", serif; color: #1b4332; margin-bottom: 16px; }
  .dept-table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; }
  .dept-table th, .dept-table td { padding: 12px 16px; text-align: left; border-bottom: 1px solid #eee6d6; }
  .dept-table th { background: #1b4332; color: #faf7f2; font-weight: 600; }
  .dept-table a { color: #b7925a; text-decoration: none; font-weight: 600; }
  .dept-table a:hover { text-decoration: underline; }
  .muted { color: #2d3142; opacity: 0.6; }
</style>

<div class="dept-page">
  <h1>🏛️ Departments</h1>
  <table class="dept-table">
    <thead>
      <tr><th>Name</th><th>Head</th><th>Cadence</th><th># Terms</th><th></th></tr>
    </thead>
    <tbody>
      {% for d in departments %}
        <tr>
          <td>{{ d.name }}</td>
          <td>{% if d.head %}{{ d.head.get_full_name|default:d.head.username }}{% else %}<span class="muted">—</span>{% endif %}</td>
          <td>{{ d.get_cadence_display|default:"—" }}</td>
          <td>{{ d.term_count }}</td>
          <td>
            <a href="{% url 'department_calendar' d.id %}">Calendar</a> ·
            <a href="{% url 'department_settings' d.id %}">Settings</a>
          </td>
        </tr>
      {% empty %}
        <tr><td colspan="5" class="muted">No departments yet.</td></tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
```

> **Note on base template:** If the repo's admin layout lives at a different path than `layouts/admin_base.html`, grep for an existing admin page (`grep -rn "{% extends" accounts/templates/ | head`) and use whichever base extends work today.

- [ ] **Step 6: Register URLs**

Edit `accounts/urls.py` — add these imports and URL patterns (pattern block goes in `urlpatterns`):

```python
from accounts.views.department_admin import (
    department_list,
    department_calendar,
    department_settings,
    semester_create,
    semester_edit,
    term_create,
    term_edit,
    department_event_create,
    department_holiday_create,
)
```

Append to `urlpatterns`:

```python
    # [Classedge LMS] Department admin
    path("departments/", department_list, name="department_list"),
    path("departments/<int:dept_id>/calendar/", department_calendar, name="department_calendar"),
    path("departments/<int:dept_id>/settings/", department_settings, name="department_settings"),
    path("departments/<int:dept_id>/semesters/create/", semester_create, name="semester_create"),
    path("departments/<int:dept_id>/semesters/<int:sem_id>/edit/", semester_edit, name="semester_edit"),
    path("departments/<int:dept_id>/terms/create/", term_create, name="term_create"),
    path("departments/<int:dept_id>/terms/<int:term_id>/edit/", term_edit, name="term_edit"),
    path("departments/<int:dept_id>/events/create/", department_event_create, name="department_event_create"),
    path("departments/<int:dept_id>/holidays/create/", department_holiday_create, name="department_holiday_create"),
```

Since Tasks 8–11 implement the other views, define stubs right now so URL registration does not break. Append to `accounts/views/department_admin.py`:

```python
from django.http import HttpResponse


def _stub(request, *args, **kwargs):
    return HttpResponse("stub", status=501)


department_calendar = _stub
department_settings = _stub
semester_create = _stub
semester_edit = _stub
term_create = _stub
term_edit = _stub
department_event_create = _stub
department_holiday_create = _stub
```

These will be replaced one-by-one in later tasks.

- [ ] **Step 7: Run `department_list` tests — expect pass**

Run: `python manage.py test accounts.tests.test_department_admin.DepartmentListViewTests --keepdb -v 2`
Expected: 3 tests PASS.

- [ ] **Step 8: Add admin sidebar link**

Find the admin sidebar:

```bash
grep -rn "sidebar\|sidenav" accounts/templates/ registrar/templates/ layouts/ 2>/dev/null | grep -i admin | head
```

Open the matched admin base/sidebar template (likely `layouts/templates/layouts/admin_base.html` or similar) and insert, near other admin nav links:

```django
{# [Classedge LMS] Department admin #}
{% if request.user.is_superuser or request.user.profile.role.name|lower == "admin" %}
  <a href="{% url 'department_list' %}" class="sidebar-link">🏛️ Departments</a>
{% endif %}
```

Style to match adjacent nav entries.

- [ ] **Step 9: Commit**

```bash
git add accounts/views/department_admin.py accounts/views/__init__.py accounts/urls.py accounts/templates/accounts/departments/department_list.html accounts/tests/test_department_admin.py
git add <path-to-sidebar-template-you-edited>
git commit -m "feat(accounts): add department_list admin view + sidebar entry"
```

---

## Task 8: `department_settings` view + template

**Files:**
- Modify: `accounts/views/department_admin.py`
- Create: `accounts/templates/accounts/departments/department_settings.html`
- Modify: `accounts/tests/test_department_admin.py`

- [ ] **Step 1: Add test for settings view**

Append to `accounts/tests/test_department_admin.py`:

```python
class DepartmentSettingsViewTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username="adm2", email="adm2@test.io", password="x",
        )
        make_profile_for(self.admin, "admin")
        self.dept = make_department(name="Science")
        self.someone = CustomUser.objects.create_user(
            username="boss", email="boss@test.io", password="x",
        )
        make_profile_for(self.someone, "teacher")

    def test_admin_can_save_head_and_cadence(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("department_settings", args=[self.dept.id]),
            {"head": self.someone.id, "cadence": "trimester"},
        )
        self.assertIn(resp.status_code, (200, 302))
        self.dept.refresh_from_db()
        self.assertEqual(self.dept.head_id, self.someone.id)
        self.assertEqual(self.dept.cadence, "trimester")

    def test_teacher_denied(self):
        t = CustomUser.objects.create_user(username="t2", email="t2@x.io", password="x")
        make_profile_for(t, "teacher")
        self.client.force_login(t)
        resp = self.client.get(reverse("department_settings", args=[self.dept.id]))
        self.assertEqual(resp.status_code, 403)
```

- [ ] **Step 2: Run — expect 2 failures (stub returns 501)**

Run: `python manage.py test accounts.tests.test_department_admin.DepartmentSettingsViewTests --keepdb -v 2`

- [ ] **Step 3: Replace stub with real view**

In `accounts/views/department_admin.py`, remove `department_settings = _stub` and add:

```python
from django.shortcuts import get_object_or_404, redirect

from accounts.models.account_models import CustomUser
from accounts.models.department_models import Department


@admin_required
def department_settings(request, dept_id):
    """[Classedge LMS] Edit Department.head and Department.cadence."""
    dept = get_object_or_404(Department, pk=dept_id)
    if request.method == "POST":
        head_id = request.POST.get("head") or None
        cadence = request.POST.get("cadence") or None
        if cadence and cadence not in dict(Department.CADENCE_CHOICES):
            cadence = None
        dept.head = CustomUser.objects.filter(pk=head_id).first() if head_id else None
        dept.cadence = cadence
        dept.save()
        return redirect("department_list")
    candidate_heads = CustomUser.objects.filter(is_active=True).order_by("username")
    return render(
        request,
        "accounts/departments/department_settings.html",
        {"dept": dept, "candidate_heads": candidate_heads, "cadence_choices": Department.CADENCE_CHOICES},
    )
```

- [ ] **Step 4: Create the template**

Create `accounts/templates/accounts/departments/department_settings.html`:

```django
{% extends "layouts/admin_base.html" %}

{% block title %}{{ dept.name }} — Settings{% endblock %}

{% block content %}
<style>
  .settings-page { background: #faf7f2; padding: 24px 32px; font-family: "Inter Tight", sans-serif; max-width: 560px; }
  .settings-page h1 { font-family: "Fraunces", serif; color: #1b4332; }
  .settings-page label { display: block; margin-top: 12px; color: #2d3142; font-weight: 600; }
  .settings-page select { width: 100%; padding: 8px; border: 1px solid #e0d6c1; border-radius: 6px; background: #fff; }
  .settings-page button { margin-top: 16px; padding: 10px 18px; border: 0; border-radius: 6px; background: #1b4332; color: #faf7f2; font-weight: 600; cursor: pointer; }
</style>

<div class="settings-page">
  <h1>{{ dept.name }} — Settings</h1>
  <form method="post">
    {% csrf_token %}
    <label>Head
      <select name="head">
        <option value="">— Unassigned —</option>
        {% for u in candidate_heads %}
          <option value="{{ u.id }}" {% if dept.head_id == u.id %}selected{% endif %}>
            {{ u.get_full_name|default:u.username }}
          </option>
        {% endfor %}
      </select>
    </label>
    <label>Cadence
      <select name="cadence">
        <option value="">— Unset —</option>
        {% for value, label in cadence_choices %}
          <option value="{{ value }}" {% if dept.cadence == value %}selected{% endif %}>{{ label }}</option>
        {% endfor %}
      </select>
    </label>
    <button type="submit">Save</button>
  </form>
</div>
{% endblock %}
```

- [ ] **Step 5: Run tests — expect pass**

Run: `python manage.py test accounts.tests.test_department_admin.DepartmentSettingsViewTests --keepdb -v 2`

- [ ] **Step 6: Commit**

```bash
git add accounts/views/department_admin.py accounts/templates/accounts/departments/department_settings.html accounts/tests/test_department_admin.py
git commit -m "feat(accounts): add department_settings view to edit head + cadence"
```

---

## Task 9: `department_calendar` view + template + context processor + teacher_base shortcut

**Files:**
- Modify: `accounts/views/department_admin.py`
- Create: `accounts/context_processors.py`
- Modify: `classedge/settings.py`
- Create: `accounts/templates/accounts/departments/department_calendar.html`
- Modify: teacher_base.html (find via grep)
- Modify: `accounts/tests/test_department_admin.py`

- [ ] **Step 1: Add test**

Append to `accounts/tests/test_department_admin.py`:

```python
class DepartmentCalendarViewTests(TestCase):
    def setUp(self):
        self.head = CustomUser.objects.create_user(
            username="dh", email="dh@test.io", password="x",
        )
        make_profile_for(self.head, "teacher")
        self.dept = make_department(name="Math", head=self.head)
        self.other = CustomUser.objects.create_user(
            username="ot", email="ot@test.io", password="x",
        )
        make_profile_for(self.other, "teacher")

    def test_head_can_view(self):
        self.client.force_login(self.head)
        resp = self.client.get(reverse("department_calendar", args=[self.dept.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Math")

    def test_non_head_denied(self):
        self.client.force_login(self.other)
        resp = self.client.get(reverse("department_calendar", args=[self.dept.id]))
        self.assertEqual(resp.status_code, 403)
```

- [ ] **Step 2: Run — expect failures**

Run: `python manage.py test accounts.tests.test_department_admin.DepartmentCalendarViewTests --keepdb -v 2`

- [ ] **Step 3: Replace stub**

In `accounts/views/department_admin.py`, remove the `department_calendar = _stub` line and add:

```python
from accounts.services.department_access import authorize_department_head
from calendars.models import Event, Holiday
from course.models.semester_model import Semester


@login_required
def department_calendar(request, dept_id):
    """[Classedge LMS] Department head landing page — semesters, terms, events."""
    dept = get_object_or_404(Department, pk=dept_id)
    authorize_department_head(request.user, dept)
    semesters = (
        Semester.objects.filter(department=dept)
        .prefetch_related("term_set")
        .order_by("-start_date")
    )
    events = Event.objects.filter(department=dept).order_by("start_date")
    holidays = Holiday.objects.filter(department=dept).order_by("date")
    return render(
        request,
        "accounts/departments/department_calendar.html",
        {"dept": dept, "semesters": semesters, "events": events, "holidays": holidays},
    )
```

> **Note:** Use `term_set` if `Term.semester` has no `related_name`; otherwise use the `related_name`. Verify with the shell introspection from Task 7.

- [ ] **Step 4: Create context processor**

Create `accounts/context_processors.py`:

```python
def department_context(request):
    """[Classedge LMS] Provide the logged-in user's first headed department (if any)."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    head = user.headed_departments.first() if hasattr(user, "headed_departments") else None
    return {"headed_department": head}
```

- [ ] **Step 5: Register the context processor**

Open `classedge/settings.py`. Find the `TEMPLATES = [...]` block and append to the `context_processors` list inside `OPTIONS`:

```python
                'accounts.context_processors.department_context',
```

(If `classedge/settings.py` doesn't exist, use `ls classedge/` or `grep -rn "TEMPLATES = " --include='*.py' -l` to find the real settings module.)

- [ ] **Step 6: Create the calendar template**

Create `accounts/templates/accounts/departments/department_calendar.html`:

```django
{% extends "teacher_base.html" %}
{% load static %}

{% block title %}{{ dept.name }} — Calendar{% endblock %}

{% block content %}
<style>
  .dc { background: #faf7f2; padding: 24px 32px; font-family: "Inter Tight", sans-serif; color: #2d3142; }
  .dc h1, .dc h2 { font-family: "Fraunces", serif; color: #1b4332; }
  .card { background: #fff; border-radius: 10px; padding: 20px; margin-bottom: 20px; border: 1px solid #eee6d6; }
  .sem { border-left: 4px solid #b7925a; padding-left: 14px; margin-bottom: 16px; }
  .term-row { display: flex; gap: 12px; align-items: center; padding: 8px 0; border-bottom: 1px dashed #eee6d6; }
  .btn { padding: 6px 12px; border-radius: 6px; background: #1b4332; color: #faf7f2; text-decoration: none; font-weight: 600; border: 0; cursor: pointer; }
  .btn.alt { background: #b7925a; }
  .muted { opacity: 0.65; }
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
</style>

<div class="dc">
  <h1>{{ dept.name }}</h1>

  {# Info card #}
  <section class="card">
    <div><strong>Head:</strong> {{ dept.head.get_full_name|default:dept.head.username|default:"—" }}</div>
    <div><strong>Cadence:</strong> {{ dept.get_cadence_display|default:"—" }}</div>
    {% if request.user.is_superuser or request.user.profile.role.name|lower == "admin" %}
      <a class="btn alt" style="margin-top:10px; display:inline-block;" href="{% url 'department_settings' dept.id %}">Edit</a>
    {% endif %}
  </section>

  {# Semesters #}
  <section class="card">
    <div style="display:flex; justify-content:space-between; align-items:center;">
      <h2>Semesters</h2>
      <form method="post" action="{% url 'semester_create' dept.id %}" style="display:flex; gap:8px;">
        {% csrf_token %}
        <select name="semester_name" required>
          {% for value, label in semester_choices %}<option value="{{ value }}">{{ label }}</option>{% endfor %}
        </select>
        <input type="date" name="start_date" required>
        <input type="date" name="end_date" required>
        <button class="btn" type="submit">+ Add Semester</button>
      </form>
    </div>
    {% for sem in semesters %}
      {% include "accounts/departments/_semester_block.html" with sem=sem dept=dept %}
    {% empty %}
      <p class="muted">No semesters yet.</p>
    {% endfor %}
  </section>

  {# Events + Holidays #}
  <section class="two-col">
    <div class="card">
      <h2>Events</h2>
      <form method="post" action="{% url 'department_event_create' dept.id %}">
        {% csrf_token %}
        <input name="title" placeholder="Title" required>
        <input type="date" name="start_date" required>
        <input type="date" name="end_date">
        <button class="btn" type="submit">Add</button>
      </form>
      <ul>
        {% for e in events %}<li>{{ e.start_date|date:"Y-m-d" }} — {{ e.title }}</li>{% empty %}<li class="muted">None</li>{% endfor %}
      </ul>
    </div>
    <div class="card">
      <h2>Holidays</h2>
      <form method="post" action="{% url 'department_holiday_create' dept.id %}">
        {% csrf_token %}
        <input name="title" placeholder="Title" required>
        <input type="date" name="date" required>
        <input name="color" placeholder="#b7925a" value="#b7925a">
        <button class="btn" type="submit">Add</button>
      </form>
      <ul>
        {% for h in holidays %}<li>{{ h.date|date:"Y-m-d" }} — {{ h.title }}</li>{% empty %}<li class="muted">None</li>{% endfor %}
      </ul>
    </div>
  </section>
</div>
{% endblock %}
```

- [ ] **Step 7: Create `_semester_block.html`**

Create `accounts/templates/accounts/departments/_semester_block.html`:

```django
<div class="sem" id="semester-{{ sem.id }}">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <strong>{{ sem.semester_name }} ({{ sem.start_date|date:"Y-m-d" }} – {{ sem.end_date|date:"Y-m-d" }})</strong>
    <form
      hx-post="{% url 'term_create' dept.id %}"
      hx-target="#semester-{{ sem.id }}"
      hx-swap="outerHTML"
      style="display:flex; gap:6px;">
      {% csrf_token %}
      <input type="hidden" name="semester_id" value="{{ sem.id }}">
      <select name="term_name">
        <option value="Prelim">Prelim</option>
        <option value="Midterm">Midterm</option>
        <option value="Pre-Final">Pre-Final</option>
        <option value="Final Term">Final Term</option>
      </select>
      <input type="date" name="start_date">
      <input type="date" name="end_date">
      <button class="btn" type="submit">+ Term</button>
    </form>
  </div>
  {% for term in sem.term_set.all %}
    {% include "accounts/departments/_term_row.html" with term=term dept=dept %}
  {% empty %}
    <p class="muted">No terms yet.</p>
  {% endfor %}
</div>
```

- [ ] **Step 8: Create `_term_row.html`**

Create `accounts/templates/accounts/departments/_term_row.html`:

```django
{% if edit_mode %}
<form class="term-row"
      hx-post="{% url 'term_edit' dept.id term.id %}"
      hx-target="#term-{{ term.id }}"
      hx-swap="outerHTML">
  {% csrf_token %}
  <div id="term-{{ term.id }}" style="display:flex; gap:8px; align-items:center; width:100%;">
    <select name="term_name">
      {% for value, label in term.TERM_CHOICES %}
        <option value="{{ value }}" {% if term.term_name == value %}selected{% endif %}>{{ label }}</option>
      {% endfor %}
    </select>
    <input type="date" name="start_date" value="{{ term.start_date|date:'Y-m-d' }}">
    <input type="date" name="end_date" value="{{ term.end_date|date:'Y-m-d' }}">
    <button class="btn" type="submit">Save</button>
    {% if error %}<span style="color:#c08479;">{{ error }}</span>{% endif %}
  </div>
</form>
{% else %}
<div class="term-row" id="term-{{ term.id }}">
  <span>{{ term.term_name }}</span>
  <span class="muted">{{ term.start_date|date:"Y-m-d"|default:"—" }} → {{ term.end_date|date:"Y-m-d"|default:"—" }}</span>
  <a href="#"
     hx-get="{% url 'term_edit' dept.id term.id %}?mode=edit"
     hx-target="#term-{{ term.id }}"
     hx-swap="outerHTML"
     style="margin-left:auto;">Edit</a>
</div>
{% endif %}
```

- [ ] **Step 9: Add teacher_base shortcut**

Locate the teacher base template:

```bash
grep -rn "teacher_base" --include='*.html' -l | head
```

Open the first match and add near other nav items:

```django
{# [Classedge LMS] Department head shortcut #}
{% if headed_department %}
  <a href="{% url 'department_calendar' headed_department.id %}" class="sidebar-link">🏛️ My Department</a>
{% endif %}
```

- [ ] **Step 10: Inject `semester_choices` into the view context**

Update the view in `department_admin.py` to pass `semester_choices`:

```python
from course.models.semester_model import Semester
...
        {"dept": dept, "semesters": semesters, "events": events, "holidays": holidays,
         "semester_choices": Semester.SEMESTER_CHOICES},
```

- [ ] **Step 11: Run calendar tests — expect pass**

Run: `python manage.py test accounts.tests.test_department_admin.DepartmentCalendarViewTests --keepdb -v 2`

- [ ] **Step 12: Commit**

```bash
git add accounts/views/department_admin.py accounts/context_processors.py accounts/templates/accounts/departments/ classedge/settings.py accounts/tests/test_department_admin.py
git add <teacher_base-template-you-edited>
git commit -m "feat(accounts): add department_calendar view with HTMX fragments + nav shortcut"
```

---

## Task 10: Semester + Term create/edit views with HTMX fragments

**Files:**
- Modify: `accounts/views/department_admin.py`
- Create: `accounts/tests/test_semester_term_crud.py`

- [ ] **Step 1: Write failing CRUD tests**

Create `accounts/tests/test_semester_term_crud.py`:

```python
from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models.account_models import CustomUser
from accounts.tests.helpers import make_department, make_profile_for, make_semester
from course.models.term_model import Term


class SemesterCRUDTests(TestCase):
    def setUp(self):
        self.head = CustomUser.objects.create_user(
            username="h", email="h@x.io", password="x",
        )
        make_profile_for(self.head, "teacher")
        self.dept = make_department(head=self.head)
        self.client.force_login(self.head)

    def test_create_semester(self):
        resp = self.client.post(
            reverse("semester_create", args=[self.dept.id]),
            {"semester_name": "First Semester", "start_date": "2026-06-01", "end_date": "2026-10-31"},
        )
        self.assertIn(resp.status_code, (200, 302))
        self.assertEqual(self.dept.semesters.count(), 1)

    def test_create_semester_cross_dept_denied(self):
        other_head = CustomUser.objects.create_user(username="h2", email="h2@x.io", password="x")
        make_profile_for(other_head, "teacher")
        self.client.force_login(other_head)
        resp = self.client.post(
            reverse("semester_create", args=[self.dept.id]),
            {"semester_name": "First Semester", "start_date": "2026-06-01", "end_date": "2026-10-31"},
        )
        self.assertEqual(resp.status_code, 403)


class TermCRUDTests(TestCase):
    def setUp(self):
        self.head = CustomUser.objects.create_user(username="h", email="h@x.io", password="x")
        make_profile_for(self.head, "teacher")
        self.dept = make_department(head=self.head)
        self.sem = make_semester(self.dept)
        self.client.force_login(self.head)

    def test_create_term(self):
        resp = self.client.post(
            reverse("term_create", args=[self.dept.id]),
            {"semester_id": self.sem.id, "term_name": "Prelim",
             "start_date": "2026-06-05", "end_date": "2026-07-05"},
        )
        self.assertIn(resp.status_code, (200, 302))
        self.assertEqual(Term.objects.count(), 1)

    def test_create_term_out_of_range_rejected(self):
        resp = self.client.post(
            reverse("term_create", args=[self.dept.id]),
            {"semester_id": self.sem.id, "term_name": "Prelim",
             "start_date": "2026-05-01", "end_date": "2026-07-05"},
        )
        # Expect the HTMX fragment to render with an error; no Term should be persisted
        self.assertEqual(Term.objects.count(), 0)

    def test_edit_term_happy_path(self):
        term = Term.objects.create(
            semester=self.sem, term_name="Prelim",
            start_date=date(2026, 6, 10), end_date=date(2026, 7, 10),
        )
        resp = self.client.post(
            reverse("term_edit", args=[self.dept.id, term.id]),
            {"term_name": "Prelim", "start_date": "2026-06-15", "end_date": "2026-07-15"},
        )
        self.assertIn(resp.status_code, (200, 302))
        term.refresh_from_db()
        self.assertEqual(term.start_date, date(2026, 6, 15))

    def test_edit_term_non_head_denied(self):
        term = Term.objects.create(semester=self.sem, term_name="Prelim")
        intruder = CustomUser.objects.create_user(username="int", email="int@x.io", password="x")
        make_profile_for(intruder, "teacher")
        self.client.force_login(intruder)
        resp = self.client.post(
            reverse("term_edit", args=[self.dept.id, term.id]),
            {"term_name": "Midterm"},
        )
        self.assertEqual(resp.status_code, 403)
```

- [ ] **Step 2: Run — expect failures (stubs)**

Run: `python manage.py test accounts.tests.test_semester_term_crud --keepdb -v 2`

- [ ] **Step 3: Replace the semester/term stubs**

In `accounts/views/department_admin.py`, delete the 4 stub lines for semester/term, and add:

```python
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST, require_http_methods

from course.models.term_model import Term


@login_required
@require_POST
def semester_create(request, dept_id):
    """[Classedge LMS] Create a new Semester owned by this department."""
    dept = get_object_or_404(Department, pk=dept_id)
    authorize_department_head(request.user, dept)
    Semester.objects.create(
        department=dept,
        semester_name=request.POST.get("semester_name"),
        start_date=request.POST.get("start_date"),
        end_date=request.POST.get("end_date"),
    )
    return redirect("department_calendar", dept_id=dept.id)


@login_required
@require_POST
def semester_edit(request, dept_id, sem_id):
    """[Classedge LMS] Edit a department's Semester dates."""
    dept = get_object_or_404(Department, pk=dept_id)
    authorize_department_head(request.user, dept)
    sem = get_object_or_404(Semester, pk=sem_id, department=dept)
    sem.semester_name = request.POST.get("semester_name", sem.semester_name)
    sem.start_date = request.POST.get("start_date") or sem.start_date
    sem.end_date = request.POST.get("end_date") or sem.end_date
    sem.save()
    return redirect("department_calendar", dept_id=dept.id)


@login_required
@require_POST
def term_create(request, dept_id):
    """[Classedge LMS] Create a new Term under one of this department's Semesters."""
    dept = get_object_or_404(Department, pk=dept_id)
    authorize_department_head(request.user, dept)
    sem = get_object_or_404(Semester, pk=request.POST.get("semester_id"), department=dept)
    term = Term(
        semester=sem,
        term_name=request.POST.get("term_name"),
        start_date=request.POST.get("start_date") or None,
        end_date=request.POST.get("end_date") or None,
        created_by=request.user,
    )
    try:
        term.full_clean()
        term.save()
    except ValidationError as e:
        # Re-render just the semester block with an error band
        return render(
            request,
            "accounts/departments/_semester_block.html",
            {"sem": sem, "dept": dept, "error": "; ".join(e.messages)},
        )
    return render(
        request,
        "accounts/departments/_semester_block.html",
        {"sem": sem, "dept": dept},
    )


@login_required
@require_http_methods(["GET", "POST"])
def term_edit(request, dept_id, term_id):
    """[Classedge LMS] HTMX inline edit of term_name + start_date + end_date; validates via clean()."""
    dept = get_object_or_404(Department, pk=dept_id)
    authorize_department_head(request.user, dept)
    term = get_object_or_404(Term, pk=term_id, semester__department=dept)
    if request.method == "GET" and request.GET.get("mode") == "edit":
        return render(
            request,
            "accounts/departments/_term_row.html",
            {"term": term, "dept": dept, "edit_mode": True},
        )
    if request.method == "POST":
        term.term_name = request.POST.get("term_name", term.term_name)
        term.start_date = request.POST.get("start_date") or None
        term.end_date = request.POST.get("end_date") or None
        try:
            term.full_clean()
            term.save()
            return render(
                request,
                "accounts/departments/_term_row.html",
                {"term": term, "dept": dept, "edit_mode": False},
            )
        except ValidationError as e:
            return render(
                request,
                "accounts/departments/_term_row.html",
                {"term": term, "dept": dept, "edit_mode": True, "error": "; ".join(e.messages)},
            )
    return render(
        request,
        "accounts/departments/_term_row.html",
        {"term": term, "dept": dept, "edit_mode": False},
    )
```

- [ ] **Step 4: Run the tests — expect pass**

Run: `python manage.py test accounts.tests.test_semester_term_crud --keepdb -v 2`

- [ ] **Step 5: Commit**

```bash
git add accounts/views/department_admin.py accounts/tests/test_semester_term_crud.py
git commit -m "feat(accounts): semester/term CRUD with HTMX fragments + clean() validation"
```

---

## Task 11: Department-scoped Event + Holiday create views

**Files:**
- Modify: `accounts/views/department_admin.py`

- [ ] **Step 1: Replace the stubs**

In `accounts/views/department_admin.py`, delete the last two `_stub` aliases and add:

```python
from calendars.models import Event, Holiday


@login_required
@require_POST
def department_event_create(request, dept_id):
    """[Classedge LMS] Create a department-scoped Event."""
    dept = get_object_or_404(Department, pk=dept_id)
    authorize_department_head(request.user, dept)
    Event.objects.create(
        department=dept,
        title=request.POST.get("title"),
        description=request.POST.get("description", ""),
        start_date=request.POST.get("start_date") or None,
        end_date=request.POST.get("end_date") or None,
        location=request.POST.get("location", ""),
        created_by=request.user,
    )
    return redirect("department_calendar", dept_id=dept.id)


@login_required
@require_POST
def department_holiday_create(request, dept_id):
    """[Classedge LMS] Create a department-scoped Holiday."""
    dept = get_object_or_404(Department, pk=dept_id)
    authorize_department_head(request.user, dept)
    Holiday.objects.create(
        department=dept,
        title=request.POST.get("title"),
        date=request.POST.get("date"),
        color=request.POST.get("color", "#b7925a"),
        holiday_type=request.POST.get("holiday_type", "Regular Holiday"),
    )
    return redirect("department_calendar", dept_id=dept.id)
```

Now remove the entire `_stub` helper block at the bottom of the file — it's no longer referenced.

- [ ] **Step 2: Manual smoke test**

Run: `python manage.py runserver 0.0.0.0:8000 &`

Then open `http://localhost:8000/departments/<id>/calendar/`, post an Event and a Holiday via the inline forms. Verify both appear in the rendered lists. Kill the server.

- [ ] **Step 3: Add smoke tests**

Append to `accounts/tests/test_department_admin.py`:

```python
class EventHolidayCreateTests(TestCase):
    def setUp(self):
        self.head = CustomUser.objects.create_user(username="h3", email="h3@x.io", password="x")
        make_profile_for(self.head, "teacher")
        self.dept = make_department(head=self.head)
        self.client.force_login(self.head)

    def test_create_event(self):
        from calendars.models import Event
        resp = self.client.post(
            reverse("department_event_create", args=[self.dept.id]),
            {"title": "Open House", "start_date": "2026-07-01"},
        )
        self.assertIn(resp.status_code, (200, 302))
        self.assertEqual(Event.objects.filter(department=self.dept).count(), 1)

    def test_create_holiday(self):
        from calendars.models import Holiday
        resp = self.client.post(
            reverse("department_holiday_create", args=[self.dept.id]),
            {"title": "Department Day", "date": "2026-08-20", "color": "#b7925a"},
        )
        self.assertIn(resp.status_code, (200, 302))
        self.assertEqual(Holiday.objects.filter(department=self.dept).count(), 1)
```

- [ ] **Step 4: Run tests**

Run: `python manage.py test accounts.tests.test_department_admin.EventHolidayCreateTests --keepdb -v 2`

- [ ] **Step 5: Commit**

```bash
git add accounts/views/department_admin.py accounts/tests/test_department_admin.py
git commit -m "feat(accounts): add department-scoped Event and Holiday create views"
```

---

## Task 12: `visible_department_ids` service + `calendar_api` filtering

**Files:**
- Create: `calendars/services/__init__.py`
- Create: `calendars/services/department_filter.py`
- Modify: `calendars/views.py`
- Create: `calendars/tests/__init__.py` (if missing)
- Create: `calendars/tests/test_department_filter.py`
- Create: `calendars/tests/test_calendar_api_scoping.py`

- [ ] **Step 1: Write the service test (TDD)**

Create `calendars/tests/test_department_filter.py`:

```python
from django.test import TestCase

from accounts.models.account_models import CustomUser
from accounts.tests.helpers import make_department, make_profile_for
from calendars.services.department_filter import visible_department_ids


class VisibleDepartmentIdsTests(TestCase):
    def setUp(self):
        self.math = make_department(name="Math")
        self.sci = make_department(name="Sci")

    def _user(self, username, role, dept=None):
        u = CustomUser.objects.create_user(username=username, email=f"{username}@x.io", password="x")
        make_profile_for(u, role, department=dept)
        return u

    def test_superuser_sees_all(self):
        su = CustomUser.objects.create_superuser(username="su", email="su@x.io", password="x")
        make_profile_for(su, "admin")
        self.assertIsNone(visible_department_ids(su))

    def test_admin_sees_all(self):
        admin = self._user("adm", "admin")
        self.assertIsNone(visible_department_ids(admin))

    def test_teacher_in_math(self):
        t = self._user("t", "teacher", dept=self.math)
        self.assertEqual(visible_department_ids(t), {self.math.id})

    def test_head_of_math_without_profile_dept(self):
        u = self._user("h", "teacher")
        self.math.head = u
        self.math.save()
        self.assertEqual(visible_department_ids(u), {self.math.id})

    def test_head_and_member_of_different_depts(self):
        u = self._user("u", "teacher", dept=self.sci)
        self.math.head = u
        self.math.save()
        self.assertEqual(visible_department_ids(u), {self.math.id, self.sci.id})

    def test_user_without_any_dept(self):
        u = self._user("nobody", "teacher")
        self.assertEqual(visible_department_ids(u), set())
```

- [ ] **Step 2: Run — expect ImportError**

Run: `python manage.py test calendars.tests.test_department_filter --keepdb -v 2`

- [ ] **Step 3: Create the service**

Create `calendars/services/__init__.py` (empty).

Create `calendars/services/department_filter.py`:

```python
def visible_department_ids(user):
    """[Classedge LMS] Return the set of Department IDs a user should see scoped calendar items for.

    Returns None to mean "no filter, see everything" (superusers + admins).
    Returns an (empty) set otherwise.
    """
    if user.is_superuser:
        return None
    role = getattr(getattr(user, "profile", None), "role", None)
    if role and role.name.lower() == "admin":
        return None
    ids = set()
    profile = getattr(user, "profile", None)
    if profile and getattr(profile, "department_fields_id", None):
        ids.add(profile.department_fields_id)
    if hasattr(user, "headed_departments"):
        ids.update(user.headed_departments.values_list("id", flat=True))
    return ids
```

- [ ] **Step 4: Run — expect pass**

Run: `python manage.py test calendars.tests.test_department_filter --keepdb -v 2`

- [ ] **Step 5: Add the integration test for `calendar_api`**

Create `calendars/tests/test_calendar_api_scoping.py`:

```python
from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models.account_models import CustomUser
from accounts.tests.helpers import make_department, make_profile_for
from calendars.models import Event


class CalendarApiScopingTests(TestCase):
    def setUp(self):
        self.math = make_department(name="Math")
        self.sci = make_department(name="Sci")
        self.math_evt = Event.objects.create(
            title="Math Fair", start_date=date(2026, 6, 10),
            department=self.math,
            created_by=CustomUser.objects.create_user(username="creator", email="c@x.io", password="x"),
        )
        self.global_evt = Event.objects.create(
            title="All Hands", start_date=date(2026, 6, 11),
            created_by=self.math_evt.created_by,
        )

    def _login(self, username, role, dept=None):
        u = CustomUser.objects.create_user(username=username, email=f"{username}@x.io", password="x")
        make_profile_for(u, role, department=dept)
        self.client.force_login(u)
        return u

    def _titles(self, resp):
        return {item["title"] for item in resp.json() if item.get("type") == "event"}

    def test_math_teacher_sees_math_and_global(self):
        self._login("t1", "teacher", dept=self.math)
        resp = self.client.get(reverse("calendar_api"))  # adjust name if different
        titles = self._titles(resp)
        self.assertIn("Math Fair", titles)
        self.assertIn("All Hands", titles)

    def test_sci_teacher_hidden_from_math_event(self):
        self._login("t2", "teacher", dept=self.sci)
        resp = self.client.get(reverse("calendar_api"))
        titles = self._titles(resp)
        self.assertNotIn("Math Fair", titles)
        self.assertIn("All Hands", titles)

    def test_admin_sees_all(self):
        self._login("adm", "admin")
        resp = self.client.get(reverse("calendar_api"))
        titles = self._titles(resp)
        self.assertIn("Math Fair", titles)
        self.assertIn("All Hands", titles)
```

> **URL name:** confirm with `grep -n "name='calendar_api'\\|name=\"calendar_api\"" calendars/urls.py`. If the name differs, use the real value.

- [ ] **Step 6: Run — expect failures (filtering not yet applied)**

Run: `python manage.py test calendars.tests.test_calendar_api_scoping --keepdb -v 2`

- [ ] **Step 7: Wire the filter into `calendar_api`**

Open `calendars/views.py`. At the top add:

```python
from django.db.models import Q

from calendars.services.department_filter import visible_department_ids
```

Inside `calendar_api`, replace `for event in Event.objects.all():` with:

```python
            dept_ids = visible_department_ids(request.user)
            if dept_ids is None:
                events_qs = Event.objects.all()
            else:
                events_qs = Event.objects.filter(
                    Q(department__isnull=True) | Q(department_id__in=dept_ids)
                )
            for event in events_qs:
```

Even though `Holiday` and `Announcement` are currently commented-out in `calendar_api`, the filter applies to any future re-enablement — but we don't touch commented code here. Only the `events` query is changed.

- [ ] **Step 8: Run — expect pass**

Run: `python manage.py test calendars.tests.test_calendar_api_scoping --keepdb -v 2`

- [ ] **Step 9: Commit**

```bash
git add calendars/services/ calendars/tests/__init__.py calendars/tests/test_department_filter.py calendars/tests/test_calendar_api_scoping.py calendars/views.py
git commit -m "feat(calendars): filter calendar_api events by department membership"
```

---

## Task 13: Function-label enforcement test

**Files:**
- Create: `accounts/tests/test_function_labels.py`

- [ ] **Step 1: Add the test**

Create `accounts/tests/test_function_labels.py`:

```python
import inspect

from django.test import SimpleTestCase

from accounts.services import department_access
from accounts.views import department_admin
from calendars.services import department_filter


PUBLIC_MODULES = [department_access, department_admin, department_filter]


class ClassedgeLMSLabelTests(SimpleTestCase):
    def test_every_public_function_is_labeled(self):
        missing = []
        for mod in PUBLIC_MODULES:
            for name, obj in inspect.getmembers(mod, inspect.isfunction):
                if name.startswith("_"):
                    continue
                if obj.__module__ != mod.__name__:
                    # imported symbol, skip
                    continue
                doc = inspect.getdoc(obj) or ""
                if "[Classedge LMS]" not in doc:
                    missing.append(f"{mod.__name__}.{name}")
        self.assertFalse(missing, f"Missing [Classedge LMS] label: {missing}")
```

- [ ] **Step 2: Run it**

Run: `python manage.py test accounts.tests.test_function_labels --keepdb -v 2`
Expected: PASS. If any function is reported, add `[Classedge LMS]` to the first line of its docstring and re-run.

- [ ] **Step 3: Commit**

```bash
git add accounts/tests/test_function_labels.py
git commit -m "test: enforce [Classedge LMS] label on department-feature functions"
```

---

## Task 14: Full-suite smoke + manual QA

- [ ] **Step 1: Run the full new-test set**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py test \
  accounts.tests.test_department_access \
  accounts.tests.test_department_admin \
  accounts.tests.test_department_migration \
  accounts.tests.test_function_labels \
  accounts.tests.test_semester_term_crud \
  accounts.tests.test_term_date_validation \
  calendars.tests.test_calendar_api_scoping \
  calendars.tests.test_department_filter \
  --keepdb -v 2
```

Expected: all ~20+ tests PASS.

- [ ] **Step 2: Broader smoke**

Run: `python manage.py test accounts calendars course --keepdb -v 1`
Expected: no regression failures from existing test modules. If a pre-existing test fails in a way unrelated to this feature, note it and check with the user before skipping.

- [ ] **Step 3: Manual QA checklist**

Start the dev server: `python manage.py runserver`

Log in as each role (use existing dev credentials) and verify:

- **Admin:** Sidebar has 🏛️ Departments link. Can list, assign head + cadence.
- **Department head (teacher with `headed_departments`):** Sees "🏛️ My Department" shortcut. Can create a Semester, add a Term, HTMX inline edit a Term, add an Event, add a Holiday.
- **Teacher in dept X:** Calendar shows only dept-X events + institution-wide events; dept-Y events absent.
- **Non-head, non-admin user** visiting `/departments/<X>/calendar/`: 403.
- **Term with start_date before semester start:** HTMX form re-renders with rose-colored inline error; no row created.

- [ ] **Step 4: Final commit if anything adjusted**

If step 3 revealed any template polish or copy fix, commit:

```bash
git add -p
git commit -m "chore(accounts): manual QA polish for department calendar UI"
```

- [ ] **Step 5: Open a PR**

```bash
git push -u origin <branch-name>
gh pr create --title "Department-scoped calendars" --body "$(cat <<'EOF'
## Summary
- Each Department owns its own Semesters + Terms, with clean() validation ensuring term dates fit inside the semester window.
- Holiday / Event / Announcement are now optionally scoped to a Department (null = institution-wide).
- Department head admin UI at /departments/<id>/calendar/ with HTMX inline term editing.
- calendar_api now filters events by department membership.
- Data migration seeds a "General" Department and attaches orphan Semesters.

## Test plan
- [ ] New tests pass: ~20 tests across accounts/calendars
- [ ] Manual: admin lists + edits, head manages semesters/terms, cross-dept visibility hidden
- [ ] Existing calendar_api still returns institution-wide events
EOF
)"
```

---

## Self-review checklist for the implementer

Before marking the plan complete, confirm:

- [ ] Every new public function has `[Classedge LMS]` in its docstring.
- [ ] No new `ProtectedRoute` entries were added (Classedge LMS uses Django templates, not React).
- [ ] `Semester.department` is `PROTECT` on delete (never cascade-delete a dept's semesters).
- [ ] `Holiday/Event/Announcement.department` is `SET_NULL` (deleting a dept leaves items as institution-wide).
- [ ] The `General` Department is idempotent on re-migrate.
- [ ] `visible_department_ids` returns `None` (not an empty set) for superusers & admins — the `calendar_api` code path relies on the `None` sentinel to skip filtering.
- [ ] `term.full_clean()` is called inside views (`term_create`, `term_edit`) — not implicit on `save()`.

---

Plan complete and saved to `docs/superpowers/plans/2026-04-22-department-scoped-calendars.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
