# Permission Categorization + Role-Picker UI Polish — Design

**Status:** Draft
**Date:** 2026-04-23
**Phase:** 3 of 3 of the Classedge user/role/permission refactor
**Predecessors:** Phase 1 (IT Admin role foundation, merged PR #2), Phase 2 (permission-based decorators, merged PR #5)

## Context

Phases 1 and 2 of the Classedge auth refactor shipped on 2026-04-23. Phase 1 introduced the IT Admin role (the only role with `is_superuser=True`). Phase 2 migrated all role-name decorators (`@admin_required`, `@teacher_or_admin_required`, etc.) to Django's native permission system (`@permission_required("app.codename")`).

This left one piece of the original refactor unaddressed: the role-editing UI that IT Admin uses. Today it's functional but brittle, and the department-head dropdown shows every active user rather than users whose role is head-eligible.

## Problems being solved

1. **Brittle permission whitelist.** `roles/views.py` contains five copies of a hardcoded block: an `app_label` allowlist plus an `excluded_models` denylist (lines 22-30 of `roleList`, duplicated in `viewRole`, `createRole`, `updateRole`, `import_roles_csv`, `export_roles_csv`, `download_roles_template`). Every new app or model requires editing all copies. Drift between copies has already happened — e.g., `logs` is a typo (`'gradebookcomponent','logs'` concatenated into one string) in `createRole` that silently excludes the `logs` app from that one view.

2. **Picker groups by implementation, not function.** The current picker is a flat table of 62 model rows × 4 action columns, alphabetized by model name. Permissions that belong together functionally (e.g., gradebook permissions scattered across the `gradebookcomponent` app, the `studentgrade` app, and `activitytypepercentage`) render in different parts of the table. IT Admins must hunt by Django-model-name, not by feature.

3. **No bulk operation within a functional area.** Building a custom role like "Gradebook TA" — who should have all gradebook perms — requires ticking ~20 individual boxes across non-adjacent table rows.

4. **Dept-head dropdown shows everyone.** `accounts/views/department_admin.py:64` queries `CustomUser.objects.filter(is_active=True)` with no role filtering. Any active user (students included) appears in the dropdown.

## Locked design decisions (inherited from Phase 1/2 brainstorming)

These were fixed during the 2026-04-22 brainstorm that produced the three-phase plan:

- **Code-side `PERMISSION_CATEGORIES` dict**, not a DB model. Migrate to a model later only if IT Admins genuinely request taxonomy control.
- **No UI for creating custom permissions.** Devs add permissions alongside features (standard Django flow). IT Admin assigns existing permissions to custom roles via the existing `/roleList/` CRUD UI.
- **Single-tenant assumption.** No multi-tenancy work.
- **Hard cutover.** One PR, no shim period, no feature flag.

## Decisions made during this brainstorm (2026-04-23)

1. **Categorization axis: functional domain** (not Django app label). Categories describe *what work a permission enables*, crossing app boundaries. Example: "Gradebook" bundles perms from three Django apps together because IT Admins think in terms of features, not Django's code layout.

2. **Dept-head marker: hardcoded list.** `DEPARTMENT_HEAD_ROLE_NAMES = ("Program Head", "Principal")` in `roles/constants.py`. No schema change, no migration, no extra UI. Adding "Principal" is a one-line edit; it is already listed so the filter will pick up the Principal role as soon as it is created.

3. **Picker UX: collapsible sections + per-section select-all.** Each category is an HTML5 `<details>` accordion with a "Select all in this category" checkbox in the `<summary>`. Global "Check All" kept.

4. **Uncategorized-permission handling: strict allowlist + CI guard.** Only permissions listed in `PERMISSION_CATEGORIES` render in the picker. A test enumerates every permission from a list of Classedge-owned apps and fails CI if any is missing from the dict. No "Other" catch-all bucket.

5. **No data migration.** Existing role → permission assignments are preserved exactly. IT Admin can adjust any role after Phase 3 ships using the improved picker. In particular, the current accidental equivalence between `Program Head` and `Academic Director` (identical permission shapes) is left alone.

6. **CSV import/export deduped as part of Phase 3.** All three CSV endpoints currently embed their own copies of the app-label whitelist. Replacing them with the single `get_all_categorized_permissions()` helper is included in scope (same code smell, ~40 lines across 3 functions).

## Architecture

### New files

- **`roles/permission_categories.py`** — the single source of truth.
  ```python
  PERMISSION_CATEGORIES: dict[str, list[str]] = {
      "User Management": ["accounts.add_customuser", ...],
      "Roles & Permissions": ["roles.add_role", ...],
      ...
  }

  CATEGORY_ORDER: list[str] = [
      "User Management",
      "Roles & Permissions",
      ...
  ]

  EXPLICITLY_EXCLUDED_MODELS: set[str] = {
      # Operational/system models deliberately hidden from the picker.
      "retakerecord", "retakerecorddetail",
      "messagereadstatus", "messagetrashstatus", "messageunreadstatus",
      "msteams", "scormpackage",
      "studentprogress",
      "day", "section",
  }

  def get_categorized_permissions() -> list[tuple[str, list[Permission]]]:
      """[Classedge LMS] Returns [(category_label, [Permission, ...]), ...] in CATEGORY_ORDER.
      One DB query, ordered by CATEGORY_ORDER, used by role CRUD picker views."""

  def get_all_categorized_permissions() -> QuerySet[Permission]:
      """[Classedge LMS] Flat QuerySet of every permission appearing in PERMISSION_CATEGORIES.
      Used by CSV import/export views."""
  ```

  Codenames stored as `"app_label.codename"` (standard Django form). Flat `dict[str, list[str]]` — no classes. Category labels in English; wrap with `gettext_lazy` only if localization becomes a requirement later.

- **`roles/constants.py`** — adds:
  ```python
  DEPARTMENT_HEAD_ROLE_NAMES: tuple[str, ...] = ("Program Head", "Principal")
  ```

- **`roles/tests/test_categorization.py`** — CI guard enforcing categorization completeness. Three test methods:
  - `test_every_permission_from_our_apps_is_categorized` — iterates a `CLASSEDGE_APPS` list, asserts every Django auto-permission from those apps (minus `EXPLICITLY_EXCLUDED_MODELS`) appears in some category.
  - `test_no_permission_is_in_two_categories` — enforces the single-bucket invariant.
  - `test_every_categorized_codename_resolves_to_a_real_permission` — catches typos and orphan entries for deleted models.

- **`roles/tests/test_picker_rendering.py`** — three tests:
  - `test_picker_renders_all_categories_in_order` — IT Admin gets the addRole page; HTML contains each category header in `CATEGORY_ORDER`.
  - `test_picker_preselects_current_permissions_on_update` — updateRole page has correct checkboxes pre-checked.
  - `test_picker_hides_django_internal_permissions` — `auth.session`, admin log entries, celery perms are absent from the HTML.

- **`roles/tests/test_auth_smoke.py`** — end-to-end smoke tests of the auth surface that Phase 3 touches:
  - `test_register_login_logout_roundtrip`
  - `test_role_crud_roundtrip` (create a role with perms → update perms → view → delete)
  - `test_dept_head_dropdown_filters_to_program_head_role` (create a Program Head user and a Teacher user; assert only the Program Head appears in the candidate dropdown on the department-settings page)

### Files modified, not created

- **`roles/views.py`** — delete all 5 duplicated `excluded_models` / `content_type__app_label__in=[...]` blocks. Each view calls `get_categorized_permissions()` (for picker views) or `get_all_categorized_permissions()` (for CSV views). Net deletion from this file is substantial (~200 lines).

- **`roles/templates/role/addRole.html`** — replace the flat permissions table with the grouped-and-collapsible structure described below.

- **`roles/templates/role/updateRole.html`** — same change as `addRole.html`, with `{% if perm in role.permissions.all %}checked{% endif %}` on each checkbox.

- **`roles/templates/role/viewRole.html`** — same grouped structure, but read-only (checkboxes `disabled`).

- **`accounts/views/department_admin.py:64`** — one-line change to `candidate_heads`:
  ```python
  from roles.constants import DEPARTMENT_HEAD_ROLE_NAMES
  candidate_heads = (
      CustomUser.objects
      .filter(is_active=True, profile__role__name__in=DEPARTMENT_HEAD_ROLE_NAMES)
      .order_by("username")
  )
  ```

- Possibly **`accounts/tests/test_department_admin.py`** (or wherever dept-settings view tests live today — to be located during implementation) — amend existing `candidate_heads` assertions to cover the new filter behavior.

### Files explicitly NOT touched

- `roles/models.py` — Role schema unchanged. No `is_department_head_eligible` field (Q2 decision).
- Role data in the DB — no data migration.
- Permissions in the DB — no custom permissions added (standard Django auto-perms only).
- `roles/urls.py` — routing unchanged.
- The 127 `role.name.lower()` comparisons deferred to Phase 2b — out of scope.

## Data flow

### Picker render (add/update/view role)

1. View calls `get_categorized_permissions()`, receives `list[tuple[str, list[Permission]]]` in `CATEGORY_ORDER`.
2. View passes `categorized_permissions` (plus `role` for update/view) to the template.
3. Template iterates with one `<details>` per category:
   ```html
   {% for category, perms in categorized_permissions %}
     <details class="perm-category" open>
       <summary>
         <input type="checkbox" class="select-all-category" data-category="{{ forloop.counter }}">
         {{ category }} <span class="count">({{ perms|length }})</span>
       </summary>
       <table>
         {% for perm in perms %}
           <tr>
             <td>{{ perm.name }}</td>
             <td>
               <input type="checkbox" name="permissions" value="{{ perm.id }}"
                      class="perm-checkbox cat-{{ forloop.parentloop.counter }}"
                      {% if perm in role.permissions.all %}checked{% endif %}>
             </td>
           </tr>
         {% endfor %}
       </table>
     </details>
   {% endfor %}
   ```
4. Inline vanilla JS (no new dependencies):
   - Existing global "Check All" continues to work (targets `.perm-checkbox`).
   - New per-category `.select-all-category` toggles only `.cat-N` checkboxes scoped by `data-category`.
   - HTML5 `<details>` handles collapse natively. No JS for open/close.

### Form submit (create/update role)

No change from Phase 2. POST body `permissions=<id>&permissions=<id>&...` → `role.permissions.set(Permission.objects.filter(id__in=selected_permissions))`.

### Dept-head filter

Single `CustomUser.objects.filter(...)` change in `department_settings` view, described above. When the "Principal" role is eventually created via `/roleList/`, the filter immediately picks up Principal users — no further code change.

### CSV import/export

`import_roles_csv`, `export_roles_csv`, and `download_roles_template` each replace their inline whitelist with `get_all_categorized_permissions()`. CSV column headers (`Can view course`, etc.) continue to derive from the permissions themselves; no CSV format change.

## The proposed category list

| Category | Covers (models) |
|---|---|
| User Management | customuser, profile, displayimage, apikey, loginhistory, userlegalconsent, certificate, studentsdg |
| Roles & Permissions | role |
| Departments & Programs | department, program, schoolname, legaldocument, termandagreement |
| Academic Calendar | semester, term, schedule, retake, studentinvite, subjectenrollment |
| Course Content | course, subject, subjectcollaborator, module, subjectgradefinalization, sdg |
| Activities & Quizzes | activity, activitytype, activityquestion, questionchoice, quiztype, rubrics, rubricsitem, studentactivity, studentquestion, scorechangelog |
| Gradebook | gradebookcomponents, termgradebookcomponents, activitytypepercentage, transmutationrule, gradevisibilitysettings, studentgrade |
| Attendance | attendance, attendancestatus, teacher_attendance, teacherattendancepoints, studentparticipationscore |
| Teacher Evaluations | evaluationassignment, evaluationquestion, teacherevaluation, teacherevaluationresponse |
| Messaging | message, friendrequest, messagenotification |
| Classroom Tools | classroom, classroom_mode, screenshot |
| Reports & Logs | notification, studentactivitylog, subjectlog, useractivitylog, usersubjectlog, badge, attachment |

**Display order (`CATEGORY_ORDER`):** User Management → Roles & Permissions → Departments & Programs → Academic Calendar → Course Content → Activities & Quizzes → Gradebook → Attendance → Teacher Evaluations → Classroom Tools → Messaging → Reports & Logs.

Each category expands to every `add`/`view`/`change`/`delete` permission for the listed models — typically 20-60 individual permissions per category.

## Edge cases

**Handled by tests:**
- New permission added without categorization → `test_every_permission_from_our_apps_is_categorized` fails CI with the list of missing codenames.
- Codename typo in `PERMISSION_CATEGORIES` → `test_every_categorized_codename_resolves_to_a_real_permission` fails.
- Model deleted but its permission strings still in the dict → same test fails.
- Same permission listed in two categories → `test_no_permission_is_in_two_categories` fails.
- Principal role added later → no code change needed; `DEPARTMENT_HEAD_ROLE_NAMES` already lists it.

**Handled by design:**
- IT Admin's own view: IT Admin is `is_superuser=True`, bypasses all permission checks, so the picker's categorization is cosmetic for them. Intentional — picker is for editing *other* roles.
- User currently assigned as a department head but whose role isn't in `DEPARTMENT_HEAD_ROLE_NAMES`: stays assigned. Phase 3 only filters the dropdown, not the FK stored on `Department.head`. IT Admin may re-pick if they want to realign.

**Deliberately NOT handled** (out of scope):
- Multi-language category labels. Plain English for now; wrap with `gettext_lazy` if/when localization is a product requirement.
- Category editability via UI. Locked: devs curate.
- Migration of categorization to a DB model. Reconsider only if IT Admins request taxonomy control.

## Risks

- **Template change could break save flow.** Mitigated by `test_role_crud_roundtrip` which exercises POST → DB.
- **Collapsible `<details>` rendering.** Native HTML5, supported in every browser Classedge targets. No polyfill needed.
- **Dept-head dropdown narrows existing assignments.** Existing `Department.head` FK values are untouched; only the dropdown of *new* candidates narrows. Intentional.
- **Category decisions are subjective.** Changes to `PERMISSION_CATEGORIES` are pure code edits with no migration — easy to revisit post-merge.

## Test environment notes

Same gotchas as Phase 2 (from `project_classedge_it_admin_refactor.md`):
- Test DB is Neon Postgres. Always `--keepdb`; fresh rebuilds take ~5 min and lock the shared DB.
- `venv` at `~/classedge/env/`. `.env` must be symlinked into any worktree.
- Settings module `lms.settings`.

## Rollout

1. Single PR to `personal/main` (push to `personal` remote — Classedge policy).
2. No data migration, no schema migration.
3. Deploy: `git pull && python manage.py collectstatic && systemctl restart gunicorn` (standard).
4. No feature flag; old picker fully replaced on merge.

## Diff size estimate

- `roles/permission_categories.py` — ~250 lines (mostly the dict).
- Tests (`test_categorization.py`, `test_picker_rendering.py`, `test_auth_smoke.py`) — ~150 lines total, ~15 test methods.
- Template rewrite (`addRole.html` + `updateRole.html` + `viewRole.html`) — ~80 net lines changed.
- `roles/views.py` — ~200 lines deleted, ~60 added (net −140).
- `accounts/views/department_admin.py` — one-line change.
- `roles/constants.py` — new file, ~10 lines.

Net: approximately **+340 lines** across ~10 files. Estimated effort: **~2 days**, consistent with the Phase 3 estimate in the project memory.

## Out of scope (explicit)

- **Phase 2b** — the ~127 hardcoded `role.name.lower()` comparisons scattered across `course/views/`, `calendars/`, etc. Those are display/branching logic, not access gates, and require per-callsite semantic judgment. Deferred.
- **Aggregated Reports**, **SHS separation**, **two-step teacher import**, **IDE auto-grading**, **Teams/Meet/Zoom conferencing**, **native PPT viewer**, **LTI 1.3** — unrelated pending items tracked separately.
- **Academic Director vs Program Head de-duplication** — a data question, not a Phase 3 question. IT Admin can adjust via the new picker if desired.
