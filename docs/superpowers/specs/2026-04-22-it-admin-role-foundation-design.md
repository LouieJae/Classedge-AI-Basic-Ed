# IT Admin Role Foundation — Design

**Status:** Drafted 2026-04-22
**Phase:** 1 of 3 in the user/role/permission refactor
**Branch:** `feat/it-admin-role-foundation`

## 1. Motivation

Classedge LMS currently uses a mix of:

- Role-name string matching in decorators (`@admin_required`, `@teacher_required`, etc.) — 28+ callsites.
- Django's native permission system, used sparingly via `@permission_required(...)`.
- A singleton `Role(name="Admin")` whose 24 explicit permissions are bypassed in practice because `@admin_required` matches by name.

Gaps identified during manual review:

- No clear top-level "deployment owner" role. The `Admin` role is functionally a superuser at the decorator level but isn't wired as one at the Django level.
- A duplicate `Role(name="teacher")` (id=11) orphan coexists with `Role(name="Teacher")` (id=5).
- Hardcoded excluded models and app-label whitelist in `roles/views.py` hide permissions from the role-editing UI.
- No seed/management command to bootstrap a fresh deploy with a working admin user.

This spec covers **Phase 1 only** — the foundation. Later phases (covered in separate specs):

- **Phase 2:** Replace all role-name decorators with `@permission_required("codename")`.
- **Phase 3:** Permission-picker categorization (code-side dict), hardcoded-exclusion cleanup, dept-head picker filtering, auth-flow tests.

## 2. Locked decisions

| # | Decision |
|---|----------|
| 1 | Defer multi-tenancy. Classedge remains one-school-per-deployment. |
| 2 | IT Admin **replaces** the existing Admin role (rename + migrate). No coexistence. |
| 3 | Decorator refactor (Phase 2) will replace role-name checks with `@permission_required("codename")` across all views. |
| 4 | Permission categorization will use a code-side dict (Phase 3), not a DB model. |
| 5 | IT Admin does **not** create custom permissions via UI. Permissions are dev-declared; IT Admin assigns existing ones to custom roles. |
| 6 | IT Admin users have `is_superuser = True`. Django's native superuser bypass is the mechanism for god-mode. |
| 7 | IT Admin is an **exclusive** role: one user = one role; no impersonation of other roles; dedicated IT Admin dashboard and UI. |

## 3. Scope of Phase 1

**In scope:**

- Role rename (`Admin` → `IT Admin`) via data migration.
- Orphan role cleanup (delete `Role(name="teacher")` id=11, merge its 1 user into `Role(name="Teacher")` id=5).
- Bidirectional invariant: `Profile.role == "IT Admin"` ⇔ `CustomUser.is_superuser == True`, enforced via `post_save` signal.
- `@admin_required` decorator updated to match `is_superuser` (compatible with Phase 2 eventual removal).
- New IT Admin dashboard at `/it-admin/` — a landing page linking to existing CRUD screens (users, roles, departments). No new CRUD built here.
- Dashboard routing: IT Admin users redirected to `/it-admin/` when they hit `/dashboard/`.
- `seed_it_admin` management command for fresh-deploy bootstrap.
- Tests covering the above.

**Out of scope for Phase 1:**

- Decorator refactor beyond `@admin_required`.
- Any changes to non-admin role UX, permissions, or dashboards.
- `PermissionCategory` model or UI.
- User-creation UX changes (admins continue to use existing screens).
- Self-service signup.

## 4. Architecture

### 4.1 Schema changes

**None.** `Role`, `Profile`, `CustomUser` models unchanged. Everything is data migrations plus code (signals, views, templates, management command).

### 4.2 Data migrations (order matters)

1. **`roles/migrations/NNNN_rename_admin_to_it_admin.py`** — `Role.objects.filter(name="Admin").update(name="IT Admin")`. Reverse: update in opposite direction. Idempotent.
2. **`roles/migrations/NNNN_merge_orphan_teacher_role.py`** — For each profile on `Role(name="teacher")`, reassign to `Role(name="Teacher")`. Delete the orphan role. Reverse: recreate the orphan as an empty row (lossy on profile reassignments; acceptable because only 1 user affected).
3. **`accounts/migrations/NNNN_backfill_it_admin_superuser.py`** — For every profile with role `"IT Admin"`, ensure `user.is_superuser = True`. Do NOT yank superuser flag from any other user. Reverse: no-op.

### 4.3 Signal (new file: `accounts/signals.py`)

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from accounts.models.account_models import Profile


@receiver(post_save, sender=Profile)
def sync_it_admin_superuser(sender, instance, **kwargs):
    """[Classedge LMS] Keep is_superuser aligned with IT Admin role assignment."""
    user = instance.user
    should_be_superuser = bool(instance.role and instance.role.name == "IT Admin")
    if user.is_superuser != should_be_superuser:
        user.is_superuser = should_be_superuser
        user.save(update_fields=["is_superuser"])
