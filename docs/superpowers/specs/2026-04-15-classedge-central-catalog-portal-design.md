# Classedge — Central Catalog & Portal Foundation (Sub-project 1)

**Date:** 2026-04-15
**Status:** Design approved, ready for implementation planning
**Parent initiative:** Classedge Plus tier (central-content-consumer product tier)

---

## Context

Classedge is evolving into a three-tier product:

- **Core** — LMS platform only (the existing product as shipped today).
- **Plus** — LMS + centrally-authored content. The school consumes subject packages produced, reviewed, and pushed by a central content team. Schools can schedule, curate, and supplement, but cannot edit central content.
- **Prime** — LMS + per-school AI integration (original roadmap: school runs its own content generation, RAG tutor, at-risk dashboard, etc.).

Tiers are mutually exclusive: a school picks one of the three. Core and Plus/Prime do not overlap in feature set; Prime does not receive central content.

The three tiers are being built in order: Core exists today, **Plus ships next**, Prime follows.

The Plus tier itself is too large for a single design spec — it contains six major subsystems (central data models, central portal, school matching/push workflow, school-side consumption UI, textbook ingestion pipeline, AI generation pipeline). This spec covers **Sub-project 1 only**: the central catalog data model and the 3-role authoring portal. The remaining sub-projects will each get their own spec.

## Scope of this spec

**In scope:**
- New Django app `central_content/` living in the existing Classedge repo
- Central data models (`CentralSubject`, `CentralModule`, `CentralActivity`) that mirror the content-bearing fields of Classedge's existing `Subject`, `Module`, and `Activity` and add central-only metadata
- New user model `CentralStaff` with three roles (Editor, Reviewer, Publisher)
- Subdomain-based portal deployment at `central.classedge.app`
- Authoring portal UI (Django templates + HTMX): dashboard, subject/module/activity CRUD, state transitions, staff management
- `draft → in_review → approved` state machine with per-record audit log
- Manual content authoring (no AI generation yet)

**Out of scope (deferred to later sub-projects):**
- "Push to school" action and subject-matching workflow (Sub-project 2)
- Tenancy model extensions to tag a school as Plus-tier and snapshot central content into its tenant tables (Sub-project 2)
- School-side UI for receiving, scheduling, curating, and supplementing pushed content (Sub-project 3)
- Textbook ingestion, curriculum planning, and AI generation pipeline (Sub-project 4)
- Quiz question authoring (question-level models and UI — future spec)
- Rich text editing beyond stock Django textareas
- End-to-end browser automation tests
- SSO, MFA, or auth flows more sophisticated than email + password
- Billing, pricing, tier provisioning UX

## Design decisions (converged during brainstorming)

| # | Decision | Chosen | Why |
|---|---|---|---|
| 1 | Tier model | Three tiers, whole-school, mutually exclusive | Simpler business model; no per-subject mixing |
| 2 | Build order after Core | Plus first, then Prime | Lower risk; central team controls content quality before handing AI to schools; pipeline reusable for Prime |
| 3 | Plus scope decomposition | Four sub-projects (catalog/portal → push → school-side → generation) | Single spec is too large; ship incrementally |
| 4 | Catalog physical model | Same DB, copy-on-assign snapshot | Version stability per school, no cross-tenant live queries |
| 5 | Portal location | New Django app, subdomain `central.classedge.app`, separate settings, shared DB | Clean cookie + URL isolation, single deployment |
| 6 | Central data shape | Mirror content-bearing fields only, plus central-only metadata | Keeps eventual copy-on-assign a near-trivial record clone, excludes school-operational junk |
| 7 | User model | New `CentralStaff` model, separate from `accounts.CustomUser` | School users and staff are different audiences; avoids conditional logic across the existing codebase |
| 8 | Roles | Editor / Reviewer / Publisher (three explicit roles) | Separates content authoring, QA, and distribution; Publisher is the only superuser equivalent |
| 9 | State machine | `draft → in_review → approved`, with `request-changes` and Publisher-only `reopen` | Minimal viable editorial workflow |
| 10 | Frontend stack | Django templates + HTMX + Tailwind | Matches existing Classedge conventions; no new SPA build |

## Architecture & Deployment

### Codebase

