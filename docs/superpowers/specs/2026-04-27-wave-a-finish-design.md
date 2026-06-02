# Wave A Finish — Design

**System:** Classedge LMS
**Status:** Drafted 2026-04-27
**Parent spec:** `docs/superpowers/specs/2026-04-25-non-teacher-student-dashboard-redesign-design.md` (merged to main as PR #14)
**Scope:** Implement the **remainder of Wave A** of the parent spec: 4 dashboards using "Operations Mode" — Registrar, Coil Admin, Academic Director, IT Admin (replaces existing scaffold).

## 1. Why this sub-project

The parent spec locks 11 dashboard designs across 4 staging Waves but stops at design. Wave A is "lowest risk because the data sources mostly exist" — it touches no new Django apps, no new models (with one stub), and exercises every section of the new shell against real data. Shipping Wave A first proves the shell, the partials, and the per-role view pattern before Wave B introduces 5 brand-new apps.

The current `templates/it_admin_base.html` (shipped during the role-rename PRs) is a Bricolage-typography scaffold, **not** Operations Mode. Replacing it is part of Wave A finish, not pre-existing work.

## 2. Locked decisions

| # | Decision |
|---|----------|
| 1 | **Foundation-first build sequence.** One PR ships shell + CSS + partials + shared test fixtures with no roles wired. Subsequent PRs each ship one role end-to-end. |
| 2 | **PR order: Foundation → Registrar → Coil Admin → Academic Director → IT Admin (redo).** IT Admin replaces working scaffold code, so it ships last after the shell is shaken out by 3 lower-risk dashboards. |
| 3 | **Coil Admin "collaborative classes" panel = stub.** Show a placeholder ("Coming soon") rather than extend `CoilPartnerSchool`. The class-level association is a separate sub-spec. |
| 4 | **Pytest view tests per role.** Each role PR includes a view test, a permission test, and a template-render test. Foundation PR provides shared `OperationsDashboardTestMixin` and fixtures. No Playwright. |
| 5 | **Parent spec merged first.** Doc-only PR #14 merged to main before this sub-project opens its first PR, so all references resolve on main. |
| 6 | **Teacher / Student paths untouched.** No edits to `teacher_base.html`, `student_base.html`, or their views. |

## 3. PR breakdown

| # | Branch | Adds | Touches existing | Estimated diff size |
|---|---|---|---|---|
| 1 | `feat/wave-a-finish-foundation` | `templates/operations_base.html`, `static/css/operations_base.css`, `templates/operations/{kpi_strip,scope_bar,worklist_panel,context_strip}.html`, `accounts/tests/operations_dashboard_mixin.py` | None | ~600 lines |
| 2 | `feat/wave-a-finish-registrar` | `accounts/views/registrar_dashboard.py`, `templates/operations/registrar_dashboard.html`, `accounts/tests/test_registrar_dashboard.py`, route entry | `accounts/views/dashboard.py` (router) | ~250 lines |
| 3 | `feat/wave-a-finish-coil-admin` | `accounts/views/coil_admin_dashboard.py`, `templates/operations/coil_admin_dashboard.html`, `accounts/tests/test_coil_admin_dashboard.py`, route entry | `accounts/views/dashboard.py` (router) | ~250 lines |
| 4 | `feat/wave-a-finish-academic-director` | `accounts/views/academic_director_dashboard.py`, `templates/operations/academic_director_dashboard.html`, `accounts/tests/test_academic_director_dashboard.py`, route entry | `accounts/views/dashboard.py` (router) | ~300 lines |
| 5 | `feat/wave-a-finish-it-admin-redo` | `accounts/views/it_admin_dashboard.py` (rewritten), `templates/operations/it_admin_dashboard.html`, `accounts/tests/test_it_admin_dashboard.py` | **Deletes** `templates/it_admin_base.html` and `templates/it_admin/dashboard.html`; updates router | ~350 lines |

Each PR targets `main`, opens against `personal` remote (per `feedback_classedge_remote.md`), uses merge commits (matching project style), deletes its branch on merge.

## 4. Architecture

### 4.1 Shell — `operations_base.html`

`operations_base.html` is itself a base template (it does not extend anything else). Its body skeleton:

```
<aside class="ops-side">
  <div class="brand">…</div>
  <div class="role-tag">{{ role_glyph }} {{ role_tag }}</div>
  <nav>{% for item in nav_items %}…{% endfor %}</nav>
  <div class="user-block">…</div>
</aside>
<main>
  {% include 'operations/scope_bar.html' with tags=scope_tags %}
  <header class="greeting">
    <h1>Good {{ time_of_day }}, {{ request.user.first_name }}</h1>
    <p class="walk-in"><em>{{ greeting_question }}</em></p>
    <div class="actions">{% for a in quick_actions %}…{% endfor %}</div>
  </header>
  {% include 'operations/kpi_strip.html' with kpis=kpis %}
  <section class="grid-main">
    <div class="primary">{% block primary_panel %}{% endblock %}</div>
    <div class="secondary">{% block secondary_panel %}{% endblock %}</div>
  </section>
  {% include 'operations/context_strip.html' with left=ctx_left right=ctx_right %}
</main>
```

Each role's template extends `operations_base.html` and overrides `primary_panel` and `secondary_panel`. Everything else is data-driven via context dict.

### 4.2 CSS — `operations_base.css`

All design tokens from parent spec §4.3 (cream/forest/gold/rose/ink) live here. Class names: `.ops-shell`, `.ops-side`, `.scope-bar`, `.kpi-strip`, `.kpi`, `.kpi.warn`, `.kpi.ok`, `.grid-main`, `.context-strip`. No inline styles in role templates — if a role needs custom styling, it goes through new utility classes added to this stylesheet, not per-role `<style>` blocks.

### 4.3 Per-role view module

Each `<role>_dashboard.py` exports one view function decorated with `@login_required` and `@role_required(<role_name>)`. The view computes:

```python
context = {
    'role_tag': 'Registrar',
    'role_glyph': '⎙',
    'nav_items': [...],
    'scope_tags': [...],
    'greeting_question': '...',
    'quick_actions': [...],
    'time_of_day': _time_of_day(),
    'kpis': [...],
    'ctx_left': {...},
    'ctx_right': {...},
    # plus role-specific panel data referenced by the role template's overrides
}
```

KPI computation, queryset assembly, and any reframing (e.g., Academic Director's program × performance heatmap) live in this module. Test seam: each KPI is a top-level function so tests can patch / call directly.

### 4.4 Routing

`accounts/views/dashboard.py` already routes by role for Teacher / Student / IT Admin. Extend to:

```python
ROLE_TO_DASHBOARD = {
    'Teacher': teacher_dashboard,
    'Student': student_dashboard,
    'IT Admin': it_admin_dashboard,         # rewritten in PR #5
    'Registrar': registrar_dashboard,        # PR #2
    'Coil Admin': coil_admin_dashboard,      # PR #3
    'Academic Director': academic_director_dashboard,  # PR #4
}
```

Roles not in the map continue to fall through to the existing default (legacy `base.html`). Wave B/C/D will extend the same map.

## 5. Per-role data sources (Wave A only)

| Role | KPI sources | Primary panel source | Secondary panel source |
|---|---|---|---|
| **Registrar** | `accounts.Profile` (active enrollments via `Profile.section`), enrollment-request models, request audit log | Aging request queue (sorted by `created_at`, SLA-flagged at 7 days) | Request volume 14-day chart from same audit log |
| **Coil Admin** | `coil.CoilPartnerSchool` (status counts), enrolled-student count via partner-school FK, scheduled session count from `coil` calendar entries | Partner schools table (mirrors `CoilPartnerSchool.status` pipeline; pending invites first) | Funnel: Sent → Pending → Partner → Rejected. **Collaborative classes panel = stub** ("Coming soon — model pending"). |
| **Academic Director** | `gamification.AtRiskFlag` (count + Δ), `gamification.OutcomeAttainment` (avg %), `central_content.SyllabusPlan` (coverage %), `ai_content.ContentHealth` (health %) | Program × Performance Band heatmap (5 programs × 5 bands) | Pending decisions queue: SyllabusPlan approvals + content escalations, sorted oldest-first |
| **IT Admin (redo)** | Active users 24h (auth log), failed-login 1h (auth log), 5xx rate (Django log tail or fallback to placeholder), Celery queue depth (broker introspection), DB p95 latency (placeholder if `pg_stat_activity` unavailable on SQLite) | Pending requests + recent admin actions (interleaved feed from `easyaudit`) | Service health 24h tick bars (Celery / Redis / DB / web) |

**Placeholders accepted**: 5xx rate and DB p95 may render as `—` on SQLite dev; production uses the real values. The view returns `None` and the template shows a gray dash. This is documented in PR #5's description.

## 6. Test contract

### 6.1 Foundation PR

- `accounts/tests/operations_dashboard_mixin.py` — `OperationsDashboardTestMixin` providing:
  - `make_user_with_role(role_name)` fixture
  - `assert_renders_for_role(role_name)` helper
  - `assert_403_for_other_roles(role_name)` helper
  - `assert_kpi_count(response, n)` helper

### 6.2 Per-role PR

Each role test file follows this pattern (~30 lines):

```python
class RegistrarDashboardTests(OperationsDashboardTestMixin, TestCase):
    role = 'Registrar'
    glyph = '⎙'

    def test_renders_for_registrar(self): self.assert_renders_for_role(self.role)
    def test_403_for_other_roles(self): self.assert_403_for_other_roles(self.role)
    def test_kpi_count(self): ...  # 5 KPIs
    def test_aging_queue_sorted_by_age(self): ...  # role-specific
    def test_glyph_renders(self): self.assertContains(response, self.glyph)
```

Each role contributes 1 role-specific test for its primary panel sort logic — i.e., the highest-value test that catches regressions in queryset ordering. No snapshot tests, no Playwright.

## 7. Out of scope

- **Mobile breakpoints** — desktop-first, parent spec §8.
- **Dark theme** — parent spec §8.
- **Real-time refresh** (websockets / SSE) — scope bar shows static "as of" timestamp.
- **i18n** — English-only.
- **Coil collaborative-class data model** — stubbed (decision #3); real model in a separate spec.
- **Wave B/C/D roles** — Time Keeper, QA, Librarian, Guidance Counselor, Department Staff, Program Head, Principal, Parent/Guardian.
- **Visual regression / Playwright** — decision #4.
- **Permission gating per panel** — each role's nav and panels assume their permissions are present per Phase 2/3 patterns from the role refactor.
- **Migration of existing Princilpal users** — already shipped via PR #13.

## 8. Open questions

1. **IT Admin nav targets after redo.** Existing scaffold links to `admin_and_staff_list`, `roleList`, `department_list`, `sign_out`. The Operations Mode shell uses `nav_items` from the view's context. PR #5 must enumerate every existing nav target and preserve them — verify by grep before opening the PR.
2. **5xx rate / DB p95 source on dev.** SQLite has no `pg_stat_activity`. Decision: render `—` on SQLite, gated by `connection.vendor == 'postgresql'`. Document in PR #5.
3. **Academic Director fixture data.** `gamification.AtRiskFlag` / `OutcomeAttainment` / `central_content.SyllabusPlan` may not have realistic dev data. Test fixtures should include 1 program × 5 bands × N students. Confirm exact fixture shape during PR #4.

## 9. Rollback plan

Each PR is a single merge commit; rollback = `git revert <merge>`. The Operations Mode shell is namespaced to `templates/operations*` and `static/css/operations_base.css` so reverting one role's PR cannot break a different role. PR #5 (IT Admin redo) is the only PR with deletion of existing files — rollback restores `it_admin_base.html` and `it_admin/dashboard.html` from git history.

## 10. Definition of done

- All 5 PRs merged to main on `personal` remote.
- Local main `manage.py migrate` clean (no migration churn from this sub-project — Wave A is pure UI/view code).
- Logging in as each of the 4 roles on `localhost:8000` lands on the redesigned dashboard with non-empty data.
- `pytest accounts/tests/test_*_dashboard.py` passes.
- `templates/it_admin_base.html` and `templates/it_admin/dashboard.html` deleted; no remaining references in code or templates (grep gate).
- This spec doc remains on main as the reference for Wave B kickoff.