```

Wired via `accounts/apps.py`:

```python
def ready(self):
    from accounts import signals  # noqa: F401
```

No `Profile.clean()` validator. The signal is the single enforcement point; `clean()` would create a brittle double-gate.

### 4.4 `@admin_required` update

`roles/decorators.py` currently checks `role.name.lower() == "admin"`. Phase 1 change: short-circuit on `is_superuser`. The role-name match is removed in the same edit.

```python
def admin_required(view):
    @wraps(view)
    def _wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_superuser:
            return view(request, *args, **kwargs)
        raise PermissionDenied
    return _wrapper
```

Post-migration, all former Admin users are IT Admins and all IT Admins are `is_superuser=True`, so behavior is preserved. Phase 2 removes this decorator entirely and replaces callsites with `@permission_required`.

### 4.5 IT Admin dashboard

#### URL

```python
# accounts/urls.py
path("it-admin/", it_admin_dashboard, name="it_admin_dashboard"),
```

One URL in Phase 1. No redirect shortcuts for `it-admin/users/` etc. — the landing links hit existing paths directly (`/roles/roleList/`, `/departments/`, etc.).

#### View (`accounts/views/it_admin.py`)

```python
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from accounts.models.account_models import CustomUser
from accounts.models.department_models import Department
from roles.models import Role


def _is_it_admin(user):
    return user.is_authenticated and user.is_superuser


@login_required
@user_passes_test(_is_it_admin)
def it_admin_dashboard(request):
    """[Classedge LMS] IT Admin landing. Links to users/roles/depts; shows counts."""
    context = {
        "user_count": CustomUser.objects.filter(is_active=True).count(),
        "role_count": Role.objects.count(),
        "department_count": Department.objects.count(),
        "superuser_count": CustomUser.objects.filter(is_superuser=True).count(),
    }
    return render(request, "it_admin/dashboard.html", context)
```

Gating is `is_superuser`, not role-name. Aligned with the signal invariant.

#### Templates

- **`templates/it_admin_base.html`** — thin layout: sidebar (Dashboard, Users, Roles, Departments, Back to site) + content block. Reuses the Bricolage/Inter Tight + cream/forest/gold palette from `teacher_base.html`. No new design system.
- **`templates/it_admin/dashboard.html`** — four counter cards (users / roles / departments / superusers), each with a "Manage →" link to the existing CRUD screens. Pure index. No forms.

### 4.6 Dashboard routing

`accounts/views/dashboard.py` currently branches teacher vs student vs default. Add a first branch:

```python
if request.user.is_superuser:
    return redirect("it_admin_dashboard")