New Django app `central_content/` inside the existing Classedge repo. No new repos. Same virtualenv, same `requirements.txt`, same migrations pipeline.

### Runtime separation

Central portal runs on a separate subdomain with its own settings module:

- `lms/settings/central.py` inherits from base settings, overrides `ROOT_URLCONF = 'central_content.urls'`, restricts `ALLOWED_HOSTS` to `central.classedge.app`, and disables school-facing middleware that is irrelevant or harmful in the central context (school tenant resolution, student session enforcement, etc.).
- Main Classedge app continues on its existing domain with its existing settings module, completely unchanged.
- Both processes share the same Postgres database and (when later introduced) the same Redis/Celery infra. No cross-service sync is needed because everything lives in one DB.
- Deployment is one additional Gunicorn process in the existing container or host, pointed at the `central` settings module.

### Why separate subdomain rather than one shared URL tree

- Session cookies are scoped to the subdomain, so a school user session at `schoolx.classedge.app` cannot bleed into central access (and vice versa).
- URL tree stays clean: central has its own root, school has its own root, no namespace prefix gymnastics.
- Future operational split (separate deploy cadence, separate WAF rules) becomes a config change, not a rewrite.

### Why not an entirely separate service

The central catalog shares the database with school tenants so that Sub-project 2's copy-on-assign can be an in-process ORM operation. Splitting central into its own service now would force a cross-service content-sync protocol in Sub-project 2, which is complexity without benefit at the current scale.

## User & Auth Model

### `CentralStaff` model

```text
CentralStaff
  id              BigAutoField
  email           EmailField, unique, primary login identifier
  full_name       CharField(150)
  role            CharField(choices=Editor|Reviewer|Publisher)
  is_active       BooleanField(default=True)
  password        CharField (Django's built-in hasher)
  date_joined     DateTimeField(auto_now_add)
  last_login      DateTimeField(null=True, blank=True)
```

A single role per user. If the content team later grows to require a user in multiple roles, upgrading to a `ManyToMany` of roles is a migration and a permission-layer change — not a design change.

### Why not reuse `accounts.CustomUser`

- `CustomUser` is already coupled to school-side semantics: student/teacher/parent profiles, school foreign keys, roster queries. Reusing it would require conditional logic at every consumer.
- A separate model gives the central team a clean audit trail and the option of different password policies, MFA, or SSO later without touching school auth.
- Permission reasoning is simpler: "is this user `CentralStaff` with role `X`" vs. "is this `CustomUser` in group `X` with no conflicting school profile."

### Auth flow

- Login page at `central.classedge.app/login` — email and password, stock Django form.
- Session cookie scoped to `central.classedge.app` only (not shared with school subdomains).
- Standard Django session authentication. No JWT, no SSO, no MFA in this sub-project.
- First `CentralStaff` (role `Publisher`) is created via a management command: `python manage.py create_central_staff --email ... --role Publisher`. This avoids a chicken-and-egg UI problem on first deploy.
- Password reset uses Django's stock password-reset views, wired to the central portal's own templates.

### Permissions matrix

| Action | Editor | Reviewer | Publisher |
|---|---|---|---|
| Create/edit draft content | ✅ | ✅ | ✅ |
| Submit draft for review | ✅ | ✅ | ✅ |
| Approve `in_review` content | ❌ | ✅ | ✅ |
| Request changes on `in_review` | ❌ | ✅ | ✅ |
| Reopen approved content | ❌ | ❌ | ✅ |
| View content in any state | ✅ | ✅ | ✅ |
| Manage `CentralStaff` users | ❌ | ❌ | ✅ |
| Hard-delete content | ❌ | ❌ | ✅ |

Enforcement lives at the view layer via:

- A DRF permission class `CentralRolePermission` for any API endpoints.
- A decorator `@central_role_required(*allowed_roles)` for classic Django views.
- No permission logic in models or managers — views and serializers are the policy boundary.

Editors may edit each other's drafts (collaborative mode). UI hides edit buttons from non-authors by default but the API permits it — this keeps the permission matrix simple and avoids an ownership rule that would need to be revisited later.

## Data Model

### Design principle

