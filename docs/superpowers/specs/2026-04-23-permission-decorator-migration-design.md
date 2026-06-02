# Phase 2 — Permission-decorator migration (Classedge LMS)

**Date:** 2026-04-23
**Phase:** 2 of 3 (user/role/permission refactor)
**Depends on:** Phase 1 — IT Admin role foundation (PR #2, branch `feat/it-admin-role-foundation`). Phase 2 implementation does not begin until Phase 1 is merged into `main`.
**Branch (planned):** `feat/permission-decorator-migration`, cut from `main` post-Phase-1 merge.

## 1. Goal

Replace role-name gating with permission-based gating for all teacher-facing instructor surfaces in Classedge LMS, so future role changes (e.g., a "Junior Teacher" role) require only a permission grant in the `/roleList/` UI rather than a code change.

## 2. Scope

### In scope

- Replace `@teacher_or_admin_required` on **17 callsites** across:
  - `gradebookcomponent/views/instructor_grading.py` — 6
  - `gamification/views.py` — 4 (badge management)
  - `gamification/teacher_views.py` — 1 (`send_recognition`)
  - `gamification/subject_analytics.py` — 2
  - `ide/views.py` — 3
  - `module/views/crud_views.py` — 1 (drop only — already gated by `module.delete_module`)
- Hard-delete the four legacy role-name decorators from `roles/decorators.py`:
  - `teacher_required` (0 callsites today, dead code)
  - `student_required` (0 callsites today, dead code)
  - `registrar_required` (0 callsites today, dead code)
  - `teacher_or_admin_required` (17 callsites, replaced by this spec)
- Data migration that grants the new permissions to existing roles per the matrix in §4.
- Per-callsite regression tests (~17 tests, ~50 assertions) plus a data-migration test and an import-hygiene test.

### Out of scope (explicitly)

- `@admin_required` and the 9 `roles/views.py` callsites that use it. Phase 1 already simplified `@admin_required` to a strict `is_superuser` check, which is the correct expression of "IT Admin only" since IT Admin is exclusive (no impersonation, no dual role) and tied to `is_superuser`. Replacing those decorators with `@permission_required` would create the false impression that role management is delegable, contradicting Phase 1's design.
- The 127 `role.name.lower()` ad-hoc role-string checks scattered across `calendars/`, `course/views/attendance_views.py`, `course/views/subject_details_views.py`, `course/views/coil_and_hali_subject_views.py`, etc. Those are display/branching logic, not access gates, and require per-callsite semantic judgment unrelated to decorator migration. Defer to a later phase.
- Any access-policy expansion beyond the gap-fill matrix in §4.

### Non-goal: behavior change

With the gap-fill exception below, post-deploy access behavior must equal pre-deploy access behavior for every existing role. The data migration is the contract.

## 3. Permission-mapping table

All 17 callsites map to existing Django auto-generated model permissions. **Zero new custom permissions are needed.**

| # | File:Line | View | New decorator (replaces `@teacher_or_admin_required`) |
|---|---|---|---|
| 1 | gradebookcomponent/views/instructor_grading.py:55 | `gradebook_home` | `@permission_required('activity.view_studentactivity', raise_exception=True)` |
| 2 | …:78 | `subject_gradebook` | `@permission_required('activity.view_studentactivity', raise_exception=True)` |
| 3 | …:136 | `subject_gradebook_csv` | `@permission_required('activity.view_studentactivity', raise_exception=True)` |
| 4 | …:170 | `grading_queue` | `@permission_required('activity.change_studentactivity', raise_exception=True)` |
| 5 | …:189 | `grade_submission` | `@permission_required('activity.change_studentactivity', raise_exception=True)` |
| 6 | …:235 | `override_score` | `@permission_required('activity.change_studentactivity', raise_exception=True)` |
| 7 | module/views/crud_views.py:47 | `deleteModule` | **(drop only — already gated by `module.delete_module`)** |
| 8 | ide/views.py:141 | `coding_overview` | `@permission_required('ide.view_codingexercise', raise_exception=True)` |
| 9 | ide/views.py:178 | `coding_exercise_results` | `@permission_required('ide.view_codingexercise', raise_exception=True)` |
| 10 | ide/views.py:210 | `coding_score_override` | `@permission_required('ide.change_codesubmission', raise_exception=True)` |
| 11 | gamification/teacher_views.py:19 | `send_recognition` | `@permission_required('gamification.add_teacherrecognition', raise_exception=True)` |
| 12 | gamification/views.py:420 | `badge_list` | `@permission_required('gamification.view_badgedefinition', raise_exception=True)` |
| 13 | gamification/views.py:444 | `badge_toggle_active` | `@permission_required('gamification.change_badgedefinition', raise_exception=True)` |
| 14 | gamification/views.py:454 | `badge_edit` | `@permission_required('gamification.change_badgedefinition', raise_exception=True)` |
| 15 | gamification/views.py:475 | `badge_manual_award` | `@permission_required('gamification.add_studentbadge', raise_exception=True)` |
| 16 | gamification/subject_analytics.py:55 | `subject_panel_view` | `@permission_required('gamification.view_studentgamification', raise_exception=True)` |
| 17 | gamification/subject_analytics.py:173 | `student_detail_view` | `@permission_required('gamification.view_studentgamification', raise_exception=True)` |

**Distinct permissions used (8 total, all auto-generated):**
- `activity.view_studentactivity` (3), `activity.change_studentactivity` (3)
- `ide.view_codingexercise` (2), `ide.change_codesubmission` (1)
- `gamification.add_teacherrecognition` (1), `gamification.view_badgedefinition` (1), `gamification.change_badgedefinition` (2), `gamification.add_studentbadge` (1), `gamification.view_studentgamification` (2)

## 4. Data migration

### Matrix — role × permission grants

| Role | Permissions granted by migration |
|---|---|
| **Teacher** | `activity.view_studentactivity`, `activity.change_studentactivity`, `ide.view_codingexercise`, `ide.change_codesubmission`, `gamification.add_teacherrecognition`, `gamification.view_badgedefinition`, `gamification.change_badgedefinition`, `gamification.add_studentbadge`, `gamification.view_studentgamification` (the 9 perms required by the swapped callsites — preserves today's `@teacher_or_admin_required` access exactly. `module.delete_module`, used by the one module callsite, is assumed already present on the Teacher role since `deleteModule` has been working in production; if the migration test reveals it is not, add it here.) |
| **Program Head** *(if exists)* | `activity.view_studentactivity`, `gamification.view_studentgamification`, `module.view_module` (gradebook read + analytics read + module read) |
| **Academic Dean** *(if exists)* | same as Program Head |
| **Academic Director** *(if exists)* | same as Program Head |
| **Registrar** *(if exists)* | `activity.view_studentactivity` (gradebook read only — for transcript workflows) |
| **IT Admin** | (no migration action — bypasses everything via `is_superuser`) |
| **Student / others** | (no migration action — keeps current denial behavior) |

The Program Head/Dean/Director/Registrar grants are the "fix-known-gaps" expansion bundled with the behavior-preserving migration. They mirror the existing `['admin', 'program head', 'dean']` role-string checks already present in `course/views/subject_details_views.py` for subject viewing — the intent of those existing checks extends naturally to gradebook read access.

### Mechanism

New Django data migration in `roles/migrations/`, next sequential number after Phase 1's rename migration. Uses `RunPython` with forward + reverse functions, idempotent.

**Forward operation.** For each `(role_name, [perm_codenames])` entry in the matrix:
1. `role = Role.objects.filter(name=role_name).first()` — if `None`, log info "skipping <role>: not present" and continue (do not error).
2. For each codename, resolve `Permission.objects.get(content_type__app_label=..., codename=...)`. If the permission itself is missing (shouldn't happen — Django auto-creates them at migrate time), log warning and skip.
3. `role.permissions.add(*resolved_perms)` — `add()` is idempotent for M2M.

**Reverse operation.** Symmetric — removes the same perms from the same roles using `role.permissions.remove(*resolved_perms)`. Allows clean rollback during testing or post-deploy.

**Idempotency contract.** Re-running the migration must be a no-op. M2M `add()` gives this for free; the role-existence check handles roles created later.

**What the migration does NOT do.**
- Does not create any roles. Roles like Program Head must already exist (via IT Admin role-CRUD or earlier seed). If they don't, those rows are skipped with a log line.
- Does not touch any user's role assignment. Profiles unchanged.
- Does not grant or revoke perms on Teachers' personal user accounts (Django `User.user_permissions`). Operates only on `Role.permissions`.

**Coupling to Phase 1.** This migration runs after Phase 1's rename migration ("Admin" → "IT Admin"). Since Phase 2 doesn't grant perms to "IT Admin" anyway (superuser bypass handles it), the rename has no impact on this migration's correctness.

## 5. Decorator deletion (hard cutover)

### `roles/decorators.py` — final state after Phase 2

Phase 1 leaves `@admin_required` (a strict `is_superuser` shim, kept for the 9 `roles/views.py` gates). Phase 2 deletes the four legacy role-name decorators. Final file is ~10 lines:

```python
from django.core.exceptions import PermissionDenied


def admin_required(view_func):
    """[Classedge LMS] IT Admin only — strict is_superuser check (set by Phase 1).

    Kept as a decorator (not @permission_required) because IT Admin is the
    sole superuser-bypass role; expressing it as a permission would falsely
    imply the gate is delegable to other roles.
    """
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped
```

Deleted: `teacher_required`, `student_required`, `registrar_required`, `teacher_or_admin_required`.

### Per-callsite mechanics for the 17 swaps

For each of the 6 affected view files:
1. Remove `from roles.decorators import teacher_or_admin_required` (replace with the new import only if `admin_required` is still needed — none of the 6 files use it; verified).
2. Add `from django.contrib.auth.decorators import permission_required` if not already imported (`module/views/crud_views.py` already has it).
3. For each `@teacher_or_admin_required` line, replace with the corresponding `@permission_required(...)` from §3.
4. For `module/views/crud_views.py:47` only: just delete the `@teacher_or_admin_required` line — `@permission_required('module.delete_module', raise_exception=True)` is already there directly below it.

**Decorator stacking order convention** (matches the existing 112 `@permission_required` callsites in the codebase): `@login_required` first, `@permission_required(...)` second, then HTTP-method decorators like `@require_POST`. Most of the 17 callsites already have this shape with `@teacher_or_admin_required` slotted in the middle — replacement preserves position.

## 6. Testing strategy

### Test inventory

- **17 per-callsite gating tests** — one per row in §3's table. Each is a distinct test function (not parameterized) so a single failure pinpoints exactly which view regressed.
- **1 data-migration test** — fresh DB with all 6 named roles created, run migration forward, assert exact perm sets per role, run again (idempotency), run reverse, assert clean.
- **1 import-hygiene test** — asserts the four legacy decorators are no longer importable from `roles.decorators` (catches accidental re-introduction).

Total: ~19 test functions, ~55 assertions.

### Test file location

New file `roles/tests/test_permission_gating.py` (matching Phase 1's pattern of `roles/tests/...`). The data-migration test lives there too — it's all about role/permission wiring.

### Per-callsite test pattern

```python
def test_subject_gradebook_gating(client):
    teacher_user = make_user_with_role("Teacher", grant_perms=True)
    other_user   = make_user_with_role("Student", grant_perms=False)
    superuser    = make_it_admin()
    url = reverse("subject_gradebook", args=[some_subject.id])

    # 200: teacher with the migrated perm
    client.force_login(teacher_user)
    assert client.get(url).status_code == 200

    # 403: role without the perm
    client.force_login(other_user)
    assert client.get(url).status_code == 403

    # 200: IT Admin (superuser bypass)
    client.force_login(superuser)
    assert client.get(url).status_code == 200
```

Helper `make_user_with_role(role_name, grant_perms=True)` lives in `roles/tests/helpers.py`. It creates the role if needed, optionally runs the data-migration's grant logic for that role, creates a user, assigns `profile.role`, returns the user. Check `gradebookcomponent/tests/helpers.py:create_user_with_role` first — reuse if it does the right thing.

### What's NOT tested per callsite (deliberately)

Keeps tests focused on the gating contract, not view behavior:
- Response body content (covered by Phase 1's existing 24 tests + per-feature tests).
- Object-level authorization (e.g., `authorize_subject_access` in gradebook views — separate layer with its own tests).
- HTTP method mismatches (decorator stacking handles this).

### Import-hygiene test

```python
def test_legacy_decorators_removed():
    import roles.decorators as d
    for name in ("teacher_required", "student_required",
                 "registrar_required", "teacher_or_admin_required"):
        assert not hasattr(d, name), f"{name} should have been deleted in Phase 2"
```

### Test setup gotchas

- `accounts/utils/signal_utils.py` auto-creates a Profile with role "Student" on `CustomUser` creation. Tests that need a Teacher user must update the profile after creation (`profile.role = teacher_role; profile.save()`) — which then triggers Phase 1's transition-aware `is_superuser` signal correctly. Don't bypass the signal.
- Use the data-migration's grant function directly in `make_user_with_role` rather than re-implementing the perm-grant logic inline.

### CI expectation

Combined Phase 1 (24 tests) + Phase 2 (~19 tests) = ~43 tests in `roles/tests/`. All must pass before merge.

## 7. Branching, sequencing, rollout

### Branch

`feat/permission-decorator-migration`, cut from `main` **after** PR #2 (Phase 1) merges. No work begins on the branch until Phase 1 is in main.

### Implementation sequence (single PR, commits ordered for bisectability)

1. **Commit 1 — data migration.** New `roles/migrations/00XX_grant_phase2_perms.py` with forward + reverse `RunPython`. No view changes yet. Migration is a no-op behaviorally because nothing checks the new perms yet — but it's safe to apply ahead of code.
2. **Commit 2 — migration test.** New `roles/tests/test_permission_gating.py` with the data-migration test only. Verifies Commit 1 in isolation.
3. **Commit 3 — replace 17 decorators + update imports.** All 6 view files updated. `roles/decorators.py` still has the legacy decorators (kept temporarily so import-hygiene test can fail loudly in commit 5).
4. **Commit 4 — add 17 per-callsite gating tests + import-hygiene test.** The 17 gating tests pass on commit 3's state; the import-hygiene test fails until commit 5.
5. **Commit 5 — delete the four legacy decorator functions.** `roles/decorators.py` shrinks to just `admin_required`. Import-hygiene test now passes. Final `git grep` finds zero references.

This ordering means: if any commit is reverted, the system is still in a coherent state.

### Deploy / rollout

- Single deploy. Migration runs at `manage.py migrate` time (standard).
- No feature flag — the change is atomic at the deploy boundary.
- Post-deploy verification: log in as a Teacher (any existing Teacher user, no setup required) and confirm gradebook + IDE + send-recognition still work. Log in as a Program Head (if any exist in the seeded DB) and confirm gradebook read-only access works.
- Rollback if needed: re-deploy the previous build + run `manage.py migrate roles 00XX_phase1_last` to reverse Phase 2's data migration. The reverse `RunPython` cleans up the granted perms.

### Risks & mitigations

- **A Teacher user has lost access because the migration didn't run** (deploy ordering bug). *Mitigation:* The migration test in commit 2 is required to pass in CI; if migration logic itself is broken, CI catches it before deploy. Post-deploy smoke check covers operator error.
- **A role we forgot exists in production** (e.g., custom IT-Admin-created "Lead Teacher") loses access because the migration only knows about the 6 roles in the matrix. *Mitigation:* Document in PR description: "if your school has custom teacher-equivalent roles, IT Admin must grant the perm set listed in this PR via `/roleList/`." This is the cost of behavior-preserving + curated gap-fill; it's accepted.
- **The 127 `role.name.lower()` checks in non-decorator code still gate access by role string, not perm** — they don't regress *but* they also don't benefit from this refactor. *Mitigation:* Out of scope (§2); flag for a future Phase 2b.

## 8. Definition of done

1. PR opened with the 5 commits above.
2. CI green: migration test, 17 gating tests, import-hygiene test, plus all pre-existing tests.
3. `git grep '@teacher_or_admin_required\|@teacher_required\|@student_required\|@registrar_required'` returns zero matches.
4. Manual QA:
   - Teacher login → gradebook access ✓
   - Program Head login → gradebook read-only ✓
   - Student login → 403 on gradebook ✓
   - IT Admin login → 200 on everything
5. PR approved + merged into `main`.
6. Project memory `project_classedge_it_admin_refactor.md` updated to mark Phase 2 shipped, Phase 3 pending.
