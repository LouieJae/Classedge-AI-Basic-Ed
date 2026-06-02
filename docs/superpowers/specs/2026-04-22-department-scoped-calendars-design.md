# Department-Scoped Calendars — Design

**System:** Classedge LMS (`~/classedge`)
**Date:** 2026-04-22
**Apps:** `accounts/` (primary), `course/`, `calendars/`

All new function signatures in this spec carry a `[Classedge LMS]` label per repo-wide convention.

---

## 1. Scope & Goal

Every Department owns its own term dates (never shared across departments) and may optionally scope calendar events, holidays, and announcements to only its own members.

### 1.1 Primary screens

1. **Department list** (`/departments/`) — admin/superuser list of all departments with head + cadence + term count. Navigates to per-department admin.
2. **Department calendar admin** (`/departments/<id>/calendar/`) — department head's landing page. Department info card + Semesters (with nested Terms, inline-editable) + Events & Holidays scoped to this department.
3. **Updated calendar API** — existing `calendars/views.py::calendar_api` now filters `Event`/`Holiday`/`Announcement` by the requesting user's Department membership. Activity scoping is unchanged.

### 1.2 In scope

- `Department.head` FK + `Department.cadence` CharField
- `Semester.department` FK (nullable in v1 to tolerate legacy rows)
- `Holiday.department`, `Event.department`, `Announcement.department` (all nullable — null = institution-wide)
- `Term.clean()` validator ensuring `start_date`/`end_date` fall within the Semester's date range
- Department-head authorization helper + service
- Department-scoped calendar filter service
- Data migration seeding a "General" Department and attaching orphan Semesters to it
- Nav entries: admin sidebar "Departments" link + `teacher_base.html` "My Department" shortcut for users who head a department

### 1.3 Out of scope (deferred)

- `Subject.department` FK (scope-B choice during brainstorm; covered in a future feature)
- Multiple heads per department (single `Department.head` FK for v1; upgrade to M2M later if needed)
- Tightening `Term.start_date` / `end_date` to `null=False` (ship nullable first, tighten after admin-UI backfill)
- Permission-matrix overhaul (reuse existing decorators + new head-check helper)
- Per-term cross-department sharing rules (the rule is simple: never shared)
- Frontend React `ProtectedRoute` entries — Classedge LMS uses Django templates + HTMX, not React SPA

### 1.4 Success criteria

- An admin can see all departments and assign a head + cadence.
- A department head can create semesters and terms for their own department only, with dates that must fall within the semester window.
- A department-scoped Event is invisible to members of other departments.
- Institution-wide items (null `department`) remain visible to everyone.
- The data migration attaches every existing orphan Semester to a "General" Department on first deploy, without requiring a human step.

---

## 2. Data model changes

### 2.1 `accounts/models/department_models.py`

```python
class Department(models.Model):
    name = models.CharField(max_length=100)
    head = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="headed_departments",
    )
    # [Classedge LMS] Single authoritative department head — Principal / Dean / Program Head.
    cadence = models.CharField(
        max_length=20, null=True, blank=True,
        choices=[
            ("semester", "Semester"),
            ("school_year", "School Year"),
            ("trimester", "Trimester"),
            ("quarter", "Quarter"),
        ],
    )
    # [Classedge LMS] Rhythm hint — drives term-name UI suggestions and future report grouping.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### 2.2 `course/models/semester_model.py`

```python
# New field appended to existing Semester model:
department = models.ForeignKey(
    "accounts.Department", on_delete=models.PROTECT,
    null=True, blank=True, related_name="semesters",
)
# [Classedge LMS] Department that owns this semester's dates. Populated by the
# "General" backfill migration; nullable to tolerate legacy rows. Will be tightened
# to null=False in a follow-up migration after admin-UI backfill is confirmed complete.
```

### 2.3 `course/models/term_model.py` — no new FK, add validator

No column added. `Term` inherits its department via `term.semester.department`.

Add a `clean()` method:

```python
from django.core.exceptions import ValidationError


def clean(self):
    """[Classedge LMS] Ensure Term dates fall within the Semester's window when all are set."""
    if not self.semester_id:
        return
    sem = self.semester
    if self.start_date and sem.start_date and self.start_date < sem.start_date:
        raise ValidationError("Term start_date is before semester start_date.")
    if self.end_date and sem.end_date and self.end_date > sem.end_date:
        raise ValidationError("Term end_date is after semester end_date.")
    if self.start_date and self.end_date and self.end_date < self.start_date:
        raise ValidationError("Term end_date is before start_date.")