```

So IT Admin (or any Django superuser) lands on `/it-admin/` when they hit `/dashboard/`. Other roles unchanged.

### 4.7 `seed_it_admin` management command

**Location:** `accounts/management/commands/seed_it_admin.py`

**Purpose:** fresh-deploy bootstrap. Ensures `Role(name="IT Admin")` exists and that at least one user has it (and thus `is_superuser=True` via the signal). Idempotent.

**Flags:**

- `--email EMAIL` (overrides `IT_ADMIN_EMAIL` env var)
- `--password PASSWORD` (overrides `IT_ADMIN_PASSWORD` env var; supports `-` for stdin)
- `--username USERNAME` (defaults to email prefix)
- `--dry-run` (print intent, change nothing)
- `--force-reset-password` (only resets password on an existing user if set)

**Behavior:**

1. `Role.objects.get_or_create(name="IT Admin")`. Log if created.
2. Resolve email/password/username from flags → env vars → interactive prompt (when `DEBUG=True`). If `DEBUG=False` and not provided, exit 1 with clear message.
3. Look up user by email:
   - Exists → set `Profile.role` to IT Admin (signal flips `is_superuser=True`). Skip password reset unless `--force-reset-password`.
   - Missing → create `CustomUser` + `Profile(role=IT Admin)`.
4. Print summary: email / username / role / `is_superuser` state.

**Does NOT:**

- Revoke IT Admin from other users.
- Create Department or other data.
- Touch the Admin→IT Admin rename (handled by data migration).

## 5. Testing

### 5.1 Migration tests

- **`roles/tests/test_migration_rename_admin.py`** — before migration: `Role(name="Admin")` exists; after: only `Role(name="IT Admin")` exists.
- **`roles/tests/test_migration_merge_teacher_orphan.py`** — before: 2 rows matching `name ilike 'teacher'`; after: 1 row; profiles reassigned.

(Migration tests use `django-test-migrations` if available, otherwise simple post-migrate state assertions.)

### 5.2 Signal tests (`accounts/tests/test_it_admin_signal.py`)

- Assign IT Admin role to a user → `is_superuser == True`.
- Reassign to Teacher → `is_superuser == False`.
- No role → `is_superuser == False`.
- Pre-existing Django superuser with IT Admin role assignment → `is_superuser` stays True (idempotent, no spurious save).

### 5.3 Decorator test (`accounts/tests/test_admin_required_decorator.py`)

- Superuser passes.
- Non-superuser (Teacher, Student) denied.
- Anonymous denied.

### 5.4 Dashboard access (`accounts/tests/test_it_admin_dashboard.py`)

- IT Admin → GET `/it-admin/` → 200 with correct counts.
- Teacher → GET `/it-admin/` → 403 or login redirect.
- Anonymous → GET `/it-admin/` → login redirect.

### 5.5 Dashboard routing (`accounts/tests/test_dashboard_routing.py`)

- Superuser hitting `/dashboard/` → 302 redirect to `/it-admin/`.
- Teacher hitting `/dashboard/` → existing teacher flow unchanged.

### 5.6 Seeder tests (`accounts/tests/test_seed_it_admin.py`)

- Fresh DB → creates role + user → second invocation no-ops (idempotent).
- Existing user with same email → grants IT Admin role, no password reset unless `--force-reset-password`.
- Missing email + `DEBUG=False` → exits with error.
- `--dry-run` → no DB changes.

## 6. Rollout

### 6.1 Pre-deploy (staging)

1. Full test suite green.
2. `python manage.py migrate --plan` confirms order.
3. Run migrations against a staging clone; assert:
   - `Role(name="Admin")` absent; `Role(name="IT Admin")` present.
   - `Role(name="teacher")` orphan absent.
   - `admin@gmail.com` still `is_superuser=True`; role is IT Admin.
4. Log in as existing admin → lands on `/it-admin/`.
5. Log in as a teacher → unchanged dashboard.

### 6.2 Deploy (prod)

1. Announce ~5 min maintenance window.
2. `pg_dump` backup of prod DB. Non-negotiable.
3. Deploy branch; run `python manage.py migrate`.
4. Optional `seed_it_admin` run if adding a second IT Admin.
5. Smoke-test `/it-admin/` as existing admin.
6. Tail logs for 15 min.

### 6.3 Rollback

1. **Code-only:** `git revert` + redeploy. Restores `@admin_required` role-name match.
2. **Data-only:** `python manage.py migrate roles <prev>` reverses rename cleanly; orphan-merge reverse recreates empty role but does NOT restore profile assignments (lossy).
3. **Full rollback:** restore `pg_dump` from step 2 of deploy.

### 6.4 Post-deploy tasks

- Grep for any remaining `"Admin"` / `"admin"` / `"ADMIN"` string matches in role-name context; flag for Phase 2 cleanup.
- Confirm Phase 2 planning can begin.

## 7. Deliverables checklist

- [ ] 3 data migrations (rename, orphan-merge, superuser-backfill)
- [ ] `accounts/signals.py` with `sync_it_admin_superuser`
- [ ] `accounts/apps.py` updated to load signals
- [ ] `@admin_required` simplified to `is_superuser` check
- [ ] `accounts/views/it_admin.py` with `it_admin_dashboard`
- [ ] `templates/it_admin_base.html` + `templates/it_admin/dashboard.html`
- [ ] `accounts/urls.py` entry for `it_admin_dashboard`
- [ ] Dashboard-routing branch in `accounts/views/dashboard.py`
- [ ] `accounts/management/commands/seed_it_admin.py`
- [ ] Tests: migration × 2, signal, decorator, dashboard access, routing, seeder
- [ ] Manual QA: existing admin → lands on `/it-admin/`; teacher → unchanged

## 8. Open risks

| Risk | Mitigation |
|------|-----------|
| A non-IT-Admin Django superuser exists | Benign — they still pass; they'll land on `/it-admin/` if they log in. Verify no legacy superusers pre-deploy. |
| Orphan-merge migration is lossy on reverse | Accept. Only 1 user affected. `pg_dump` backup covers worst-case. |
| Signal-driven `is_superuser` edits could trigger `post_save` loops | Signal only saves when the flag value actually differs. Single save, no loop. |
| `@admin_required` still used post-Phase-1 | Expected. Removal is Phase 2 scope. |
| Future IT Admin created via shell without going through Profile | Signal only fires on Profile save. Creating a user with `is_superuser=True` directly won't assign IT Admin role. Recovery: `Profile.objects.filter(user=u).update(role=IT_ADMIN_ROLE)`. |

## 9. What comes after Phase 1

**Phase 2:** Replace all `@admin_required` / `@teacher_required` / `@student_required` / `@teacher_or_admin_required` usages with `@permission_required("app.codename")`. Grant each non-IT-Admin role the perms its views currently need. Retire legacy decorators.

**Phase 3:** `roles/permission_categories.py` code-side dict; role CRUD template renders permission picker grouped by category; delete hardcoded `excluded_models` + app whitelist in `roles/views.py`; filter `candidate_heads` dept picker to head-eligible roles; auth-flow smoke tests.