The central content tables should mirror Classedge's existing content-bearing fields, and **only** those fields. School-operational fields (teacher assignment, scheduling, enrollment, notifications) do not belong in the central catalog because they only make sense once content is attached to a specific school's class and term. Those fields are populated at push time (Sub-project 2) or remain at their default.

### `CentralSubject`

```text
# Content-bearing (will be copied to school tenant by Sub-project 2)
subject_name               CharField(200)
subject_descriptive_title  CharField(100, blank)
subject_short_name         CharField(30, blank)
subject_photo              ImageField(upload_to=..., blank)
subject_description        TextField(blank)
subject_code               CharField(30, blank)
subject_type               CharField(choices=Lec|Lab, blank)
unit                       PositiveIntegerField(default=3)
target_sdgs                M2M(subject.SDG, blank)

# Central-only metadata (never copied to school)
target_grade_level         CharField(50, blank)   # e.g. "Grade 7", "Year 1 College"
target_curriculum          CharField(100, blank)  # e.g. "K-12 DepEd Philippines"
version                    PositiveIntegerField(default=1)
state                      CharField(choices=draft|in_review|approved, default=draft)
created_by                 FK(CentralStaff, PROTECT, related='subjects_created')
submitted_by               FK(CentralStaff, SET_NULL, null, related='subjects_submitted')
reviewed_by                FK(CentralStaff, SET_NULL, null, related='subjects_reviewed')
review_notes               TextField(blank)
source_notes               TextField(blank)
created_at                 DateTimeField(auto_now_add)
updated_at                 DateTimeField(auto_now)
```

### `CentralModule`

Corresponds to a Classedge lesson.

```text
central_subject   FK(CentralSubject, CASCADE, related='modules')
file_name         CharField(100)        # lesson title
description       TextField(blank)
file              FileField(upload_to=..., blank)
url               URLField(max_length=1500, blank)
iframe_code       TextField(blank)
order             PositiveIntegerField(default=0)

# Central-only
state             CharField(choices=draft|in_review|approved, default=draft)
created_by        FK(CentralStaff, PROTECT)
reviewed_by       FK(CentralStaff, SET_NULL, null)
review_notes      TextField(blank)
created_at        DateTimeField(auto_now_add)
updated_at        DateTimeField(auto_now)

Meta.ordering = ['order']
```

Note: the existing school `Module.save()` writes to `SubjectLog` and triggers teacher/student notifications. `CentralModule.save()` does **not** replicate that logic — it is meaningless at the central level. Central saves are plain DB writes.

### `CentralActivity`

```text
central_subject     FK(CentralSubject, CASCADE, related='activities')
related_modules     M2M(CentralModule, blank)
activity_name       CharField(100)
activity_instruction  TextField(blank)
activity_type       FK(activity.ActivityType, PROTECT)
max_score           PositiveIntegerField(default=100)
time_duration       PositiveIntegerField(default=0)
passing_score       FloatField(default=0)
passing_score_type  CharField(choices=number|percentage, default=percentage)
max_retake          PositiveIntegerField(default=0)
retake_method       CharField(choices=..., default=highest)
shuffle_questions   BooleanField(default=False)
is_graded           BooleanField(default=True)

# Central-only
state               CharField(choices=draft|in_review|approved, default=draft)
created_by          FK(CentralStaff, PROTECT)
reviewed_by         FK(CentralStaff, SET_NULL, null)
review_notes        TextField(blank)
created_at          DateTimeField(auto_now_add)
updated_at          DateTimeField(auto_now)
```

### `AuditLogEntry`

```text
content_type   FK(ContentType)
object_id      PositiveIntegerField
from_state     CharField(20)
to_state       CharField(20)
actor          FK(CentralStaff, PROTECT)
notes          TextField(blank)
created_at     DateTimeField(auto_now_add)
```

One row per successful state transition, queryable per record for the review history UI.

### Fields deliberately excluded from central mirrors

These fields exist on school models but not on central mirrors, because they are school-operational:

- `assign_teacher`, `substitute_teacher`, `allow_substitute_teacher`, `collaborators`
- `max_number_of_enrollees`, `number_of_enrollees`, `room_number`, `status` (Ongoing/Available/Closed)
- `term`, `start_date`, `end_date`, `start_time`, `end_time`
- `remedial`, `remedial_students`, `classroom_mode`
- `display_lesson_for_selected_users`
- `SubjectGradeFinalization` (grade finalization is per-school-per-semester and has no central analogue)

