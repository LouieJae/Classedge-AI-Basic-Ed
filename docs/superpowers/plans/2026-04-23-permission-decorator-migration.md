# Phase 2 — Permission-decorator Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `@teacher_or_admin_required` on 17 instructor-facing callsites with `@permission_required(...)` using existing Django auto-generated model perms, plus delete four legacy role-name decorators.

**Architecture:** Single PR, single deploy. Forward + reverse Django data migration grants the migrated perms to existing roles (Teacher gets the full set; Program Head/Dean/Director get gradebook+analytics+module read; Registrar gets gradebook read). Per-file TDD: write per-callsite gating tests, swap decorators, verify. Hard cutover deletes legacy decorators after all swaps land.

**Tech Stack:** Django 4.x, Python 3.12, Django's built-in `auth.Permission` model, `django.contrib.auth.decorators.permission_required`, `RunPython` data migrations, Django `TestCase` + `Client`/`RequestFactory`.

**Spec:** `docs/superpowers/specs/2026-04-23-permission-decorator-migration-design.md`

---

## ⚠️ Pre-flight gate

This plan **must not begin** until Phase 1 (PR #2, branch `feat/it-admin-role-foundation`) has merged into `main`. Phase 2 modifies the same `roles/decorators.py` Phase 1 simplified and depends on:
- Phase 1's `roles/migrations/0003_merge_orphan_teacher_role.py` (latest roles migration we depend on).
- Phase 1's `accounts/utils/signal_utils.py` transition-aware `is_superuser` signal (used by tests).
- The `seed_it_admin` management command from Phase 1 (used to create the IT Admin test user).

**Confirm before Task 1:** `git log main --oneline | grep -i "it-admin"` shows Phase 1 commits.

---

## Task 1: Create Phase 2 branch from main

**Files:**
- (no file changes — git operation only)

- [ ] **Step 1: Verify Phase 1 is in main**

```bash
cd ~/classedge
git fetch personal
git checkout main
git pull personal main
git log --oneline -10 | grep -i "it-admin\|seed_it_admin"
```
Expected: at least one commit referencing IT Admin work present in main.

- [ ] **Step 2: Verify Phase 1 migrations are present in main**

```bash
ls roles/migrations/ accounts/migrations/ | grep -E "rename_admin|merge_orphan|backfill_it_admin"
```
Expected: `0002_rename_admin_to_it_admin.py`, `0003_merge_orphan_teacher_role.py`, `0008_backfill_it_admin_superuser.py`.

- [ ] **Step 3: Cut the Phase 2 branch**

```bash
git checkout -b feat/permission-decorator-migration
git status
```
Expected: branch created, clean tree.

---

## Task 2: Data migration — `roles/0004_grant_phase2_perms.py`

**Files:**
- Create: `roles/migrations/0004_grant_phase2_perms.py`
- Test: (added in Task 3 — Task 2 ends with the migration code; the migration test is its own task to keep commits bisectable)

- [ ] **Step 1: Create the migration file with forward + reverse RunPython**

Create `roles/migrations/0004_grant_phase2_perms.py` with this exact content:

```python
"""[Classedge LMS] Phase 2 — grant the migrated permission set to existing roles.

Forward grants are idempotent (M2M add). Reverse cleanly removes the same
perms. Roles missing from the DB are skipped with an info log line; the
migration must not crash when a school hasn't created e.g. 'Program Head'.
"""
import logging

from django.db import migrations

log = logging.getLogger(__name__)


# Mapping derived from
# docs/superpowers/specs/2026-04-23-permission-decorator-migration-design.md §4.
# Each tuple is (app_label, codename); the model name is parsed as the part
# of the codename after the first underscore.
PHASE2_GRANTS = {
    "Teacher": [
        ("activity", "view_studentactivity"),
        ("activity", "change_studentactivity"),
        ("ide", "view_codingexercise"),
        ("ide", "change_codesubmission"),
        ("gamification", "add_teacherrecognition"),
        ("gamification", "view_badgedefinition"),
        ("gamification", "change_badgedefinition"),
        ("gamification", "add_studentbadge"),
        ("gamification", "view_studentgamification"),
    ],
    "Program Head": [
        ("activity", "view_studentactivity"),
        ("gamification", "view_studentgamification"),
        ("module", "view_module"),
    ],
    "Academic Dean": [
        ("activity", "view_studentactivity"),
        ("gamification", "view_studentgamification"),
        ("module", "view_module"),
    ],
    "Academic Director": [
        ("activity", "view_studentactivity"),
        ("gamification", "view_studentgamification"),
        ("module", "view_module"),
    ],
    "Registrar": [
        ("activity", "view_studentactivity"),
    ],
}


def _resolve_perms(apps, codenames):
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    resolved = []
    for app_label, codename in codenames:
        model_name = codename.split("_", 1)[1]
        ct = (
            ContentType.objects.filter(app_label=app_label, model=model_name).first()
        )
        if ct is None:
            log.warning(
                "[Phase 2] missing content_type %s.%s; skipping perm %s",
                app_label, model_name, codename,
            )
            continue
        perm = Permission.objects.filter(content_type=ct, codename=codename).first()
        if perm is None:
            log.warning(
                "[Phase 2] missing permission %s.%s; skipping",
                app_label, codename,
            )
            continue
        resolved.append(perm)
    return resolved


def grant_phase2_perms(apps, schema_editor):
    Role = apps.get_model("roles", "Role")
    for role_name, codenames in PHASE2_GRANTS.items():
        role = Role.objects.filter(name=role_name).first()
        if role is None:
            log.info("[Phase 2] skipping role '%s': not present", role_name)
            continue
        perms = _resolve_perms(apps, codenames)
        if perms:
            role.permissions.add(*perms)


def revoke_phase2_perms(apps, schema_editor):
    Role = apps.get_model("roles", "Role")
    for role_name, codenames in PHASE2_GRANTS.items():
        role = Role.objects.filter(name=role_name).first()
        if role is None:
            continue
        perms = _resolve_perms(apps, codenames)
        if perms:
            role.permissions.remove(*perms)


class Migration(migrations.Migration):
    dependencies = [
        ("roles", "0003_merge_orphan_teacher_role"),
        ("activity", "0020_scorechangelog_reason_studentactivity_feedback"),
        ("ide", "0002_seed_coding_activity_type"),
        ("gamification", "0008_teacher_gamification_models"),
        ("module", "0002_add_central_source_id"),
    ]

    operations = [
        migrations.RunPython(grant_phase2_perms, revoke_phase2_perms),
    ]
```

> **Verify dependency app/migration names against the actual repo state at execution time.** If any of `activity/0020_*`, `ide/0002_*`, `gamification/0008_*`, `module/0002_*` has been superseded by a newer migration after Phase 1 merged, update the dependency to the newer name. The migration must depend on a migration that exists in each app, otherwise Django will refuse to load.

- [ ] **Step 2: Verify the migration loads**

```bash
python3 manage.py makemigrations --dry-run --check roles
```
Expected: no output (no new migrations needed).

```bash
python3 manage.py migrate --plan | grep "0004_grant_phase2_perms"
```
Expected: line showing the new migration is queued to run.

- [ ] **Step 3: Commit (migration only, no test yet)**

```bash
git add roles/migrations/0004_grant_phase2_perms.py
git commit -m "feat(roles): phase 2 data migration — grant migrated perms to existing roles"
```

---

## Task 3: Data migration test

**Files:**
- Create: `roles/tests/test_phase2_data_migration.py`

This test must run against the actual migration, not a re-implementation. We use Django's `MigrationExecutor` to roll the DB to before-Phase-2, seed roles, run the migration forward, assert grants, run reverse, assert clean.

- [ ] **Step 1: Write the failing test**

Create `roles/tests/test_phase2_data_migration.py`:

```python
"""[Classedge LMS] Phase 2 data migration — verify role-permission grants.

We exercise the real RunPython callbacks via the migration's PHASE2_GRANTS
constant so the test cannot drift from the migration's intent.
"""
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from roles.migrations.m0004_grant_phase2_perms_helper import (  # see Step 2
    PHASE2_GRANTS,
    grant_phase2_perms,
    revoke_phase2_perms,
)
from roles.models import Role


def _resolve(app_label, codename):
    model_name = codename.split("_", 1)[1]
    ct = ContentType.objects.get(app_label=app_label, model=model_name)
    return Permission.objects.get(content_type=ct, codename=codename)


class _AppsShim:
    """Tiny wrapper so we can call grant/revoke against real models in a test."""

    def get_model(self, app_label, model_name):
        from django.apps import apps as real_apps
        return real_apps.get_model(app_label, model_name)


class Phase2DataMigrationTests(TestCase):
    """[Classedge LMS] grant_phase2_perms/revoke_phase2_perms are idempotent and behavior-preserving."""

    def setUp(self):
        # Create every role mentioned in PHASE2_GRANTS so we exercise all rows.
        for role_name in PHASE2_GRANTS.keys():
            Role.objects.get_or_create(name=role_name)

    def _expected_perm_ids(self, role_name):
        codenames = PHASE2_GRANTS[role_name]
        return {_resolve(app, code).id for app, code in codenames}

    def test_forward_grants_expected_perms_per_role(self):
        grant_phase2_perms(_AppsShim(), None)
        for role_name in PHASE2_GRANTS:
            role = Role.objects.get(name=role_name)
            actual = set(role.permissions.values_list("id", flat=True))
            expected = self._expected_perm_ids(role_name)
            self.assertTrue(
                expected.issubset(actual),
                f"Role '{role_name}' missing perms after forward migration: "
                f"{expected - actual}",
            )

    def test_forward_is_idempotent(self):
        grant_phase2_perms(_AppsShim(), None)
        before = {
            r.name: set(r.permissions.values_list("id", flat=True))
            for r in Role.objects.all()
        }
        grant_phase2_perms(_AppsShim(), None)  # second run
        after = {
            r.name: set(r.permissions.values_list("id", flat=True))
            for r in Role.objects.all()
        }
        self.assertEqual(before, after)

    def test_reverse_removes_granted_perms(self):
        grant_phase2_perms(_AppsShim(), None)
        revoke_phase2_perms(_AppsShim(), None)
        for role_name in PHASE2_GRANTS:
            role = Role.objects.get(name=role_name)
            actual = set(role.permissions.values_list("id", flat=True))
            expected = self._expected_perm_ids(role_name)
            self.assertTrue(
                expected.isdisjoint(actual),
                f"Role '{role_name}' still has Phase 2 perms after reverse: "
                f"{expected & actual}",
            )

    def test_missing_role_is_skipped_not_crashed(self):
        Role.objects.filter(name="Program Head").delete()
        # Must not raise.
        grant_phase2_perms(_AppsShim(), None)
```

- [ ] **Step 2: Expose migration callbacks for import**

The test imports from `roles.migrations.m0004_grant_phase2_perms_helper`. Django migration files starting with a digit aren't valid module names for `from ... import`, so we expose the symbols via a sibling helper module.

Create `roles/migrations/m0004_grant_phase2_perms_helper.py`:

```python
"""[Classedge LMS] Re-export Phase 2 migration callbacks for direct test import.

Migration filenames start with a digit, which Python doesn't allow as a
module name in `from ... import`. This sibling module re-exports the
callbacks and constants so tests can call them directly.
"""
from importlib import import_module

_mig = import_module("roles.migrations.0004_grant_phase2_perms")

PHASE2_GRANTS = _mig.PHASE2_GRANTS
grant_phase2_perms = _mig.grant_phase2_perms
revoke_phase2_perms = _mig.revoke_phase2_perms
```

- [ ] **Step 3: Run the test, verify it passes**

```bash
python3 manage.py test roles.tests.test_phase2_data_migration -v 2
```
Expected: 4 tests pass. (The migration ran during `setUp` of the TestCase via the standard test-DB setup, so all perms are present; the explicit grant calls in tests are additional safety.)

If a test fails citing missing permissions (`Permission.DoesNotExist` for a model like `studentactivity`), confirm the model exists (`python3 manage.py shell -c "from activity.models.student_activity_model import StudentActivity; print(StudentActivity)"`) and that no app rename has shifted the `app_label`.

- [ ] **Step 4: Commit**

```bash
git add roles/tests/test_phase2_data_migration.py roles/migrations/m0004_grant_phase2_perms_helper.py
git commit -m "test(roles): phase 2 data migration — forward/reverse/idempotency/missing-role"
```

---

## Task 4: Test helpers — `roles/tests/helpers.py`

**Files:**
- Create: `roles/tests/helpers.py`

Per-callsite gating tests (Tasks 5-10) all need: a user assigned to a named role, with a specific perm granted via the Phase 2 migration's grant logic. Centralize this here.

- [ ] **Step 1: Create the helpers module**

Create `roles/tests/helpers.py`:

```python
"""[Classedge LMS] Shared test helpers for Phase 2 permission-gating tests."""
from django.contrib.auth import get_user_model

from accounts.models.account_models import Profile
from roles.migrations.m0004_grant_phase2_perms_helper import PHASE2_GRANTS
from roles.models import Role


User = get_user_model()


def make_user_with_role(username, role_name, *, grant_phase2=True):
    """[Classedge LMS] Create a user assigned to a named role.

    The Profile is auto-created by accounts.utils.signal_utils on user
    creation (defaulted to Student). We then update the profile to the
    requested role so the Phase 1 transition-aware is_superuser signal
    fires correctly.

    If grant_phase2 is True and PHASE2_GRANTS has an entry for role_name,
    the role receives those perms (mirroring what the data migration does
    in production). Roles outside PHASE2_GRANTS get no perms and should
    be denied by the perm-gated views.
    """
    role, _ = Role.objects.get_or_create(name=role_name)
    if grant_phase2 and role_name in PHASE2_GRANTS:
        # Use the migration's own grant function so test setup cannot
        # drift from production grants.
        from roles.migrations.m0004_grant_phase2_perms_helper import (
            grant_phase2_perms,
        )

        class _Shim:
            def get_model(self, app_label, model_name):
                from django.apps import apps
                return apps.get_model(app_label, model_name)

        grant_phase2_perms(_Shim(), None)

    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.invalid",
        password="Test@1234",
    )
    profile = Profile.objects.get(user=user)
    profile.role = role
    profile.save()
    user.refresh_from_db()  # pull is_superuser changes the signal may have made
    return user


def make_it_admin(username="phase2_it_admin"):
    """[Classedge LMS] Create an IT Admin (superuser) user — bypasses all perms."""
    role, _ = Role.objects.get_or_create(name="IT Admin")
    user = User.objects.create_superuser(
        username=username,
        email=f"{username}@example.invalid",
        password="Test@1234",
    )
    profile = Profile.objects.get(user=user)
    profile.role = role
    profile.save()
    user.refresh_from_db()
    return user
```

- [ ] **Step 2: Verify helpers import cleanly**

```bash
python3 manage.py shell -c "from roles.tests.helpers import make_user_with_role, make_it_admin; print('ok')"
```
Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add roles/tests/helpers.py
git commit -m "test(roles): helpers for phase 2 permission-gating tests"
```

---

## Task 5: Swap decorators in `gradebookcomponent/views/instructor_grading.py` (6 callsites)

**Files:**
- Modify: `gradebookcomponent/views/instructor_grading.py`
- Create: `roles/tests/test_gating_gradebook.py`

- [ ] **Step 1: Write failing tests for all 6 gradebook callsites**

Create `roles/tests/test_gating_gradebook.py`:

```python
"""[Classedge LMS] Gating tests for gradebookcomponent/views/instructor_grading.py.

Each test asserts the perm-based contract (Teacher 200 / Student 403 /
IT Admin 200). Object-level authorization (authorize_subject_access) is
covered by the gradebookcomponent test suite, not here.
"""
from django.test import Client, TestCase
from django.urls import reverse

from gradebookcomponent.tests.helpers import (
    make_activity, make_subject, make_submission,
)
from roles.tests.helpers import make_it_admin, make_user_with_role


class GradebookGatingTests(TestCase):

    def setUp(self):
        self.teacher = make_user_with_role("phase2_teacher", "Teacher")
        self.student = make_user_with_role("phase2_student", "Student")
        self.it_admin = make_it_admin()
        self.subject = make_subject(self.teacher)
        self.activity = make_activity(self.subject)
        self.sa = make_submission(self.student, self.activity)
        self.client = Client()

    def _assert_gating(self, url, *, method="get", post_data=None):
        # Teacher with perm
        self.client.force_login(self.teacher)
        resp = getattr(self.client, method)(url, data=post_data or {})
        self.assertIn(resp.status_code, (200, 302),
                      f"Teacher denied {url} (got {resp.status_code})")
        # Student without perm
        self.client.force_login(self.student)
        resp = getattr(self.client, method)(url, data=post_data or {})
        self.assertEqual(resp.status_code, 403,
                         f"Student not denied at {url}")
        # IT Admin (superuser bypass)
        self.client.force_login(self.it_admin)
        resp = getattr(self.client, method)(url, data=post_data or {})
        self.assertIn(resp.status_code, (200, 302),
                      f"IT Admin denied {url} (got {resp.status_code})")

    def test_gradebook_home(self):
        self._assert_gating(reverse("gradebook_home"))

    def test_subject_gradebook(self):
        self._assert_gating(reverse("subject_gradebook", args=[self.subject.id]))

    def test_subject_gradebook_csv(self):
        self._assert_gating(reverse("subject_gradebook_csv", args=[self.subject.id]))

    def test_grading_queue(self):
        self._assert_gating(reverse("gradebook_queue"))

    def test_grade_submission(self):
        self._assert_gating(reverse("gradebook_grade", args=[self.sa.id]))

    def test_override_score(self):
        self._assert_gating(
            reverse("gradebook_override", args=[self.sa.id]),
            method="post",
            post_data={"reason": "test", "new_score": "5"},
        )
```

> **Verify URL names** (`gradebook_home`, `subject_gradebook`, `subject_gradebook_csv`, `gradebook_queue`, `gradebook_grade`, `gradebook_override`) against `gradebookcomponent/urls.py`. Adjust to actual names if any differ.

- [ ] **Step 2: Run tests — expect Student-denied assertions to fail**

```bash
python3 manage.py test roles.tests.test_gating_gradebook -v 2
```
Expected: tests fail with the Student receiving non-403 status, because today's `@teacher_or_admin_required` doesn't deny based on perm — it denies based on role-name. (The Student role name will fail the role check too, so this *might* pass coincidentally; if all 6 pass already, that's still useful — they will continue to pass after the swap, proving no regression.)

- [ ] **Step 3: Swap the 6 decorators in `gradebookcomponent/views/instructor_grading.py`**

In `gradebookcomponent/views/instructor_grading.py`:

a. Update imports — replace `from roles.decorators import teacher_or_admin_required` with `from django.contrib.auth.decorators import permission_required`.

b. Replace each `@teacher_or_admin_required` line as follows:

| Line | Current | Replace with |
|---|---|---|
| 55 | `@teacher_or_admin_required` | `@permission_required('activity.view_studentactivity', raise_exception=True)` |
| 78 | `@teacher_or_admin_required` | `@permission_required('activity.view_studentactivity', raise_exception=True)` |
| 136 | `@teacher_or_admin_required` | `@permission_required('activity.view_studentactivity', raise_exception=True)` |
| 170 | `@teacher_or_admin_required` | `@permission_required('activity.change_studentactivity', raise_exception=True)` |
| 189 | `@teacher_or_admin_required` | `@permission_required('activity.change_studentactivity', raise_exception=True)` |
| 235 | `@teacher_or_admin_required` | `@permission_required('activity.change_studentactivity', raise_exception=True)` |

- [ ] **Step 4: Re-run tests — all 6 must pass**

```bash
python3 manage.py test roles.tests.test_gating_gradebook -v 2
```
Expected: 6/6 pass.

- [ ] **Step 5: Run the full gradebookcomponent test suite to confirm no regressions**

```bash
python3 manage.py test gradebookcomponent -v 2
```
Expected: all pre-existing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add gradebookcomponent/views/instructor_grading.py roles/tests/test_gating_gradebook.py
git commit -m "feat(gradebook): gate instructor views by activity.studentactivity perms"
```

---

## Task 6: Swap decorators in `ide/views.py` (3 callsites)

**Files:**
- Modify: `ide/views.py`
- Create: `roles/tests/test_gating_ide.py`

- [ ] **Step 1: Write failing tests for the 3 IDE callsites**

Create `roles/tests/test_gating_ide.py`:

```python
"""[Classedge LMS] Gating tests for ide/views.py teacher-facing routes."""
from django.test import Client, TestCase
from django.urls import reverse

from ide.models import CodingExercise, CodeSubmission
from gradebookcomponent.tests.helpers import make_activity, make_subject
from roles.tests.helpers import make_it_admin, make_user_with_role


class IdeGatingTests(TestCase):

    def setUp(self):
        self.teacher = make_user_with_role("phase2_ide_teacher", "Teacher")
        self.student = make_user_with_role("phase2_ide_student", "Student")
        self.it_admin = make_it_admin(username="phase2_ide_itadmin")
        self.subject = make_subject(self.teacher, name="CS 101")
        self.activity = make_activity(self.subject, quiz_type_name="Coding")
        self.exercise = CodingExercise.objects.create(
            activity=self.activity,
            language="python",
            starter_code="",
            test_cases=[],
        )
        self.submission = CodeSubmission.objects.create(
            exercise=self.exercise,
            student=self.student,
            code="",
            status="completed",
            score=0.5,
        )
        self.client = Client()

    def _assert_gating(self, url, *, method="get", post_data=None):
        self.client.force_login(self.teacher)
        resp = getattr(self.client, method)(url, data=post_data or {})
        self.assertIn(resp.status_code, (200, 302))
        self.client.force_login(self.student)
        resp = getattr(self.client, method)(url, data=post_data or {})
        self.assertEqual(resp.status_code, 403)
        self.client.force_login(self.it_admin)
        resp = getattr(self.client, method)(url, data=post_data or {})
        self.assertIn(resp.status_code, (200, 302))

    def test_coding_overview(self):
        self._assert_gating(reverse("coding_overview"))

    def test_coding_exercise_results(self):
        self._assert_gating(
            reverse("coding_exercise_results", args=[self.exercise.id])
        )

    def test_coding_score_override(self):
        self._assert_gating(
            reverse("coding_score_override", args=[self.submission.id]),
            method="post",
            post_data={"new_score": "0.75", "override_note": "x"},
        )
```

> **Verify URL names + CodingExercise/CodeSubmission required fields** against `ide/urls.py` and `ide/models.py`. Adjust constructor kwargs if model fields differ.

- [ ] **Step 2: Run tests, observe expected failures**

```bash
python3 manage.py test roles.tests.test_gating_ide -v 2
```
Expected: at least the Student-denied assertions may pass coincidentally under the role-name decorator; that is fine — re-verifying after the swap is the contract.

- [ ] **Step 3: Swap decorators in `ide/views.py`**

a. Update imports: remove `teacher_or_admin_required` from the `from roles.decorators import ...` line; if it leaves the import empty, delete the whole line. Add `from django.contrib.auth.decorators import login_required, permission_required` (preserving the existing `login_required` import).

b. Replace decorators:

| Line | Current | Replace with |
|---|---|---|
| 141 | `@teacher_or_admin_required` | `@permission_required('ide.view_codingexercise', raise_exception=True)` |
| 178 | `@teacher_or_admin_required` | `@permission_required('ide.view_codingexercise', raise_exception=True)` |
| 210 | `@teacher_or_admin_required` | `@permission_required('ide.change_codesubmission', raise_exception=True)` |

- [ ] **Step 4: Re-run tests — all 3 must pass**

```bash
python3 manage.py test roles.tests.test_gating_ide -v 2
```
Expected: 3/3 pass.

- [ ] **Step 5: Run full ide test suite**

```bash
python3 manage.py test ide -v 2
```
Expected: pre-existing IDE tests still pass.

- [ ] **Step 6: Commit**

```bash
git add ide/views.py roles/tests/test_gating_ide.py
git commit -m "feat(ide): gate teacher views by ide.codingexercise/codesubmission perms"
```

---

## Task 7: Swap decorators in `gamification/views.py` (4 callsites — badge management)

**Files:**
- Modify: `gamification/views.py`
- Create: `roles/tests/test_gating_gamification_badges.py`

- [ ] **Step 1: Write failing tests**

Create `roles/tests/test_gating_gamification_badges.py`:

```python
"""[Classedge LMS] Gating tests for gamification/views.py badge management."""
from django.test import Client, TestCase
from django.urls import reverse

from gamification.models import BadgeDefinition
from roles.tests.helpers import make_it_admin, make_user_with_role


class GamificationBadgeGatingTests(TestCase):

    def setUp(self):
        self.teacher = make_user_with_role("phase2_g_teacher", "Teacher")
        self.student = make_user_with_role("phase2_g_student", "Student")
        self.it_admin = make_it_admin(username="phase2_g_itadmin")
        self.badge = BadgeDefinition.objects.create(
            name="Test Badge",
            description="x",
            icon="",
            tier="bronze",
            criteria_json={"type": "general"},
            is_active=True,
        )
        self.client = Client()

    def _assert_gating(self, url, *, method="get", post_data=None):
        self.client.force_login(self.teacher)
        resp = getattr(self.client, method)(url, data=post_data or {})
        self.assertIn(resp.status_code, (200, 302))
        self.client.force_login(self.student)
        resp = getattr(self.client, method)(url, data=post_data or {})
        self.assertEqual(resp.status_code, 403)
        self.client.force_login(self.it_admin)
        resp = getattr(self.client, method)(url, data=post_data or {})
        self.assertIn(resp.status_code, (200, 302))

    def test_badge_list(self):
        self._assert_gating(reverse("badge_management"))

    def test_badge_toggle_active(self):
        self._assert_gating(
            reverse("badge_toggle_active", args=[self.badge.id]),
            method="post",
        )

    def test_badge_edit(self):
        self._assert_gating(reverse("badge_edit", args=[self.badge.id]))

    def test_badge_manual_award(self):
        self._assert_gating(
            reverse("badge_manual_award", args=[self.badge.id])
        )
```

> **Verify URL names + BadgeDefinition required fields** against `gamification/urls.py` and `gamification/models.py`. Adjust if needed.

- [ ] **Step 2: Run tests; expect failures or coincidental passes**

```bash
python3 manage.py test roles.tests.test_gating_gamification_badges -v 2
```

- [ ] **Step 3: Swap decorators in `gamification/views.py`**

a. Imports: remove `teacher_or_admin_required` from the `roles.decorators` import; add `from django.contrib.auth.decorators import permission_required` if absent (it's already imported in many gamification files — verify).

b. Replace decorators:

| Line | View | Replace with |
|---|---|---|
| 420 | `badge_list` | `@permission_required('gamification.view_badgedefinition', raise_exception=True)` |
| 444 | `badge_toggle_active` | `@permission_required('gamification.change_badgedefinition', raise_exception=True)` |
| 454 | `badge_edit` | `@permission_required('gamification.change_badgedefinition', raise_exception=True)` |
| 475 | `badge_manual_award` | `@permission_required('gamification.add_studentbadge', raise_exception=True)` |

- [ ] **Step 4: Re-run tests**

```bash
python3 manage.py test roles.tests.test_gating_gamification_badges -v 2
```
Expected: 4/4 pass.

- [ ] **Step 5: Commit**

```bash
git add gamification/views.py roles/tests/test_gating_gamification_badges.py
git commit -m "feat(gamification): gate badge views by badge/studentbadge perms"
```

---

## Task 8: Swap decorator in `gamification/teacher_views.py` (1 callsite — `send_recognition`)

**Files:**
- Modify: `gamification/teacher_views.py`
- Create: `roles/tests/test_gating_gamification_teacher.py`

- [ ] **Step 1: Write failing test**

Create `roles/tests/test_gating_gamification_teacher.py`:

```python
"""[Classedge LMS] Gating test for gamification/teacher_views.py:send_recognition."""
import json

from django.test import Client, TestCase
from django.urls import reverse

from roles.tests.helpers import make_it_admin, make_user_with_role


class SendRecognitionGatingTests(TestCase):

    def setUp(self):
        self.teacher = make_user_with_role("phase2_tv_teacher", "Teacher")
        self.student = make_user_with_role("phase2_tv_student", "Student")
        self.it_admin = make_it_admin(username="phase2_tv_itadmin")
        # Create a target student to send recognition to (must be valid).
        self.target = make_user_with_role("phase2_tv_target", "Student")
        self.client = Client()
        self.url = reverse("send_recognition")
        self.payload = json.dumps({
            "student_id": self.target.id,
            "message": "Great job!",
            "xp_amount": 10,
        })

    def _post_as(self, user):
        self.client.force_login(user)
        return self.client.post(
            self.url, data=self.payload, content_type="application/json",
        )

    def test_teacher_passes(self):
        resp = self._post_as(self.teacher)
        self.assertNotEqual(resp.status_code, 403)

    def test_student_denied(self):
        resp = self._post_as(self.student)
        self.assertEqual(resp.status_code, 403)

    def test_it_admin_passes(self):
        resp = self._post_as(self.it_admin)
        self.assertNotEqual(resp.status_code, 403)
```

- [ ] **Step 2: Run test**

```bash
python3 manage.py test roles.tests.test_gating_gamification_teacher -v 2
```

- [ ] **Step 3: Swap decorator in `gamification/teacher_views.py`**

a. Update import on line 12: change `from roles.decorators import teacher_or_admin_required` to either delete (if no other uses in file) or remove just `teacher_or_admin_required` from the import list. Add `from django.contrib.auth.decorators import login_required, permission_required` (preserving `login_required`).

b. Replace line 19 (`@teacher_or_admin_required`) with:

```python
@permission_required('gamification.add_teacherrecognition', raise_exception=True)
```

- [ ] **Step 4: Re-run test, expect 3/3 pass**

```bash
python3 manage.py test roles.tests.test_gating_gamification_teacher -v 2
```

- [ ] **Step 5: Commit**

```bash
git add gamification/teacher_views.py roles/tests/test_gating_gamification_teacher.py
git commit -m "feat(gamification): gate send_recognition by gamification.add_teacherrecognition"
```

---

## Task 9: Swap decorators in `gamification/subject_analytics.py` (2 callsites)

**Files:**
- Modify: `gamification/subject_analytics.py`
- Create: `roles/tests/test_gating_subject_analytics.py`

- [ ] **Step 1: Write failing tests**

Create `roles/tests/test_gating_subject_analytics.py`:

```python
"""[Classedge LMS] Gating tests for gamification/subject_analytics.py."""
from django.test import Client, TestCase
from django.urls import reverse

from gradebookcomponent.tests.helpers import make_subject
from roles.tests.helpers import make_it_admin, make_user_with_role


class SubjectAnalyticsGatingTests(TestCase):

    def setUp(self):
        self.teacher = make_user_with_role("phase2_sa_teacher", "Teacher")
        self.student = make_user_with_role("phase2_sa_student", "Student")
        self.it_admin = make_it_admin(username="phase2_sa_itadmin")
        self.subject = make_subject(self.teacher, name="Phys 101")
        self.client = Client()

    def _assert_gating(self, url):
        self.client.force_login(self.teacher)
        self.assertIn(self.client.get(url).status_code, (200, 302))
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.it_admin)
        self.assertIn(self.client.get(url).status_code, (200, 302))

    def test_subject_panel_view(self):
        self._assert_gating(
            reverse("subject_panel_view", args=[self.subject.id])
        )

    def test_student_detail_view(self):
        self._assert_gating(
            reverse("student_detail_view", args=[self.subject.id, self.student.id])
        )
```

> **Verify URL names** against `gamification/urls.py`.

- [ ] **Step 2: Run tests**

```bash
python3 manage.py test roles.tests.test_gating_subject_analytics -v 2
```

- [ ] **Step 3: Swap decorators in `gamification/subject_analytics.py`**

a. Imports: remove `teacher_or_admin_required` from `roles.decorators` import; add `from django.contrib.auth.decorators import permission_required`.

b. Replace decorators:

| Line | View | Replace with |
|---|---|---|
| 55 | `subject_panel_view` | `@permission_required('gamification.view_studentgamification', raise_exception=True)` |
| 173 | `student_detail_view` | `@permission_required('gamification.view_studentgamification', raise_exception=True)` |

- [ ] **Step 4: Re-run tests**

```bash
python3 manage.py test roles.tests.test_gating_subject_analytics -v 2
```
Expected: 2/2 pass.

- [ ] **Step 5: Commit**

```bash
git add gamification/subject_analytics.py roles/tests/test_gating_subject_analytics.py
git commit -m "feat(gamification): gate subject_analytics by gamification.view_studentgamification"
```

---

## Task 10: Drop redundant decorator in `module/views/crud_views.py` (1 callsite)

**Files:**
- Modify: `module/views/crud_views.py`
- Create: `roles/tests/test_gating_module.py`

This callsite already has `@permission_required('module.delete_module', raise_exception=True)` directly under the legacy decorator. We just delete the legacy one — no replacement.

- [ ] **Step 1: Write failing test**

Create `roles/tests/test_gating_module.py`:

```python
"""[Classedge LMS] Gating test for module/views/crud_views.py:deleteModule.

Today this view is double-gated by @teacher_or_admin_required AND
@permission_required('module.delete_module'). Phase 2 drops the role
decorator; the perm decorator alone must continue to gate correctly.
"""
from django.test import Client, TestCase
from django.urls import reverse

from gradebookcomponent.tests.helpers import make_subject
from module.models.module import Module
from roles.tests.helpers import make_it_admin, make_user_with_role


class ModuleDeleteGatingTests(TestCase):

    def setUp(self):
        self.teacher = make_user_with_role("phase2_m_teacher", "Teacher")
        # Teacher must also have module.delete_module — grant it directly
        # since PHASE2_GRANTS doesn't include this perm (it's pre-existing).
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get(app_label="module", model="module")
        perm = Permission.objects.get(content_type=ct, codename="delete_module")
        teacher_role = self.teacher.profile.role
        teacher_role.permissions.add(perm)

        self.student = make_user_with_role("phase2_m_student", "Student")
        self.it_admin = make_it_admin(username="phase2_m_itadmin")
        self.subject = make_subject(self.teacher, name="Music 101")
        self.module = Module.objects.create(
            module_name="Lesson 1", subject=self.subject,
        )
        self.url = reverse("deleteModule", args=[self.module.id])
        self.client = Client()

    def test_teacher_with_perm_passes(self):
        self.client.force_login(self.teacher)
        resp = self.client.post(self.url)
        self.assertIn(resp.status_code, (200, 302))

    def test_student_without_perm_denied(self):
        self.client.force_login(self.student)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_it_admin_passes(self):
        self.client.force_login(self.it_admin)
        resp = self.client.post(self.url)
        self.assertIn(resp.status_code, (200, 302))
```

> **Verify URL name + Module field names** (`module_name`, `subject`) against the module app.

- [ ] **Step 2: Run tests**

```bash
python3 manage.py test roles.tests.test_gating_module -v 2
```

- [ ] **Step 3: Drop the redundant decorator in `module/views/crud_views.py:47`**

Remove only the line `@teacher_or_admin_required` (line 47). Keep `@permission_required('module.delete_module', raise_exception=True)` directly below it. Also remove `teacher_or_admin_required` from the `from roles.decorators import ...` import; if it leaves the import empty, delete the whole line.

- [ ] **Step 4: Re-run tests, expect 3/3 pass**

```bash
python3 manage.py test roles.tests.test_gating_module -v 2
```

- [ ] **Step 5: Run full module test suite to confirm no regression**

```bash
python3 manage.py test module -v 2
```

- [ ] **Step 6: Commit**

```bash
git add module/views/crud_views.py roles/tests/test_gating_module.py
git commit -m "refactor(module): drop redundant @teacher_or_admin_required from deleteModule"
```

---

## Task 11: Delete legacy decorators + import-hygiene test

**Files:**
- Modify: `roles/decorators.py`
- Create: `roles/tests/test_legacy_decorators_removed.py`

- [ ] **Step 1: Write the import-hygiene test (must fail right now)**

Create `roles/tests/test_legacy_decorators_removed.py`:

```python
"""[Classedge LMS] Phase 2 — verify legacy role-name decorators are gone."""
from django.test import TestCase


class LegacyDecoratorsRemovedTests(TestCase):
    """[Classedge LMS] roles.decorators must not expose the four role-name decorators."""

    LEGACY_NAMES = (
        "teacher_required",
        "student_required",
        "registrar_required",
        "teacher_or_admin_required",
    )

    def test_legacy_decorators_not_importable(self):
        import roles.decorators as d
        for name in self.LEGACY_NAMES:
            self.assertFalse(
                hasattr(d, name),
                f"{name} should have been deleted in Phase 2 but is still in roles.decorators",
            )

    def test_admin_required_still_present(self):
        """[Classedge LMS] @admin_required is intentionally kept (Phase 1's superuser shim)."""
        import roles.decorators as d
        self.assertTrue(hasattr(d, "admin_required"))
```

- [ ] **Step 2: Run test — confirm `test_legacy_decorators_not_importable` fails**

```bash
python3 manage.py test roles.tests.test_legacy_decorators_removed -v 2
```
Expected: `test_legacy_decorators_not_importable` fails (decorators still present); `test_admin_required_still_present` passes.

- [ ] **Step 3: Delete the four legacy decorators in `roles/decorators.py`**

Replace the entire contents of `roles/decorators.py` with:

```python
# In decorators.py

from django.core.exceptions import PermissionDenied


def admin_required(view_func):
    """[Classedge LMS] IT Admin only — strict is_superuser check (set by Phase 1).

    Kept as a decorator (not @permission_required) because IT Admin is the
    sole superuser-bypass role; expressing it as a permission would falsely
    imply the gate is delegable to other roles. Used by roles/views.py for
    role-CRUD endpoints.
    """
    def _wrapped_view_func(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view_func
```

- [ ] **Step 4: Verify nothing in the codebase still imports the deleted decorators**

```bash
git grep '@teacher_or_admin_required\|@teacher_required\|@student_required\|@registrar_required' -- ':!docs' ':!*.md'
```
Expected: zero matches.

```bash
git grep 'from roles.decorators import' -- ':!docs' ':!*.md'
```
Expected: every match imports only `admin_required` (or imports nothing — i.e., no remaining imports from this module besides `admin_required` in `roles/views.py`).

- [ ] **Step 5: Re-run import-hygiene tests — both must pass**

```bash
python3 manage.py test roles.tests.test_legacy_decorators_removed -v 2
```
Expected: 2/2 pass.

- [ ] **Step 6: Run the full test suite**

```bash
python3 manage.py test -v 2
```
Expected: all tests pass — Phase 1's 24 + Phase 2's ~19 + all pre-existing project tests.

- [ ] **Step 7: Commit**

```bash
git add roles/decorators.py roles/tests/test_legacy_decorators_removed.py
git commit -m "refactor(roles): delete four legacy role-name decorators (Phase 2 cutover)"
```

---

## Task 12: Final verification + push + open PR

**Files:**
- (no file changes)

- [ ] **Step 1: Final grep check**

```bash
git grep '@teacher_or_admin_required\|@teacher_required\|@student_required\|@registrar_required' -- ':!docs' ':!*.md'
```
Expected: zero matches.

- [ ] **Step 2: Manage `manage.py check`**

```bash
python3 manage.py check
```
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 3: Apply migrations on a fresh DB locally to confirm clean run**

```bash
python3 manage.py migrate --run-syncdb
```
Expected: all migrations apply, including `roles 0004_grant_phase2_perms`. No errors.

- [ ] **Step 4: Push the branch**

```bash
git push -u personal feat/permission-decorator-migration
```

- [ ] **Step 5: Open PR to `main` on the `personal` fork**

Use the GitHub UI or `gh pr create`:

```bash
gh pr create --base main --head feat/permission-decorator-migration \
  --title "Phase 2: Permission-decorator migration (replace @teacher_or_admin_required)" \
  --body "$(cat <<'EOF'
## Summary
- Replaces `@teacher_or_admin_required` on 17 instructor-facing callsites with `@permission_required(...)` using existing Django auto-generated model perms.
- Deletes four legacy role-name decorators (`teacher_required`, `student_required`, `registrar_required`, `teacher_or_admin_required`).
- Adds Django data migration `roles/0004_grant_phase2_perms.py` granting the migrated perms to existing roles per the design matrix.
- Adds 17 per-callsite gating tests + data-migration test + import-hygiene test (~19 new tests).

**Spec:** `docs/superpowers/specs/2026-04-23-permission-decorator-migration-design.md`

## Operator note
If your school has custom teacher-equivalent roles created via the `/roleList/` UI (beyond Teacher/Program Head/Academic Dean/Academic Director/Registrar), the IT Admin must manually grant the perm set to them via `/roleList/` after this PR deploys. The migration only knows about the canonical roles enumerated in the spec §4 matrix.

## Test plan
- [ ] CI green: data-migration test, 17 gating tests, import-hygiene test.
- [ ] Manual QA on staging: Teacher → gradebook works; Program Head → gradebook read-only works; Student → 403 on gradebook; IT Admin → 200 on everything.
- [ ] `git grep '@teacher_or_admin_required\|@teacher_required\|@student_required\|@registrar_required'` returns zero matches.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 6: Update project memory**

After the PR is merged, update `~/.claude/projects/-Users-macbok16-a/memory/project_classedge_it_admin_refactor.md` to mark Phase 2 as SHIPPED with the PR link, and confirm Phase 3 is the next pending phase.