```

`start_date` and `end_date` remain nullable in this release. UI forms call `full_clean()` before save.

### 2.4 `calendars/models.py` — added to `Holiday`, `Event`, `Announcement`

```python
department = models.ForeignKey(
    "accounts.Department", on_delete=models.SET_NULL,
    null=True, blank=True, related_name="%(class)ss",
)
# [Classedge LMS] Null => institution-wide (visible to all users).
# Non-null => scoped to members of that department only.
```

### 2.5 No new permission keys

Classedge LMS uses role-string checks, not a permission matrix. Reuse `@admin_required` for admin-only views. A new helper `authorize_department_head(user, department)` gates head-only views.

---

## 3. URL structure & views

All new routes in `accounts/urls.py`. No URL namespace (explicit names, matching repo convention).

| URL | View | Method | Purpose |
|---|---|---|---|
| `/departments/` | `department_list` | GET | Admin list of all departments |
| `/departments/<int:dept_id>/calendar/` | `department_calendar` | GET | Department head's calendar admin page |
| `/departments/<int:dept_id>/settings/` | `department_settings` | GET/POST | Edit head + cadence (admin only) |
| `/departments/<int:dept_id>/semesters/create/` | `semester_create` | POST | Create new Semester in this department |
| `/departments/<int:dept_id>/semesters/<int:sem_id>/edit/` | `semester_edit` | POST | Update Semester dates |
| `/departments/<int:dept_id>/terms/create/` | `term_create` | POST | Create a new Term under a Semester |
| `/departments/<int:dept_id>/terms/<int:term_id>/edit/` | `term_edit` | POST | Inline-edit Term name + dates (HTMX) |
| `/departments/<int:dept_id>/events/create/` | `department_event_create` | POST | Create department-scoped Event |
| `/departments/<int:dept_id>/holidays/create/` | `department_holiday_create` | POST | Create department-scoped Holiday |

### 3.1 View signatures (all in `accounts/views/department_admin.py`)

```python
@admin_required
def department_list(request):
    """[Classedge LMS] Admin list of all departments with head + cadence + term count."""

@login_required
def department_calendar(request, dept_id):
    """[Classedge LMS] Department head's landing page — semesters, terms, events."""

@admin_required
def department_settings(request, dept_id):
    """[Classedge LMS] Edit Department.head and Department.cadence."""

@login_required
@require_POST
def semester_create(request, dept_id):
    """[Classedge LMS] Create a new Semester owned by this department."""

@login_required
@require_POST
def semester_edit(request, dept_id, sem_id):
    """[Classedge LMS] Edit a department's Semester dates."""

@login_required
@require_POST
def term_create(request, dept_id):
    """[Classedge LMS] Create a new Term under one of this department's Semesters."""

@login_required
@require_POST
def term_edit(request, dept_id, term_id):
    """[Classedge LMS] HTMX inline edit of term_name + start_date + end_date; validates via clean()."""

@login_required
@require_POST
def department_event_create(request, dept_id):
    """[Classedge LMS] Create a department-scoped Event."""

@login_required
@require_POST
def department_holiday_create(request, dept_id):
    """[Classedge LMS] Create a department-scoped Holiday."""
```

### 3.2 Authorization helper

File: `accounts/services/department_access.py`

```python
from django.core.exceptions import PermissionDenied


def authorize_department_head(user, department):
    """[Classedge LMS] Allow superusers, admins, or the department's head; otherwise PermissionDenied."""
    if user.is_superuser:
        return
    role = getattr(user.profile, "role", None)
    role_name = role.name.lower() if role else ""
    if role_name == "admin":
        return
    if department.head_id == user.id:
        return
    raise PermissionDenied("Not authorized for this department.")