These are populated when content is copied into a school tenant (Sub-project 2) or remain unset because they do not make sense per-curriculum.

### Shared lookups (reused, not mirrored)

- `subject.SDG` — global taxonomy, no school coupling. Central and school both reference it.
- `activity.ActivityType` — global lookup (`Quiz`, `Assignment`, `Exam`, etc.). Reused as-is.
- `activity.QuizType` and question-level models — **not used** in Sub-project 1. Central activities in this sub-project carry metadata only; question authoring is a future spec.

### Migrations

One initial migration creating all central tables and the `CentralStaff` model. No changes to existing Classedge tables. Foreign keys to existing tables (`SDG`, `ActivityType`) are ordinary Django FKs in the same DB.

## State Machine & Permissions

### States

`draft → in_review → approved`

### Transitions

| From | To | Trigger | Who |
|---|---|---|---|
| `draft` | `in_review` | Submit for review | Editor, Reviewer, Publisher |
| `in_review` | `draft` | Request changes (requires `review_notes`) | Reviewer, Publisher |
| `in_review` | `approved` | Approve | Reviewer, Publisher |
| `approved` | `draft` | Reopen (bumps `version` on next submit) | Publisher only |

### Rules

- A `CentralSubject` cannot be approved while any of its child `CentralModule` or `CentralActivity` records are in `draft` or `in_review`. Enforced in the view/serializer layer with an explicit error message naming the blocking children. Not a DB constraint.
- `approved` records are read-only in the portal UI. Any change requires `Reopen`, which is a Publisher-only action.
- `Reopen` on a `CentralSubject` also reverts all of its child modules and activities to `draft` (so the next approval pass exercises the full review cycle on whatever changed). Version integer is bumped so Sub-project 2's re-push logic can detect newer versions later.
- Every successful transition writes exactly one `AuditLogEntry` row. Failed transitions write none.

### Permissions enforcement

- `CentralRolePermission` DRF class handles API endpoints.
- `@central_role_required(*roles)` decorator handles classic Django views.
- No model/manager-level permission logic.
- Authorization is checked before the transition is attempted; bad requests return 403.

## Portal UI & URLs

### Stack

Django templates + HTMX + Tailwind.

- Matches existing Classedge conventions (templates throughout `course/`, `module/`, `activity/`).
- HTMX provides the interactivity needed for inline editing, modal forms, and state-transition buttons without a React build step.
- A React migration for the full Classedge product is on the product roadmap, but forking the frontend stack only for the central portal would split the frontend story.

### URL tree

All routes rooted at `central.classedge.app`, served by `central_content/urls.py`:

```text
/                                          dashboard
/login                                     CentralStaff login
/logout

/subjects/                                 list (filter by state, search)
/subjects/new                              create draft
/subjects/<id>/                            detail (tabs: Overview, Modules, Activities, History)
/subjects/<id>/edit                        edit (only when state == draft)
/subjects/<id>/submit                      POST: draft → in_review
/subjects/<id>/approve                     POST: in_review → approved
/subjects/<id>/request-changes             POST: in_review → draft
/subjects/<id>/reopen                      POST: approved → draft (Publisher only)
/subjects/<id>/history                     audit log

/subjects/<sid>/modules/new
/subjects/<sid>/modules/<id>/
/subjects/<sid>/modules/<id>/edit
/subjects/<sid>/modules/<id>/submit
/subjects/<sid>/modules/<id>/approve
/subjects/<sid>/modules/<id>/request-changes

/subjects/<sid>/activities/new
/subjects/<sid>/activities/<id>/
/subjects/<sid>/activities/<id>/edit
/subjects/<sid>/activities/<id>/submit
/subjects/<sid>/activities/<id>/approve
/subjects/<sid>/activities/<id>/request-changes

/staff/                                    list (Publisher only)
/staff/new                                 create (Publisher only)
/staff/<id>/edit                           edit/deactivate (Publisher only)
```

### Key UI surfaces

1. **Dashboard** — counts of draft / in_review / approved per content type; recent-activity feed (last 20 audit entries); "Needs review" queue for Reviewers and Publishers.

