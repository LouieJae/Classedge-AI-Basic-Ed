# IT Admin Role Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Phase 1 of the user/role/permission refactor — rename Admin → IT Admin, enforce `IT Admin role ⇔ is_superuser` invariant via a post_save signal, clean up the orphan `teacher` role, ship a minimal IT Admin landing dashboard, and provide a `seed_it_admin` management command.

**Architecture:** No schema changes. Three sequential data migrations rename the role, merge the orphan, and backfill `is_superuser` for existing IT Admin profiles. A `post_save` signal on `Profile` keeps `is_superuser` in lockstep with the IT Admin role. `@admin_required` is reduced to a single `is_superuser` check. A dedicated `/it-admin/` URL serves a counter dashboard; `/dashboard/` reroutes superusers to it.

**Tech Stack:** Django 5.0.7, PostgreSQL (Neon), Python 3.12, existing template system (Bricolage / Inter Tight palette from `teacher_base.html`).

**Spec:** `~/classedge/docs/superpowers/specs/2026-04-22-it-admin-role-foundation-design.md`

**Branch:** `feat/it-admin-role-foundation`

---

## File Structure

**Files to create:**
- `roles/migrations/0002_rename_admin_to_it_admin.py` — data migration
- `roles/migrations/0003_merge_orphan_teacher_role.py` — data migration
- `accounts/migrations/0008_backfill_it_admin_superuser.py` — data migration
- `accounts/signals.py` — `sync_it_admin_superuser` post_save handler
- `accounts/views/it_admin.py` — `it_admin_dashboard` view + helper
- `templates/it_admin_base.html` — sidebar + content layout
- `templates/it_admin/dashboard.html` — counter cards landing page
- `accounts/management/__init__.py` (if missing)
- `accounts/management/commands/__init__.py` (if missing)
- `accounts/management/commands/seed_it_admin.py` — bootstrap command
- `accounts/tests/test_it_admin_signal.py` — signal invariant tests
- `accounts/tests/test_it_admin_dashboard.py` — dashboard access + routing tests
- `accounts/tests/test_seed_it_admin.py` — seeder tests
- `roles/tests/__init__.py` (if missing)
- `roles/tests/test_admin_required_decorator.py` — decorator gate tests
- `roles/tests/test_role_data_state.py` — post-migration data assertions

**Files to modify:**
- `roles/decorators.py` — simplify `admin_required` to `is_superuser`-only
- `accounts/apps.py:8-9` — load `accounts.signals` on app ready
- `accounts/urls.py` — add `it_admin_dashboard` route
- `accounts/views/__init__.py` — export `it_admin_dashboard`
- `accounts/views/dashboard.py:48-57` — branch superusers to `/it-admin/`

---

## Task 1: Workspace setup + sanity check

**Files:**
- Read-only inspection

- [ ] **Step 1: Confirm branch state**

Run:

```bash
cd ~/classedge && git status && git branch --show-current
```

Expected: `On branch feat/it-admin-role-foundation` and `nothing to commit, working tree clean` (the spec from brainstorming is already committed). If on a different branch, switch with `git checkout feat/it-admin-role-foundation`. If the branch doesn't exist, create it from main: `git checkout main && git pull personal main && git checkout -b feat/it-admin-role-foundation`.

- [ ] **Step 2: Confirm DB baseline**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py shell -c "
from roles.models import Role
from accounts.models.account_models import CustomUser, Profile
print('Admin role exists:', Role.objects.filter(name='Admin').exists())
print('IT Admin role exists:', Role.objects.filter(name='IT Admin').exists())
print('teacher (lowercase) role exists:', Role.objects.filter(name='teacher').exists())
print('Teacher role exists:', Role.objects.filter(name='Teacher').exists())
print('Superusers:', CustomUser.objects.filter(is_superuser=True).count())
print('Admin role members:', Profile.objects.filter(role__name='Admin').count())
print('teacher (lowercase) role members:', Profile.objects.filter(role__name='teacher').count())
"
```

Expected output (should match before any changes):

```
Admin role exists: True
IT Admin role exists: False
teacher (lowercase) role exists: True
Teacher role exists: True
Superusers: 1
Admin role members: 1
teacher (lowercase) role members: 1
```

If reality differs, stop and ask the user — the migration assumptions in subsequent tasks depend on this baseline.

- [ ] **Step 3: Confirm migration heads**

Run:

```bash
cd ~/classedge && ls accounts/migrations/ roles/migrations/
```

Expected: `accounts/migrations/` ends at `0007_delete_badge.py`; `roles/migrations/` ends at `0001_initial.py`. New migrations in this plan use the next number in each app.

---

## Task 2: Rename Admin role → IT Admin (data migration)

**Files:**
- Create: `roles/migrations/0002_rename_admin_to_it_admin.py`
- Create: `roles/tests/__init__.py` (empty file, if missing)
- Create: `roles/tests/test_role_data_state.py`

- [ ] **Step 1: Write the failing test**

Create `roles/tests/__init__.py` if it doesn't exist (`touch roles/tests/__init__.py`).

Create `roles/tests/test_role_data_state.py`:

```python
"""[Classedge LMS] Asserts post-migration role table state for the IT Admin foundation."""
from django.test import TestCase

from roles.models import Role