```

Every POST endpoint in §3 calls `authorize_department_head(request.user, department)` at the top. `department_list` and `department_settings` use the existing `@admin_required` decorator.

### 3.3 HTMX conventions

- **Term row** — inline HTMX edit. Read mode = name + dates + `hx-get` "Edit" link; edit mode = input fields + save button that `hx-post`s to `term_edit`; server renders `_term_row.html` fragment and swaps it back.
- **Semester block** — after `term_create`, the server returns the updated `_semester_block.html` fragment that replaces the block. No full page reload.
- **Events / holidays** — standard HTML form POSTs (page refreshes). Simple and sufficient.

---

## 4. Templates & nav integration

Templates in `accounts/templates/accounts/departments/`.

| Template | Extends | Role |
|---|---|---|
| `department_list.html` | admin layout | Table: name, head, cadence, #terms, edit link |
| `department_calendar.html` | `teacher_base.html` (head) / admin layout (admin) | 3-section full-page admin |
| `department_settings.html` | admin layout | Small form — head picker + cadence dropdown |
| `_term_row.html` | — | HTMX fragment: one term row (read or edit mode) |
| `_semester_block.html` | — | HTMX fragment: semester + nested terms list |

### 4.1 Nav additions

Admin sidebar (existing admin base template):

```django
<!-- [Classedge LMS] Department admin -->
{% if request.user.is_superuser or request.user.profile.role.name|lower == "admin" %}
<a href="{% url 'department_list' %}">🏛️ Departments</a>
{% endif %}
```

`teacher_base.html` (via context processor `headed_department`):

```django
{% if headed_department %}
<!-- [Classedge LMS] Department head shortcut -->
<a href="{% url 'department_calendar' headed_department.id %}">🏛️ My Department</a>
{% endif %}
```

Context processor (add to `gamification/context_processors.py::student_context` — or a new `accounts/context_processors.py::department_context`):

```python
def department_context(request):
    """[Classedge LMS] Provide the logged-in user's first headed department (if any)."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    head = user.headed_departments.first() if hasattr(user, "headed_departments") else None
    return {"headed_department": head}
```

### 4.2 `department_calendar.html` layout

Three stacked sections:

- **Department info card** — name, head, cadence. Read-only for head, "Edit" link to `/settings/` for admin.
- **Semesters** — collapsible blocks, one per Semester. Each block shows its Terms with inline-editable name + dates via HTMX. Block-level "Add Term" button; page-level "Add Semester" button.
- **Events & Holidays** — two side-by-side lists for department-scoped items. Quick-add form inline at the top of each list. Link to the institution-wide calendar at the bottom.

### 4.3 Styling

- Reuse `teacher_base.html` tokens — cream `#faf7f2`, forest `#1b4332`, gold `#b7925a`, rose `#c08479`, ink `#2d3142`; Fraunces (display) + Inter Tight (body).
- Inline `<style>` blocks per template, matching SP1–SP3 + gradebook conventions.
- Validation errors in term-edit mode render inline in rose `#c08479` above the input row.

---

## 5. Calendar API filtering

File: `calendars/services/department_filter.py`

### 5.1 Function

```python
def visible_department_ids(user):
    """[Classedge LMS] Return set of Department IDs a user should see scoped calendar items for.

    - Superusers and users whose role is 'admin' → None (no filter, see all).
    - Other users → their Profile.department_fields_id plus any departments they head.
    - Users without any department association → empty set (only institution-wide items).
    """
    if user.is_superuser:
        return None
    role = getattr(user.profile, "role", None)
    if role and role.name.lower() == "admin":
        return None
    ids = set()
    if user.profile.department_fields_id:
        ids.add(user.profile.department_fields_id)
    ids.update(user.headed_departments.values_list("id", flat=True))
    return ids
```

### 5.2 Query shape in `calendars/views.py::calendar_api`

```python
from calendars.services.department_filter import visible_department_ids

dept_ids = visible_department_ids(request.user)
if dept_ids is None:
    events_qs = Event.objects.all()
    holidays_qs = Holiday.objects.all()
    anns_qs = Announcement.objects.all()
else:
    events_qs = Event.objects.filter(
        Q(department__isnull=True) | Q(department_id__in=dept_ids)
    )
    holidays_qs = Holiday.objects.filter(
        Q(department__isnull=True) | Q(department_id__in=dept_ids)
    )
    anns_qs = Announcement.objects.filter(
        Q(department__isnull=True) | Q(department_id__in=dept_ids)
    )
```

Activity filtering in `calendar_api` is unchanged — already role- and enrollment-scoped.

### 5.3 Behavior matrix

| User | Sees dept-X event | Sees institution-wide event |
|---|---|---|
| Superuser | ✅ | ✅ |
| Admin | ✅ | ✅ |
| Teacher in dept X | ✅ | ✅ |
| Teacher in dept Y | ❌ | ✅ |
| Dept-X head who teaches in dept Y | ✅ (both) | ✅ |
| User without department | ❌ | ✅ |

---

## 6. Data migration (seeding "General")

Four migrations, in dependency order:

1. `accounts/migrations/00XX_department_head_cadence.py` — schema, adds `Department.head` + `Department.cadence`.
2. `course/migrations/00XX_semester_department.py` — schema, adds `Semester.department`.
3. `calendars/migrations/00XX_department_fk.py` — schema, adds `Holiday.department` + `Event.department` + `Announcement.department`.
4. `course/migrations/00XX_seed_general_department.py` — data migration:

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
    """[Classedge LMS] Reverse: drop the link; keep the Department row for safety."""
    Department = apps.get_model("accounts", "Department")
    Semester = apps.get_model("course", "Semester")
    general = Department.objects.filter(name="General").first()
    if general:
        Semester.objects.filter(department=general).update(department=None)


class Migration(migrations.Migration):
    dependencies = [
        ("course", "00XX_semester_department"),
        ("accounts", "00XX_department_head_cadence"),
    ]
    operations = [migrations.RunPython(seed_general_department, unseed)]
```

### 6.1 What the migration does NOT do

- Does not backfill `Term.start_date` / `end_date` — they stay as-is.
- Does not backfill `Holiday.department` / `Event.department` / `Announcement.department` — existing rows stay institution-wide.
- Does not assign a Department head — admin assigns via `/departments/<id>/settings/`.

### 6.2 Ops notes

- All four migrations run atomically under `manage.py migrate`.
- `SET_NULL` semantics for `Semester.department` make a future "General" deletion safe (semesters re-orphan rather than cascade).
- Idempotent: `get_or_create` on `name="General"` means a re-run is a no-op.

---

## 7. Testing strategy

Tests under `accounts/tests/`, `course/tests/`, `calendars/tests/`. Run with `--keepdb` against `test_neondb`.

### 7.1 Test files

| File | Covers |
|---|---|
| `accounts/tests/test_department_access.py` | `authorize_department_head` — superuser / admin / head / denied |
| `accounts/tests/test_department_admin.py` | `department_list`, `department_calendar`, `department_settings` — auth, ownership, happy path |
| `accounts/tests/test_semester_term_crud.py` | `semester_create/edit`, `term_create/edit` — auth, happy path, POST redirects |
| `accounts/tests/test_term_date_validation.py` | `Term.clean()` — in-range passes, out-of-range rejects, missing dates OK |
| `calendars/tests/test_department_filter.py` | `visible_department_ids` — every row of §5.3 matrix |
| `calendars/tests/test_calendar_api_scoping.py` | `calendar_api` — dept-scoped items show/hide per user correctly |
| `accounts/tests/test_department_migration.py` | Data migration roundtrip — General exists exactly once, orphan Semesters attached |
| `accounts/tests/test_function_labels.py` | `[Classedge LMS]` label on every new public view + service function |

### 7.2 Shared helpers

Add to a new `accounts/tests/helpers.py`:

```python
def make_department(name="Math", head=None, cadence="semester"):
    """[Classedge LMS] Create a Department for tests."""

def make_semester(department, name="First Semester", start=None, end=None):
    """[Classedge LMS] Create a Semester owned by a department."""

def make_profile_for(user, role_name, department=None):
    """[Classedge LMS] Attach a Profile + Role (+ optional department_fields) to a user."""
```

Where sensible, reuse existing helpers from `gradebookcomponent/tests/helpers.py`.

### 7.3 Must-have assertions

- `authorize_department_head` denies a random teacher and allows the head / admin / superuser.
- Term created with `start_date` before its Semester's start raises `ValidationError` on `full_clean()`.
- A Semester created in department A is invisible in department B's `department_calendar` page.
- Teacher in dept X sees dept-X events + institution-wide events; dept-Y events hidden.
- Admin/superuser sees all department events regardless of their `Profile.department_fields`.
- Data migration creates exactly one `General` Department (idempotent re-run).
- POST to `term_edit` by a non-head → 403; by the head → 302 and persisted.
- Function-labels test picks up all new public functions in `department_admin.py`, `department_access.py`, `department_filter.py`.

### 7.4 Test count target

~20–25 tests across 8 files.

### 7.5 Out of scope for tests

- No load test for `calendar_api` (scoping is a cheap query).
- No Playwright / browser tests (matches codebase convention).
- No cross-browser / mobile testing.

---

## 8. Implementation commit ordering (preview for the plan phase)

1. `Department.head` + `Department.cadence` fields + schema migration
2. `authorize_department_head` helper + tests
3. `Semester.department` field + schema migration
4. `Holiday/Event/Announcement.department` fields + schema migration
5. `Term.clean()` validator + tests
6. Data migration seeding "General" + test_department_migration
7. `department_list` view + template + admin nav entry
8. `department_settings` view + template
9. `department_calendar` view + template + context processor + `teacher_base.html` shortcut
10. Semester / Term create + edit views + HTMX fragments + tests
11. Event / Holiday create views + inline forms
12. `visible_department_ids` service + `calendar_api` filtering + tests
13. Function-label enforcement test
14. Full-suite smoke run

---

## 9. Open questions

None at spec time. One small unknown flagged for implementation: how `Profile.department_fields` is populated today (single FK vs M2M) — confirm on first read and adjust `visible_department_ids` accordingly. The audit suggests single FK (`department_fields_id`); if it turns out to be M2M the function uses `user.profile.department_fields.values_list('id', flat=True)` instead.