2. **Subject list** — table with columns: name, grade level, curriculum, state, modules count, activities count, `updated_at`, owner. Filters: state, grade level, curriculum, owner. Search over name and code. Bulk actions deferred.

3. **Subject detail** — state badge, contextual action buttons (only show transitions the current user can perform in the current state), tabs:
   - **Overview** — metadata form, inline-editable when `state == draft`.
   - **Modules** — ordered list, drag-handle reorder, inline create-module form, state badges per row.
   - **Activities** — grouped by `activity_type`.
   - **History** — chronological audit log for the subject and its children.

4. **Module/Activity detail** — metadata form, state-transition buttons, `review_notes` prominently displayed when returned from review, file upload for modules, link back to parent subject.

5. **Staff management** — simple CRUD for Publishers only. Fields: email, full name, role, `is_active`. Passwords initialized via email link (Django's stock password-reset flow wired to central templates).

### Inline editing pattern

- Click any field on a draft record → transforms into an input via HTMX swap → saves on blur or Enter → toast on success.
- Full-page edit forms remain available for bulk field changes, per the user's stated preference for both patterns.

### What the UI deliberately does NOT include in this sub-project

- "Push to school" button or any school-assignment workflow (Sub-project 2)
- "Generate with AI" button (Sub-project 4)
- Quiz question authoring UI (future)
- Student-preview mode (add in Sub-project 3 once the school-side consumption UI is built)
- Rich text editor — stock Django textareas suffice for the first cut

## Testing Approach

### Test layout

```text
central_content/tests/
  __init__.py
  factories.py              factory_boy fixtures for CentralStaff + content
  test_models.py            model validation, constraints
  test_state_machine.py     every legal and illegal transition
  test_permissions.py       role × action matrix
  test_views_subjects.py    subject CRUD + transition endpoints
  test_views_modules.py     module CRUD + transition endpoints
  test_views_activities.py  activity CRUD + transition endpoints
  test_views_staff.py       staff management (Publisher-only)
  test_auth.py              login, subdomain cookie scope, logout
  test_audit_log.py         audit invariants
```

### Required test coverage

1. **State machine correctness** — every legal transition works; every illegal transition is rejected (no skipping states, no backwards jumps except `reopen`, no approving a subject with unresolved children).
2. **Role × action matrix** — parameterized tests covering every (role, action) pair against expected allow/deny. One test case per row of the permissions table.
3. **Audit log invariants** — every successful transition creates exactly one `AuditLogEntry` with correct `from_state`, `to_state`, `actor`; failed transitions create none.
4. **Auth isolation** — a session cookie from a school subdomain does not grant access to `central.classedge.app` endpoints; a `CentralStaff` session does not grant access to school endpoints.
5. **Version bump on reopen** — reopening an approved `CentralSubject` increments `version`; child modules and activities revert to `draft`.
6. **Cascading approval gate** — `CentralSubject.approve` is blocked when any child is `draft` or `in_review`; error message names the blockers.

### Out of scope for tests

- Selenium/Playwright end-to-end browser tests
- Load testing
- Data-migration tests (no migrations of existing data in this sub-project)

### TDD discipline

Every implementation task derived from this spec follows red-green-refactor: failing test first, minimal code to pass, refactor without breaking the test.

### Coverage target

No percentage target. Instead: every public view and every state transition must have at least one positive and one negative test. Private helpers are tested indirectly through the public surface.

## Deliverables

- `central_content/` Django app registered in `INSTALLED_APPS`
- `lms/settings/central.py` settings module
- One initial migration
- Management command `create_central_staff`
- Templates under `central_content/templates/central_content/`
- URL configuration under `central_content/urls.py`
- Test suite under `central_content/tests/` covering the scenarios above
- Bootstrap Gunicorn/process entry for the central subdomain (deployment config change)

## Open questions (to resolve during implementation planning, not blocking this spec)

- Exact file-storage backend for `CentralModule.file` (same S3 bucket as school content, or a separate central bucket? — operational choice, no design impact)
- Whether `CentralSubject.subject_photo` is mandatory or optional on create (product UX decision)
- Password policy for `CentralStaff` (default Django rules suffice unless the content team has stricter requirements)