class RoleDataStateTests(TestCase):
    def test_admin_role_renamed_to_it_admin(self):
        """[Classedge LMS] After data migration, only IT Admin should exist (no Admin)."""
        self.assertFalse(
            Role.objects.filter(name="Admin").exists(),
            "Legacy 'Admin' role should be renamed to 'IT Admin'.",
        )
        self.assertTrue(
            Role.objects.filter(name="IT Admin").exists(),
            "'IT Admin' role should exist after migration.",
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py test roles.tests.test_role_data_state.RoleDataStateTests.test_admin_role_renamed_to_it_admin --keepdb -v 2 2>&1 | tail -15
```

Expected: FAIL — "Legacy 'Admin' role should be renamed to 'IT Admin'." (because the migration hasn't run yet, the test DB still has the legacy Admin row from the keepdb baseline.)

> **Note:** Django uses a separate `test_neondb` test database; the legacy `Admin` row exists there because tests are using `--keepdb` and the production schema was once cloned in. Verify this assumption holds: if the keepdb DB doesn't currently have an `Admin` row, the test fails for a different reason (no Admin to begin with), in which case skip ahead — the rename is still safe.

- [ ] **Step 3: Create the data migration**

Create `roles/migrations/0002_rename_admin_to_it_admin.py`:

```python
"""[Classedge LMS] Rename the singleton 'Admin' role to 'IT Admin'."""
from django.db import migrations


def rename_admin_to_it_admin(apps, schema_editor):
    Role = apps.get_model("roles", "Role")
    Role.objects.filter(name="Admin").update(name="IT Admin")


def rename_it_admin_back_to_admin(apps, schema_editor):
    Role = apps.get_model("roles", "Role")
    Role.objects.filter(name="IT Admin").update(name="Admin")


class Migration(migrations.Migration):
    dependencies = [
        ("roles", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(rename_admin_to_it_admin, rename_it_admin_back_to_admin),
    ]
```

- [ ] **Step 4: Apply the migration to the test DB**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py migrate roles --keepdb 2>&1 | tail -5
```

Expected: `Applying roles.0002_rename_admin_to_it_admin... OK`.

- [ ] **Step 5: Re-run the test, verify it passes**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py test roles.tests.test_role_data_state.RoleDataStateTests.test_admin_role_renamed_to_it_admin --keepdb -v 2 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add roles/migrations/0002_rename_admin_to_it_admin.py roles/tests/__init__.py roles/tests/test_role_data_state.py
git commit -m "feat(roles): rename Admin role to IT Admin via data migration"
```

---

## Task 3: Merge orphan `teacher` role (data migration)

**Files:**
- Create: `roles/migrations/0003_merge_orphan_teacher_role.py`
- Modify: `roles/tests/test_role_data_state.py`

- [ ] **Step 1: Add the failing assertion**

Append to `roles/tests/test_role_data_state.py`:

```python

    def test_orphan_teacher_role_merged_into_teacher(self):
        """[Classedge LMS] After migration, only one 'Teacher' (capital T) role; 'teacher' is gone."""
        self.assertFalse(
            Role.objects.filter(name="teacher").exists(),
            "Orphan lowercase 'teacher' role should be deleted.",
        )
        self.assertTrue(
            Role.objects.filter(name="Teacher").exists(),
            "Canonical 'Teacher' role should still exist.",
        )

    def test_no_orphan_teacher_profiles(self):
        """[Classedge LMS] No Profile should still reference the deleted orphan role."""
        from accounts.models.account_models import Profile
        self.assertEqual(
            Profile.objects.filter(role__name="teacher").count(),
            0,
            "All 'teacher' role members must be reassigned to 'Teacher'.",
        )
```

- [ ] **Step 2: Run tests, verify the new ones fail**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py test roles.tests.test_role_data_state --keepdb -v 2 2>&1 | tail -15
```

Expected: 1 PASS (rename test from Task 2), 2 FAIL — orphan still exists.

- [ ] **Step 3: Create the merge migration**

Create `roles/migrations/0003_merge_orphan_teacher_role.py`:

```python
"""[Classedge LMS] Merge orphan lowercase 'teacher' role into canonical 'Teacher'."""
from django.db import migrations


def merge_orphan_teacher(apps, schema_editor):
    Role = apps.get_model("roles", "Role")
    Profile = apps.get_model("accounts", "Profile")

    canonical = Role.objects.filter(name="Teacher").first()
    orphan = Role.objects.filter(name="teacher").first()
    if not canonical or not orphan:
        return  # Either side missing — nothing to merge.

    Profile.objects.filter(role=orphan).update(role=canonical)
    orphan.delete()


def restore_orphan_teacher(apps, schema_editor):
    """[Classedge LMS] Reverse: recreate the empty orphan role.

    Profile reassignments are NOT restored — they're permanently moved to 'Teacher'.
    Acceptable: only 1 user was affected; pg_dump backup covers worst case.
    """
    Role = apps.get_model("roles", "Role")
    Role.objects.get_or_create(name="teacher")


class Migration(migrations.Migration):
    dependencies = [
        ("roles", "0002_rename_admin_to_it_admin"),
        ("accounts", "0007_delete_badge"),
    ]

    operations = [
        migrations.RunPython(merge_orphan_teacher, restore_orphan_teacher),
    ]
```

- [ ] **Step 4: Apply the migration**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py migrate roles --keepdb 2>&1 | tail -5
```

Expected: `Applying roles.0003_merge_orphan_teacher_role... OK`.

- [ ] **Step 5: Re-run all role-data tests**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py test roles.tests.test_role_data_state --keepdb -v 2 2>&1 | tail -10
```

Expected: all 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add roles/migrations/0003_merge_orphan_teacher_role.py roles/tests/test_role_data_state.py
git commit -m "feat(roles): merge orphan 'teacher' role into canonical 'Teacher'"
```

---

## Task 4: post_save signal — IT Admin ⇔ is_superuser invariant

**Files:**
- Create: `accounts/signals.py`
- Modify: `accounts/apps.py`
- Create: `accounts/tests/test_it_admin_signal.py`

- [ ] **Step 1: Write the failing tests**

Create `accounts/tests/test_it_admin_signal.py`:

```python
"""[Classedge LMS] Tests the post_save signal that syncs is_superuser with IT Admin role."""
from django.test import TestCase

from accounts.models.account_models import CustomUser, Profile
from roles.models import Role


class ItAdminSignalTests(TestCase):
    def setUp(self):
        self.it_admin_role, _ = Role.objects.get_or_create(name="IT Admin")
        self.teacher_role, _ = Role.objects.get_or_create(name="Teacher")

    def _make_user(self, suffix):
        return CustomUser.objects.create_user(
            username=f"u_{suffix}",
            email=f"u_{suffix}@x.io",
            password="x",
        )

    def test_assigning_it_admin_role_promotes_to_superuser(self):
        """[Classedge LMS] Saving a Profile with role=IT Admin must set user.is_superuser=True."""
        user = self._make_user("a")
        self.assertFalse(user.is_superuser)
        Profile.objects.create(user=user, role=self.it_admin_role)
        user.refresh_from_db()
        self.assertTrue(user.is_superuser)

    def test_changing_role_away_from_it_admin_demotes_superuser(self):
        """[Classedge LMS] Switching role from IT Admin to Teacher must clear is_superuser."""
        user = self._make_user("b")
        profile = Profile.objects.create(user=user, role=self.it_admin_role)
        user.refresh_from_db()
        self.assertTrue(user.is_superuser)
        profile.role = self.teacher_role
        profile.save()
        user.refresh_from_db()
        self.assertFalse(user.is_superuser)

    def test_no_role_clears_superuser(self):
        """[Classedge LMS] A profile with no role must not be a superuser."""
        user = self._make_user("c")
        profile = Profile.objects.create(user=user, role=self.it_admin_role)
        user.refresh_from_db()
        self.assertTrue(user.is_superuser)
        profile.role = None
        profile.save()
        user.refresh_from_db()
        self.assertFalse(user.is_superuser)

    def test_signal_is_idempotent(self):
        """[Classedge LMS] Saving the profile twice with same role must not toggle is_superuser."""
        user = self._make_user("d")
        Profile.objects.create(user=user, role=self.it_admin_role)
        user.refresh_from_db()
        first_state = user.is_superuser
        # Save again.
        profile = Profile.objects.get(user=user)
        profile.save()
        user.refresh_from_db()
        self.assertEqual(user.is_superuser, first_state)
        self.assertTrue(user.is_superuser)
```

- [ ] **Step 2: Run tests, verify they fail**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py test accounts.tests.test_it_admin_signal --keepdb -v 2 2>&1 | tail -15
```

Expected: FAIL — `is_superuser` stays False after assigning IT Admin role (signal doesn't exist yet).

- [ ] **Step 3: Implement the signal**

Create `accounts/signals.py`:

```python
"""[Classedge LMS] Signals enforcing the IT Admin role <-> is_superuser invariant."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models.account_models import Profile

IT_ADMIN_ROLE_NAME = "IT Admin"


@receiver(post_save, sender=Profile)
def sync_it_admin_superuser(sender, instance, **kwargs):
    """[Classedge LMS] Keep is_superuser aligned with IT Admin role assignment."""
    user = instance.user
    should_be_superuser = bool(instance.role and instance.role.name == IT_ADMIN_ROLE_NAME)
    if user.is_superuser != should_be_superuser:
        user.is_superuser = should_be_superuser
        user.save(update_fields=["is_superuser"])
```

- [ ] **Step 4: Wire signal into AppConfig.ready()**

Modify `accounts/apps.py`:

```python
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        import accounts.utils.signal_utils
        from accounts import signals  # noqa: F401
```

- [ ] **Step 5: Re-run tests, verify they pass**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py test accounts.tests.test_it_admin_signal --keepdb -v 2 2>&1 | tail -15
```

Expected: 4 PASS.

- [ ] **Step 6: Commit**

```bash
git add accounts/signals.py accounts/apps.py accounts/tests/test_it_admin_signal.py
git commit -m "feat(accounts): post_save signal syncs is_superuser with IT Admin role"
```

---

## Task 5: Backfill is_superuser for existing IT Admin profiles

**Files:**
- Create: `accounts/migrations/0008_backfill_it_admin_superuser.py`
- Modify: `accounts/tests/test_it_admin_signal.py` (one extra assertion)

- [ ] **Step 1: Write the failing test**

Append to `accounts/tests/test_it_admin_signal.py`:

```python


class ItAdminBackfillTests(TestCase):
    def test_existing_it_admin_profiles_have_superuser_flag(self):
        """[Classedge LMS] Every Profile with role 'IT Admin' must have is_superuser=True."""
        from accounts.models.account_models import Profile
        for profile in Profile.objects.filter(role__name="IT Admin").select_related("user"):
            self.assertTrue(
                profile.user.is_superuser,
                f"Profile {profile.user.username} has IT Admin role but is_superuser=False.",
            )
```

- [ ] **Step 2: Run test, verify it passes already**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py test accounts.tests.test_it_admin_signal.ItAdminBackfillTests --keepdb -v 2 2>&1 | tail -10
```

Expected: PASS — the existing `admin@gmail.com` already has `is_superuser=True` in the keepdb baseline. This test guards against regression; the migration is a safety net for any future deploy where the baseline differs.

> **If the test fails:** the migration in step 3 is necessary right now. Either way, build the migration; it's a no-op when not needed.

- [ ] **Step 3: Create the backfill migration**

Create `accounts/migrations/0008_backfill_it_admin_superuser.py`:

```python
"""[Classedge LMS] Safety-net backfill: ensure all IT Admin profiles have is_superuser=True."""
from django.db import migrations


def backfill_it_admin_superuser(apps, schema_editor):
    Profile = apps.get_model("accounts", "Profile")
    Role = apps.get_model("roles", "Role")
    it_admin = Role.objects.filter(name="IT Admin").first()
    if not it_admin:
        return
    for profile in Profile.objects.filter(role=it_admin).select_related("user"):
        if not profile.user.is_superuser:
            profile.user.is_superuser = True
            profile.user.save(update_fields=["is_superuser"])


def noop_reverse(apps, schema_editor):
    """[Classedge LMS] Intentionally does not yank is_superuser flags on rollback."""
    return


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_delete_badge"),
        ("roles", "0003_merge_orphan_teacher_role"),
    ]

    operations = [
        migrations.RunPython(backfill_it_admin_superuser, noop_reverse),
    ]
```

- [ ] **Step 4: Apply the migration**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py migrate --keepdb 2>&1 | tail -5
```

Expected: `Applying accounts.0008_backfill_it_admin_superuser... OK`.

- [ ] **Step 5: Re-run the backfill test**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py test accounts.tests.test_it_admin_signal.ItAdminBackfillTests --keepdb -v 2 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add accounts/migrations/0008_backfill_it_admin_superuser.py accounts/tests/test_it_admin_signal.py
git commit -m "feat(accounts): backfill is_superuser for existing IT Admin profiles"
```

---

## Task 6: Simplify `@admin_required` decorator

**Files:**
- Modify: `roles/decorators.py:5-17`
- Create: `roles/tests/test_admin_required_decorator.py`

- [ ] **Step 1: Write the failing tests**

Create `roles/tests/test_admin_required_decorator.py`:

```python
"""[Classedge LMS] Verify @admin_required gates strictly on is_superuser (post-Phase-1 simplification)."""
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from accounts.models.account_models import CustomUser, Profile
from roles.decorators import admin_required
from roles.models import Role


@admin_required
def _dummy_view(request):
    return HttpResponse("ok")


class AdminRequiredDecoratorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.it_admin_role, _ = Role.objects.get_or_create(name="IT Admin")
        self.teacher_role, _ = Role.objects.get_or_create(name="Teacher")

    def _request_as(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_superuser_passes(self):
        user = CustomUser.objects.create_superuser(
            username="su", email="su@x.io", password="x",
        )
        Profile.objects.create(user=user, role=self.it_admin_role)
        resp = _dummy_view(self._request_as(user))
        self.assertEqual(resp.status_code, 200)

    def test_teacher_denied(self):
        user = CustomUser.objects.create_user(
            username="t", email="t@x.io", password="x",
        )
        Profile.objects.create(user=user, role=self.teacher_role)
        with self.assertRaises(PermissionDenied):
            _dummy_view(self._request_as(user))

    def test_anonymous_denied(self):
        from django.contrib.auth.models import AnonymousUser
        request = self.factory.get("/")
        request.user = AnonymousUser()
        with self.assertRaises(PermissionDenied):
            _dummy_view(request)
```

- [ ] **Step 2: Run tests, verify the teacher-denied case currently passes incorrectly**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py test roles.tests.test_admin_required_decorator --keepdb -v 2 2>&1 | tail -15
```

Expected: 2 PASS (superuser passes, anonymous denied) and 1 FAIL — `test_teacher_denied`. Wait — actually the legacy decorator denies teachers too because it requires `is_superuser` OR role.name == 'admin', and teacher matches neither. So all 3 tests likely pass with the legacy code. That's fine — the tests are specs that the new behavior must continue to honor. Move on.

- [ ] **Step 3: Simplify the decorator**

Modify `roles/decorators.py` — replace the `admin_required` function (keep the others untouched):

```python
def admin_required(view_func):
    """[Classedge LMS] Phase 1: gate strictly on is_superuser. Role-name match removed; IT Admin role implies is_superuser via signal."""
    def _wrapped_view_func(request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied
        if not request.user.is_superuser:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view_func
```

- [ ] **Step 4: Re-run decorator tests**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py test roles.tests.test_admin_required_decorator --keepdb -v 2 2>&1 | tail -10
```

Expected: 3 PASS.

- [ ] **Step 5: Smoke-test other gated decorators (regression check)**

Run the broader role test set to verify nothing else broke:

```bash
cd ~/classedge && source env/bin/activate && python manage.py test roles --keepdb -v 1 2>&1 | tail -10
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add roles/decorators.py roles/tests/test_admin_required_decorator.py
git commit -m "feat(roles): simplify @admin_required to is_superuser check (Phase 1)"
```

---

## Task 7: IT Admin dashboard view + URL

**Files:**
- Create: `accounts/views/it_admin.py`
- Modify: `accounts/views/__init__.py`
- Modify: `accounts/urls.py`
- Create: `accounts/tests/test_it_admin_dashboard.py`

- [ ] **Step 1: Write the failing tests**

Create `accounts/tests/test_it_admin_dashboard.py`:

```python
"""[Classedge LMS] Dashboard access + routing tests for IT Admin."""
from django.test import TestCase
from django.urls import reverse

from accounts.models.account_models import CustomUser, Profile
from roles.models import Role


class ItAdminDashboardAccessTests(TestCase):
    def setUp(self):
        self.it_admin_role, _ = Role.objects.get_or_create(name="IT Admin")
        self.teacher_role, _ = Role.objects.get_or_create(name="Teacher")

    def test_it_admin_can_view_dashboard(self):
        """[Classedge LMS] IT Admin user gets the dashboard with counts."""
        user = CustomUser.objects.create_user(
            username="it1", email="it1@x.io", password="x",
        )
        Profile.objects.create(user=user, role=self.it_admin_role)
        self.client.force_login(user)
        resp = self.client.get(reverse("it_admin_dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("user_count", resp.context)
        self.assertIn("role_count", resp.context)
        self.assertIn("department_count", resp.context)
        self.assertIn("superuser_count", resp.context)

    def test_teacher_denied(self):
        """[Classedge LMS] Non-superusers must not see the IT Admin dashboard."""
        user = CustomUser.objects.create_user(
            username="t1", email="t1@x.io", password="x",
        )
        Profile.objects.create(user=user, role=self.teacher_role)
        self.client.force_login(user)
        resp = self.client.get(reverse("it_admin_dashboard"))
        self.assertIn(resp.status_code, (302, 403))

    def test_anonymous_redirected_to_login(self):
        """[Classedge LMS] Anonymous users hit the login redirect (302)."""
        resp = self.client.get(reverse("it_admin_dashboard"))
        self.assertEqual(resp.status_code, 302)
```

- [ ] **Step 2: Run tests, verify they fail**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py test accounts.tests.test_it_admin_dashboard --keepdb -v 2 2>&1 | tail -10
```

Expected: FAIL — `Reverse for 'it_admin_dashboard' not found.`

- [ ] **Step 3: Create the view module**

Create `accounts/views/it_admin.py`:

```python
"""[Classedge LMS] IT Admin dashboard — landing page with counts; gated on is_superuser."""
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

from accounts.models.account_models import CustomUser
from accounts.models.department_models import Department
from roles.models import Role


def _is_it_admin(user):
    """[Classedge LMS] Phase-1 check: is_superuser is the source of truth (signal keeps it in sync with role)."""
    return user.is_authenticated and user.is_superuser


@login_required
@user_passes_test(_is_it_admin)
def it_admin_dashboard(request):
    """[Classedge LMS] IT Admin landing page — counters + links to existing CRUD screens."""
    context = {
        "user_count": CustomUser.objects.filter(is_active=True).count(),
        "role_count": Role.objects.count(),
        "department_count": Department.objects.count(),
        "superuser_count": CustomUser.objects.filter(is_superuser=True).count(),
    }
    return render(request, "it_admin/dashboard.html", context)
```

- [ ] **Step 4: Export from `accounts/views/__init__.py`**

The file uses the `from .<module> import *` pattern + a single `__all__` list. Make two edits:

(a) Add the import line alongside the other `from .<module> import *` lines (e.g., near `from .dashboard import *`):

```python
from .it_admin import *
```

(b) Append `"it_admin_dashboard"` to the `__all__` list (placement: at the end of the list, before the closing bracket).

- [ ] **Step 5: Wire URL**

`accounts/urls.py` does `from accounts.views import *` near the top, so once Step 4 adds `it_admin_dashboard` to `__all__`, no additional import is needed. Just add the route to `urlpatterns` (immediately after the `path('', admin_login_view, name='admin_login_view')` entry):

```python
    path("it-admin/", it_admin_dashboard, name="it_admin_dashboard"),
```

- [ ] **Step 6: Add the placeholder template**

Create `templates/it_admin/dashboard.html` (minimal — full styling comes in Task 8):

```django
{% extends "it_admin_base.html" %}
{% block title %}IT Admin · ClassEdge{% endblock %}
{% block content %}
<div class="ita">
  <h1>IT Admin</h1>
  <section class="ita-cards">
    <div class="ita-card"><strong>{{ user_count }}</strong><span>Active users</span><a href="/accounts/">Manage</a></div>
    <div class="ita-card"><strong>{{ role_count }}</strong><span>Roles</span><a href="/roles/roleList/">Manage</a></div>
    <div class="ita-card"><strong>{{ department_count }}</strong><span>Departments</span><a href="/departments/">Manage</a></div>
    <div class="ita-card"><strong>{{ superuser_count }}</strong><span>Superusers</span></div>
  </section>
</div>
{% endblock %}
```

> **Note:** The base template `it_admin_base.html` is built in Task 8. For now this template will render under the assumption that base will exist. If you run the test before Task 8, it will fail with a TemplateDoesNotExist for `it_admin_base.html`. **Do Task 8 next**, then re-run.

- [ ] **Step 7: Build minimal `it_admin_base.html`** (placeholder so Task 7 tests can pass; Task 8 polishes)

Create `templates/it_admin_base.html`:

```django
<!doctype html>
<html><head><meta charset="utf-8"><title>{% block title %}IT Admin{% endblock %}</title></head>
<body>{% block content %}{% endblock %}</body></html>
```

(Task 8 will replace this with the full sidebar layout.)

- [ ] **Step 8: Re-run tests, verify they pass**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py test accounts.tests.test_it_admin_dashboard --keepdb -v 2 2>&1 | tail -10
```

Expected: 3 PASS.

- [ ] **Step 9: Commit**

```bash
git add accounts/views/it_admin.py accounts/views/__init__.py accounts/urls.py \
        templates/it_admin/dashboard.html templates/it_admin_base.html \
        accounts/tests/test_it_admin_dashboard.py
git commit -m "feat(accounts): IT Admin dashboard view + minimal templates"
```

---

## Task 8: Polish IT Admin base layout + dashboard styling

**Files:**
- Modify: `templates/it_admin_base.html`
- Modify: `templates/it_admin/dashboard.html`

- [ ] **Step 1: Replace `it_admin_base.html` with the styled layout**

Replace the entire contents of `templates/it_admin_base.html`:

```django
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{% block title %}IT Admin · ClassEdge{% endblock %}</title>
  <link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@500;700&family=Inter+Tight:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    body { margin: 0; font-family: "Inter Tight", sans-serif; background: #faf7f2; color: #2d3142; }
    .ita-shell { display: grid; grid-template-columns: 240px 1fr; min-height: 100vh; }
    .ita-side { background: #1b4332; color: #faf7f2; padding: 24px 16px; }
    .ita-side .brand { font-family: "Bricolage Grotesque", sans-serif; font-size: 22px; margin-bottom: 24px; display: flex; align-items: center; gap: 8px; }
    .ita-side .brand .mark { width: 28px; height: 28px; border-radius: 6px; background: #b7925a; display: inline-flex; align-items: center; justify-content: center; color: #1b4332; font-weight: 700; }
    .ita-side nav a { display: block; padding: 8px 12px; color: #faf7f2; text-decoration: none; border-radius: 6px; margin-bottom: 4px; opacity: 0.85; }
    .ita-side nav a:hover, .ita-side nav a.active { background: #2d5945; opacity: 1; }
    .ita-main { padding: 32px 40px; }
  </style>
</head>
<body>
  <div class="ita-shell">
    <aside class="ita-side">
      <div class="brand"><span class="mark">C</span> IT Admin</div>
      <nav>
        <a href="{% url 'it_admin_dashboard' %}"{% if request.resolver_match.url_name == 'it_admin_dashboard' %} class="active"{% endif %}>Dashboard</a>
        <a href="/accounts/">Users</a>
        <a href="/roles/roleList/">Roles</a>
        <a href="/departments/">Departments</a>
        <a href="/sign_out/">Sign out</a>
      </nav>
    </aside>
    <main class="ita-main">
      {% block content %}{% endblock %}
    </main>
  </div>
</body>
</html>
```

- [ ] **Step 2: Replace `it_admin/dashboard.html` with the polished cards**

Replace the entire contents of `templates/it_admin/dashboard.html`:

```django
{% extends "it_admin_base.html" %}
{% block title %}IT Admin · ClassEdge{% endblock %}
{% block content %}
<style>
  .ita h1 { font-family: "Bricolage Grotesque", sans-serif; color: #1b4332; margin-top: 0; }
  .ita-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin-top: 24px; }
  .ita-card { background: #fff; border-radius: 12px; padding: 24px; border: 1px solid #eee6d6; display: flex; flex-direction: column; gap: 8px; }
  .ita-card strong { font-family: "Bricolage Grotesque", sans-serif; font-size: 32px; color: #1b4332; }
  .ita-card span { color: #6b6f78; }
  .ita-card a { margin-top: 12px; align-self: flex-start; padding: 6px 14px; border-radius: 6px; background: #1b4332; color: #faf7f2; text-decoration: none; font-weight: 600; font-size: 14px; }
</style>
<div class="ita">
  <h1>IT Admin</h1>
  <p>Manage users, roles, and departments for this Classedge deployment.</p>
  <section class="ita-cards">
    <div class="ita-card"><strong>{{ user_count }}</strong><span>Active users</span><a href="/accounts/">Manage</a></div>
    <div class="ita-card"><strong>{{ role_count }}</strong><span>Roles</span><a href="/roles/roleList/">Manage</a></div>
    <div class="ita-card"><strong>{{ department_count }}</strong><span>Departments</span><a href="/departments/">Manage</a></div>
    <div class="ita-card"><strong>{{ superuser_count }}</strong><span>Superusers</span></div>
  </section>
</div>
{% endblock %}
```

- [ ] **Step 3: Re-run dashboard tests (no logic change, should still pass)**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py test accounts.tests.test_it_admin_dashboard --keepdb -v 2 2>&1 | tail -10
```

Expected: 3 PASS.

- [ ] **Step 4: Commit**

```bash
git add templates/it_admin_base.html templates/it_admin/dashboard.html
git commit -m "feat(accounts): polish IT Admin base layout and dashboard cards"
```

---

## Task 9: Dashboard routing — superusers redirect to /it-admin/

**Files:**
- Modify: `accounts/views/dashboard.py:48-57`
- Modify: `accounts/tests/test_it_admin_dashboard.py`

- [ ] **Step 1: Append the failing routing tests**

Append to `accounts/tests/test_it_admin_dashboard.py`:

```python


class DashboardRoutingTests(TestCase):
    def setUp(self):
        self.it_admin_role, _ = Role.objects.get_or_create(name="IT Admin")
        self.teacher_role, _ = Role.objects.get_or_create(name="Teacher")

    def test_superuser_redirects_to_it_admin(self):
        """[Classedge LMS] Superusers hitting /dashboard/ get bounced to /it-admin/."""
        user = CustomUser.objects.create_user(
            username="su2", email="su2@x.io", password="x",
        )
        Profile.objects.create(user=user, role=self.it_admin_role)  # Signal sets is_superuser=True
        self.client.force_login(user)
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("it_admin_dashboard"))

    def test_teacher_dashboard_unchanged(self):
        """[Classedge LMS] Teachers don't get bounced to /it-admin/; existing flow preserved."""
        user = CustomUser.objects.create_user(
            username="t2", email="t2@x.io", password="x",
        )
        Profile.objects.create(user=user, role=self.teacher_role)
        self.client.force_login(user)
        resp = self.client.get(reverse("dashboard"))
        # Teacher path may render directly (200) or redirect to a teacher-specific URL.
        # Either way, it must NOT be the it_admin_dashboard URL.
        if resp.status_code == 302:
            self.assertNotEqual(resp.url, reverse("it_admin_dashboard"))
        else:
            self.assertEqual(resp.status_code, 200)
```

- [ ] **Step 2: Run tests, verify the superuser case fails**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py test accounts.tests.test_it_admin_dashboard.DashboardRoutingTests --keepdb -v 2 2>&1 | tail -10
```

Expected: 1 FAIL — superuser doesn't redirect (the routing branch isn't there yet).

- [ ] **Step 3: Add the superuser branch in `dashboard()`**

Modify `accounts/views/dashboard.py` — locate the `dashboard` function (starts at line 26) and find the role-name resolution block (around lines 48-57). Add the superuser short-circuit BEFORE the role-name resolution:

```python
    if user.is_superuser:
        return redirect("it_admin_dashboard")

    role_name = user.profile.role.name.lower() if hasattr(user, 'profile') and user.profile.role else ''
```

The first line of the new branch must come immediately after the `cache.set(cache_key_semester, ...)` block (line 45) and before the existing `role_name = ...` assignment.

- [ ] **Step 4: Re-run routing tests**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py test accounts.tests.test_it_admin_dashboard.DashboardRoutingTests --keepdb -v 2 2>&1 | tail -10
```

Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add accounts/views/dashboard.py accounts/tests/test_it_admin_dashboard.py
git commit -m "feat(accounts): redirect superusers from /dashboard/ to /it-admin/"
```

---

## Task 10: `seed_it_admin` management command

**Files:**
- Create: `accounts/management/__init__.py` (if missing)
- Create: `accounts/management/commands/__init__.py` (if missing)
- Create: `accounts/management/commands/seed_it_admin.py`
- Create: `accounts/tests/test_seed_it_admin.py`

- [ ] **Step 1: Write the failing tests**

Ensure both `accounts/management/__init__.py` and `accounts/management/commands/__init__.py` exist (`touch` them if not).

Create `accounts/tests/test_seed_it_admin.py`:

```python
"""[Classedge LMS] Tests the seed_it_admin management command."""
from io import StringIO
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from accounts.models.account_models import CustomUser, Profile
from roles.models import Role


class SeedItAdminTests(TestCase):
    def _run(self, **kwargs):
        out = StringIO()
        call_command("seed_it_admin", stdout=out, **kwargs)
        return out.getvalue()

    def test_creates_role_and_user_on_fresh_db(self):
        """[Classedge LMS] First run creates IT Admin role + user, signal flips superuser flag."""
        Role.objects.filter(name="IT Admin").delete()
        CustomUser.objects.filter(email="it@example.com").delete()
        self._run(email="it@example.com", password="seedpw1234")
        self.assertTrue(Role.objects.filter(name="IT Admin").exists())
        user = CustomUser.objects.get(email="it@example.com")
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.profile.role.name, "IT Admin")

    def test_idempotent_on_second_run(self):
        """[Classedge LMS] Second run with same args: no extra users/roles."""
        Role.objects.filter(name="IT Admin").delete()
        CustomUser.objects.filter(email="it2@example.com").delete()
        self._run(email="it2@example.com", password="seedpw1234")
        self._run(email="it2@example.com", password="seedpw1234")
        self.assertEqual(CustomUser.objects.filter(email="it2@example.com").count(), 1)
        self.assertEqual(Role.objects.filter(name="IT Admin").count(), 1)

    def test_grants_role_to_existing_user(self):
        """[Classedge LMS] If a user with that email exists, grant them IT Admin (don't create duplicate)."""
        Role.objects.filter(name="IT Admin").delete()
        existing = CustomUser.objects.create_user(
            username="existing", email="exist@example.com", password="orig",
        )
        teacher_role, _ = Role.objects.get_or_create(name="Teacher")
        Profile.objects.create(user=existing, role=teacher_role)
        self._run(email="exist@example.com", password="seedpw1234")
        existing.refresh_from_db()
        self.assertTrue(existing.is_superuser)
        self.assertEqual(existing.profile.role.name, "IT Admin")
        # Password not reset (no --force-reset-password passed):
        self.assertTrue(existing.check_password("orig"))

    def test_force_reset_password_resets(self):
        """[Classedge LMS] --force-reset-password resets the existing user's password."""
        Role.objects.filter(name="IT Admin").delete()
        existing = CustomUser.objects.create_user(
            username="exist2", email="exist2@example.com", password="origpw",
        )
        teacher_role, _ = Role.objects.get_or_create(name="Teacher")
        Profile.objects.create(user=existing, role=teacher_role)
        self._run(email="exist2@example.com", password="newpw5678", force_reset_password=True)
        existing.refresh_from_db()
        self.assertTrue(existing.check_password("newpw5678"))

    @override_settings(DEBUG=False)
    def test_missing_email_in_production_errors(self):
        """[Classedge LMS] DEBUG=False + no email arg + no env: hard error, no prompt."""
        Role.objects.filter(name="IT Admin").delete()
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("IT_ADMIN_EMAIL", None)
            os.environ.pop("IT_ADMIN_PASSWORD", None)
            with self.assertRaises(CommandError):
                self._run()

    def test_dry_run_changes_nothing(self):
        """[Classedge LMS] --dry-run prints intent without touching the DB."""
        Role.objects.filter(name="IT Admin").delete()
        CustomUser.objects.filter(email="dry@example.com").delete()
        self._run(email="dry@example.com", password="seedpw1234", dry_run=True)
        self.assertFalse(Role.objects.filter(name="IT Admin").exists())
        self.assertFalse(CustomUser.objects.filter(email="dry@example.com").exists())
```

- [ ] **Step 2: Run tests, verify they fail**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py test accounts.tests.test_seed_it_admin --keepdb -v 2 2>&1 | tail -15
```

Expected: 6 errors, all `CommandError: Unknown command: 'seed_it_admin'`.

- [ ] **Step 3: Implement the management command**

Create `accounts/management/commands/seed_it_admin.py`:

```python
"""[Classedge LMS] Bootstrap an IT Admin role + user on a fresh Classedge deployment."""
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts.models.account_models import CustomUser, Profile
from roles.models import Role


IT_ADMIN_ROLE_NAME = "IT Admin"


class Command(BaseCommand):
    help = "[Classedge LMS] Ensure the IT Admin role exists and at least one user has it."

    def add_arguments(self, parser):
        parser.add_argument("--email", type=str, default=None, help="IT Admin email; falls back to IT_ADMIN_EMAIL env var.")
        parser.add_argument("--password", type=str, default=None, help="IT Admin password; falls back to IT_ADMIN_PASSWORD env var.")
        parser.add_argument("--username", type=str, default=None, help="Username; defaults to email prefix.")
        parser.add_argument("--dry-run", action="store_true", help="Print intent without writing to the DB.")
        parser.add_argument("--force-reset-password", action="store_true", help="Reset the password even if user exists.")

    def handle(self, *args, **options):
        email = options.get("email") or os.environ.get("IT_ADMIN_EMAIL")
        password = options.get("password") or os.environ.get("IT_ADMIN_PASSWORD")
        username = options.get("username")
        dry_run = options.get("dry_run", False)
        force_reset = options.get("force_reset_password", False)

        if not email:
            if not settings.DEBUG:
                raise CommandError("IT_ADMIN_EMAIL is required (env var or --email) in non-DEBUG mode.")
            email = input("IT Admin email: ").strip()
            if not email:
                raise CommandError("Email is required.")

        if not password:
            if not settings.DEBUG:
                raise CommandError("IT_ADMIN_PASSWORD is required (env var or --password) in non-DEBUG mode.")
            import getpass
            password = getpass.getpass("IT Admin password: ")
            if not password:
                raise CommandError("Password is required.")

        if not username:
            username = email.split("@", 1)[0]

        self.stdout.write(f"Email: {email}")
        self.stdout.write(f"Username: {username}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no changes will be made."))
            return

        role, role_created = Role.objects.get_or_create(name=IT_ADMIN_ROLE_NAME)
        if role_created:
            self.stdout.write(self.style.SUCCESS(f"Created Role '{IT_ADMIN_ROLE_NAME}'"))
        else:
            self.stdout.write(f"Role '{IT_ADMIN_ROLE_NAME}' already exists")

        user = CustomUser.objects.filter(email=email).first()
        if user:
            self.stdout.write(f"User {email} exists — granting IT Admin role")
            if force_reset:
                user.set_password(password)
                user.save(update_fields=["password"])
                self.stdout.write(self.style.WARNING("Password reset (--force-reset-password)."))
        else:
            user = CustomUser.objects.create_user(
                username=username, email=email, password=password,
            )
            self.stdout.write(self.style.SUCCESS(f"Created user {email}"))

        profile, _ = Profile.objects.get_or_create(user=user)
        if profile.role != role:
            profile.role = role
            profile.save()  # Signal flips is_superuser=True
            self.stdout.write(self.style.SUCCESS("Profile.role set to IT Admin"))
        else:
            self.stdout.write("Profile.role already IT Admin")

        user.refresh_from_db()
        self.stdout.write(self.style.SUCCESS(
            f"Done. is_superuser={user.is_superuser}, role={profile.role.name}"
        ))
```

- [ ] **Step 4: Re-run tests**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py test accounts.tests.test_seed_it_admin --keepdb -v 2 2>&1 | tail -15
```

Expected: 6 PASS.

- [ ] **Step 5: Commit**

```bash
git add accounts/management/__init__.py accounts/management/commands/__init__.py \
        accounts/management/commands/seed_it_admin.py accounts/tests/test_seed_it_admin.py
git commit -m "feat(accounts): seed_it_admin management command for fresh-deploy bootstrap"
```

---

## Task 11: Full-suite smoke + manual QA + commit deliverables checklist

**Files:**
- Read-only verification + final commit

- [ ] **Step 1: Run the full Phase 1 test set**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py test \
  accounts.tests.test_it_admin_signal \
  accounts.tests.test_it_admin_dashboard \
  accounts.tests.test_seed_it_admin \
  roles.tests.test_admin_required_decorator \
  roles.tests.test_role_data_state \
  --keepdb -v 2 2>&1 | tail -30
```

Expected: ~17-19 tests, all PASS.

- [ ] **Step 2: Broader regression smoke**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py test accounts roles --keepdb -v 1 2>&1 | tail -20
```

Expected: no regressions in existing accounts/roles tests.

- [ ] **Step 3: Manual QA — existing admin login**

Start the dev server (note: pick a free port; 8000/8001/8002 may be taken by other projects):

```bash
cd ~/classedge && source env/bin/activate && python manage.py runserver 8003
```

In a browser:
1. Visit `http://localhost:8003/`
2. Log in as `admin@gmail.com` / (existing password — if unknown, reset via shell: `python manage.py shell -c "from accounts.models.account_models import CustomUser; u=CustomUser.objects.get(username='admin'); u.set_password('admin123'); u.save()"`)
3. Confirm the post-login page is the new IT Admin dashboard at `/it-admin/` (URL bar + cards visible).
4. Confirm sidebar links work: Users → `/accounts/`; Roles → `/roles/roleList/`; Departments → `/departments/`.
5. Sign out via sidebar.

- [ ] **Step 4: Manual QA — teacher unaffected**

In the same browser:
1. Log in as `516ricomaraon@gmail.com` / `test123` (or any existing teacher).
2. Confirm post-login lands on the teacher dashboard (`/gamification/dashboard/`), NOT `/it-admin/`.
3. Visit `/it-admin/` directly in the URL bar.
4. Confirm 403 Forbidden (or login redirect — both acceptable).

Stop the dev server (Ctrl+C).

- [ ] **Step 5: Verify migration plan is clean**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py migrate --plan 2>&1 | tail -15
```

Expected: no pending migrations (everything applied during prior tasks).

- [ ] **Step 6: Verify seeder works on a clean dry-run**

Run:

```bash
cd ~/classedge && source env/bin/activate && python manage.py seed_it_admin --email it@example.com --password testpw123 --dry-run
```

Expected output ends with: `Dry run — no changes will be made.` and DB unchanged (verify via `python manage.py shell -c "from accounts.models.account_models import CustomUser; print(CustomUser.objects.filter(email='it@example.com').exists())"` → False).

- [ ] **Step 7: Mark spec deliverables checklist complete**

Open `docs/superpowers/specs/2026-04-22-it-admin-role-foundation-design.md`. In Section 7 ("Deliverables checklist"), change every `- [ ]` to `- [x]` for items now done. Save.

- [ ] **Step 8: Final commit**

```bash
git add docs/superpowers/specs/2026-04-22-it-admin-role-foundation-design.md
git commit -m "docs: mark IT Admin Phase 1 deliverables as complete"
```

- [ ] **Step 9: Push branch + open PR (per existing workflow)**

```bash
cd ~/classedge && git push -u personal feat/it-admin-role-foundation
gh pr create --repo teryopitikin/Classedge-Ai --base main --head feat/it-admin-role-foundation \
  --title "IT Admin role foundation (Phase 1)" \
  --body "$(cat <<'EOF'
## Summary
- Renames the singleton 'Admin' role to 'IT Admin' (data migration).
- Merges orphan lowercase 'teacher' role into canonical 'Teacher'.
- post_save signal keeps `is_superuser` aligned with the IT Admin role.
- Backfill migration ensures existing IT Admin profiles have `is_superuser=True`.
- `@admin_required` simplified to a strict `is_superuser` check.
- New `/it-admin/` dashboard at `accounts.views.it_admin.it_admin_dashboard` with counter cards + sidebar layout (`it_admin_base.html`).
- Dashboard router (`/dashboard/`) redirects superusers to `/it-admin/`.
- `seed_it_admin` management command for fresh-deploy bootstrap (idempotent).

## Test plan
- ~17 new tests across migration state, signal invariants, decorator, dashboard access, dashboard routing, and seeder.
- Manual: existing admin lands on `/it-admin/`; teacher dashboards unchanged; non-superuser hitting `/it-admin/` denied.

## Out of scope (later phases)
- Phase 2: replace remaining role-name decorators with `@permission_required("codename")`.
- Phase 3: code-side permission categorization, hardcoded `excluded_models` cleanup, dept-head picker filtering.
EOF
)"
```

---

## Open Risks Carried Forward to Phase 2/3

| Risk | Plan |
|------|-----|
| Other Django superusers exist that aren't IT Admins | Phase 1 logs them; Phase 2 adds a management command to audit. |
| `@teacher_required` / `@student_required` / `@registrar_required` still match by string | Phase 2 replaces with permission-based decorators. |
| Hardcoded `excluded_models` + app whitelist in `roles/views.py` | Phase 3 cleanup. |
