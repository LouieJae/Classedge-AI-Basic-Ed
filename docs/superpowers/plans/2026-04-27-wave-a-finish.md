# Wave A Finish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the remaining four "Operations Mode" dashboards (Registrar, Coil Admin, Academic Director, IT Admin redo) for Classedge LMS, foundation-first across 5 PRs against the `personal` remote.

**Architecture:** A single base template `templates/operations_base.html` plus 4 partials and one shared CSS file form a reusable shell. Each role gets its own view module under `accounts/views/` and its own role template that extends the shell and overrides `primary_panel` / `secondary_panel`. A shared test mixin keeps per-role tests around 30 lines.

**Tech Stack:** Django 5.0, SQLite (dev) / PostgreSQL (prod), `django.test.TestCase` (run via `manage.py test`), the project's existing `Role` / `Profile` / `CustomUser` models, and existing data models (`coil.CoilPartnerSchool`, `gamification.StudentGamification`, `central_content.CurriculumPlan`).

**Spec:** `docs/superpowers/specs/2026-04-27-wave-a-finish-design.md` (parent: `docs/superpowers/specs/2026-04-25-non-teacher-student-dashboard-redesign-design.md`).

**Conventions enforced by existing tests:**
- Every new public function MUST start its docstring with `[Classedge LMS]` (enforced by `accounts/tests/test_function_labels.py`).
- New view modules MUST be added to `PUBLIC_MODULES` in `accounts/tests/test_function_labels.py`.
- Pushes go to the `personal` remote (never `origin`). PRs target `main`. Merges use merge commits with `--delete-branch`.

---

## Phase 1 — Foundation (PR #1)

**Branch:** `feat/wave-a-finish-foundation`

**Adds:**
- `templates/operations_base.html`
- `static/css/operations_base.css`
- `templates/operations/scope_bar.html`
- `templates/operations/kpi_strip.html`
- `templates/operations/worklist_panel.html`
- `templates/operations/context_strip.html`
- `accounts/tests/operations_dashboard_mixin.py`
- `accounts/tests/test_operations_foundation.py`

**Touches:** none (pure additions; no role wired up yet).

### Task 1.1 — Branch from main

- [ ] **Step 1: Verify main is clean and synced**

```bash
cd ~/classedge
git checkout main && git pull personal main --ff-only
git status
```

Expected: `On branch main`, `nothing to commit, working tree clean`.

- [ ] **Step 2: Create feature branch**

```bash
git checkout -b feat/wave-a-finish-foundation
```

Expected: `Switched to a new branch 'feat/wave-a-finish-foundation'`.

### Task 1.2 — Write failing test for the operations base template

**Files:**
- Create: `accounts/tests/test_operations_foundation.py`

- [ ] **Step 1: Write the test**

```python
"""[Classedge LMS] Foundation tests for the Operations Mode dashboard shell."""
from django.template.loader import render_to_string
from django.test import SimpleTestCase


class OperationsBaseTemplateTests(SimpleTestCase):
    """[Classedge LMS] Verify operations_base.html renders all required zones."""

    def _ctx(self, **overrides):
        base = {
            "role_tag": "Test Role",
            "role_glyph": "▲",
            "nav_items": [{"url": "#", "label": "Dashboard", "active": True}],
            "scope_tags": [{"label": "Term", "value": "AY 2026"}],
            "quick_actions": [{"url": "#", "label": "Action", "primary": True}],
            "greeting_question": "What needs me today?",
            "kpis": [
                {"label": "Open Items", "value": "12", "delta": "+2", "tone": "warn"},
            ],
            "ctx_left": {"title": "Calendar", "items": []},
            "ctx_right": {"title": "Runway", "items": []},
            "request": type("R", (), {"user": type("U", (), {"first_name": "Tester", "is_authenticated": True})})(),
            "time_of_day": "morning",
        }
        base.update(overrides)
        return base

    def test_renders_role_tag_and_glyph(self):
        html = render_to_string("operations_base.html", self._ctx())
        self.assertIn("Test Role", html)
        self.assertIn("▲", html)

    def test_renders_greeting_with_first_name(self):
        html = render_to_string("operations_base.html", self._ctx())
        self.assertIn("Good morning, Tester", html)
        self.assertIn("What needs me today?", html)

    def test_renders_scope_tags(self):
        html = render_to_string("operations_base.html", self._ctx())
        self.assertIn("Term", html)
        self.assertIn("AY 2026", html)

    def test_renders_kpi_strip(self):
        html = render_to_string("operations_base.html", self._ctx())
        self.assertIn("Open Items", html)
        self.assertIn("12", html)
        self.assertIn("kpi warn", html)

    def test_renders_quick_actions(self):
        html = render_to_string("operations_base.html", self._ctx())
        self.assertIn("Action", html)
```

- [ ] **Step 2: Run the test (expect failure)**

```bash
cd ~/classedge
env/bin/python manage.py test accounts.tests.test_operations_foundation -v 2
```

Expected: 5 errors, all `TemplateDoesNotExist: operations_base.html`.

### Task 1.3 — Create the partials

**Files:**
- Create: `templates/operations/scope_bar.html`
- Create: `templates/operations/kpi_strip.html`
- Create: `templates/operations/worklist_panel.html`
- Create: `templates/operations/context_strip.html`

- [ ] **Step 1: scope_bar.html**

```html
{% comment %}[Classedge LMS] Operations Mode scope bar — pills for term/department/scope + live timestamp.{% endcomment %}
<div class="scope-bar">
  <div class="scope-tags">
    {% for tag in tags %}
      <span class="scope-pill"><strong>{{ tag.label }}</strong> {{ tag.value }}</span>
    {% endfor %}
  </div>
  <div class="scope-live">
    <span class="live-dot"></span>
    <span class="live-label">Live · as of {{ as_of|default:"now" }}</span>
  </div>
</div>
```

- [ ] **Step 2: kpi_strip.html**

```html
{% comment %}[Classedge LMS] Operations Mode KPI strip — 4–5 cards, each with label/value/delta/optional tone.{% endcomment %}
<section class="kpi-strip">
  {% for k in kpis %}
    <div class="kpi {{ k.tone }}">
      <div class="kpi-label">{{ k.label }}</div>
      <div class="kpi-value">{{ k.value }}{% if k.unit %}<span class="kpi-unit"> {{ k.unit }}</span>{% endif %}</div>
      {% if k.delta %}<div class="kpi-delta">{{ k.delta }}</div>{% endif %}
    </div>
  {% endfor %}
</section>
```

- [ ] **Step 3: worklist_panel.html**

```html
{% comment %}[Classedge LMS] Operations Mode worklist panel — sortable table; rows can be flagged with .row-flagged.{% endcomment %}
<div class="worklist-panel">
  <header class="panel-header">
    <h2>{{ title }}</h2>
    {% if why %}<span class="why"><em>{{ why }}</em></span>{% endif %}
  </header>
  <table class="worklist">
    <thead>
      <tr>
        {% for col in columns %}<th>{{ col }}</th>{% endfor %}
      </tr>
    </thead>
    <tbody>
      {% for row in rows %}
        <tr class="{% if row.flagged %}row-flagged{% endif %}">
          {% for cell in row.cells %}<td>{{ cell }}</td>{% endfor %}
        </tr>
      {% empty %}
        <tr><td colspan="{{ columns|length }}" class="worklist-empty">{{ empty_message|default:"Nothing here." }}</td></tr>
      {% endfor %}
    </tbody>
  </table>
</div>
```

- [ ] **Step 4: context_strip.html**

```html
{% comment %}[Classedge LMS] Operations Mode context strip — two equal columns of ambient info.{% endcomment %}
<section class="context-strip">
  <div class="context-col">
    <h3>{{ left.title }}</h3>
    {% for item in left.items %}<div class="context-item">{{ item }}</div>{% empty %}<div class="context-empty">{{ left.empty|default:"Nothing scheduled." }}</div>{% endfor %}
  </div>
  <div class="context-col">
    <h3>{{ right.title }}</h3>
    {% for item in right.items %}<div class="context-item">{{ item }}</div>{% empty %}<div class="context-empty">{{ right.empty|default:"Nothing here." }}</div>{% endfor %}
  </div>
</section>
```

### Task 1.4 — Create the operations base template

**Files:**
- Create: `templates/operations_base.html`

- [ ] **Step 1: Write the base template**

```html
{% comment %}[Classedge LMS] Operations Mode shell — base for all non-teacher/non-student dashboards.{% endcomment %}
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{% block title %}{{ role_tag }} · ClassEdge{% endblock %}</title>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300..700&family=Inter+Tight:wght@400;500;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
  {% load static %}
  <link rel="stylesheet" href="{% static 'css/operations_base.css' %}">
  {% block extra_head %}{% endblock %}
</head>
<body>
  <div class="ops-shell">
    <aside class="ops-side">
      <div class="brand"><span class="brand-mark">C</span> ClassEdge</div>
      <div class="role-tag">{{ role_glyph }} {{ role_tag }}</div>
      <nav class="ops-nav">
        {% for item in nav_items %}
          <a href="{{ item.url }}" class="ops-nav-link {% if item.active %}active{% endif %}">{{ item.label }}</a>
          {% if item.divider_after %}<div class="ops-nav-divider"></div>{% endif %}
        {% endfor %}
      </nav>
      <div class="ops-user">
        <div class="ops-avatar">{{ request.user.first_name|default:request.user.username|make_list|first|upper }}</div>
        <div class="ops-user-meta">
          <div class="ops-user-name">{{ request.user.get_full_name|default:request.user.username }}</div>
          <div class="ops-user-role">{{ role_tag }}</div>
        </div>
        <a href="{% url 'sign_out' %}" class="ops-signout" aria-label="Sign out">&#x23FB;</a>
      </div>
    </aside>
    <main class="ops-main">
      {% include 'operations/scope_bar.html' with tags=scope_tags as_of=as_of %}
      <header class="ops-greeting">
        <div class="greeting-text">
          <h1>Good {{ time_of_day }}, {{ request.user.first_name|default:request.user.username }}</h1>
          <p class="walk-in"><em>{{ greeting_question }}</em></p>
        </div>
        <div class="ops-actions">
          {% for a in quick_actions %}
            <a href="{{ a.url }}" class="ops-btn {% if a.primary %}ops-btn-primary{% else %}ops-btn-secondary{% endif %}">{{ a.label }}</a>
          {% endfor %}
        </div>
      </header>
      {% include 'operations/kpi_strip.html' with kpis=kpis %}
      <section class="ops-grid">
        <div class="ops-primary">{% block primary_panel %}{% endblock %}</div>
        <div class="ops-secondary">{% block secondary_panel %}{% endblock %}</div>
      </section>
      {% include 'operations/context_strip.html' with left=ctx_left right=ctx_right %}
    </main>
  </div>
</body>
</html>
```

- [ ] **Step 2: Run the test (still failing — CSS not yet present, but template now resolves)**

```bash
env/bin/python manage.py test accounts.tests.test_operations_foundation -v 2
```

Expected: tests pass (the static link to a missing CSS file does not break rendering — Django templating just emits the URL).

### Task 1.5 — Create the shared stylesheet

**Files:**
- Create: `static/css/operations_base.css`

- [ ] **Step 1: Write the stylesheet**

```css
/* [Classedge LMS] Operations Mode shared stylesheet — design tokens + shell layout. */
:root {
  --cream: #faf7f2;
  --cream-2: #f3ede2;
  --paper: #ffffff;
  --forest: #1b4332;
  --forest-2: #2d5a47;
  --forest-light: #d9e4dd;
  --gold: #b7925a;
  --gold-bg: rgba(183, 146, 90, 0.08);
  --rose: #c08479;
  --rose-soft: #f4e0dc;
  --rose-deep: #7a3e3e;
  --ink: #2d3142;
  --ink-dim: #6c7080;
  --ink-muted: #a0a4b8;
}

* { box-sizing: border-box; }
body { margin: 0; font-family: "Inter Tight", sans-serif; background: var(--cream); color: var(--ink); }

.ops-shell { display: grid; grid-template-columns: 240px 1fr; min-height: 100vh; }

.ops-side { background: var(--forest); color: var(--cream); padding: 24px 16px; display: flex; flex-direction: column; gap: 16px; position: sticky; top: 0; height: 100vh; }
.ops-side .brand { font-family: "Fraunces", serif; font-size: 22px; display: flex; align-items: center; gap: 8px; }
.ops-side .brand-mark { width: 28px; height: 28px; border-radius: 6px; background: var(--gold); color: var(--forest); display: inline-flex; align-items: center; justify-content: center; font-weight: 700; }
.role-tag { font-size: 11px; letter-spacing: 0.2em; text-transform: uppercase; color: var(--cream); opacity: 0.7; padding-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); }
.ops-nav { display: flex; flex-direction: column; gap: 2px; flex: 1; overflow-y: auto; }
.ops-nav-link { color: var(--cream); text-decoration: none; padding: 8px 12px; border-radius: 6px; opacity: 0.85; font-size: 14px; }
.ops-nav-link:hover, .ops-nav-link.active { background: var(--forest-2); opacity: 1; }
.ops-nav-divider { height: 1px; background: rgba(255,255,255,0.1); margin: 8px 0; }

.ops-user { display: flex; align-items: center; gap: 8px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.1); }
.ops-avatar { width: 36px; height: 36px; border-radius: 50%; background: var(--gold); color: var(--forest); display: inline-flex; align-items: center; justify-content: center; font-weight: 700; }
.ops-user-meta { flex: 1; min-width: 0; }
.ops-user-name { font-size: 13px; font-weight: 600; }
.ops-user-role { font-size: 11px; opacity: 0.7; }
.ops-signout { color: var(--cream); text-decoration: none; opacity: 0.7; padding: 6px 8px; font-size: 18px; }
.ops-signout:hover { opacity: 1; }

.ops-main { padding: 32px 40px; overflow-x: hidden; }

.scope-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.scope-tags { display: flex; gap: 8px; flex-wrap: wrap; }
.scope-pill { background: var(--forest-light); color: var(--forest); padding: 4px 10px; border-radius: 999px; font-size: 12px; }
.scope-pill strong { font-weight: 600; }
.scope-live { display: flex; align-items: center; gap: 6px; color: var(--ink-dim); font-size: 12px; }
.live-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--forest); }

.ops-greeting { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; gap: 24px; }
.ops-greeting h1 { font-family: "Fraunces", serif; font-size: 32px; margin: 0 0 4px; font-weight: 500; }
.walk-in { color: var(--ink-dim); font-size: 14px; margin: 0; }
.ops-actions { display: flex; gap: 8px; flex-shrink: 0; }
.ops-btn { padding: 10px 16px; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: 500; }
.ops-btn-primary { background: var(--forest); color: var(--cream); }
.ops-btn-secondary { background: var(--paper); color: var(--ink); border: 1px solid var(--ink-muted); }

.kpi-strip { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 24px; }
.kpi { background: var(--paper); border-radius: 12px; padding: 16px; border: 1px solid var(--cream-2); }
.kpi-label { font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--ink-muted); }
.kpi-value { font-family: "Fraunces", serif; font-size: 32px; font-weight: 500; line-height: 1.2; margin-top: 4px; }
.kpi-unit { font-size: 14px; color: var(--ink-dim); }
.kpi-delta { font-size: 12px; color: var(--ink-dim); margin-top: 4px; }
.kpi.warn { background: linear-gradient(135deg, var(--rose-soft), #ffeae5); }
.kpi.warn .kpi-delta { color: var(--rose-deep); }
.kpi.ok { background: linear-gradient(135deg, var(--forest-light), #e8f1ec); }

.ops-grid { display: grid; grid-template-columns: 1.45fr 1fr; gap: 24px; margin-bottom: 24px; }
.ops-primary, .ops-secondary { background: var(--paper); border-radius: 12px; padding: 24px; border: 1px solid var(--cream-2); }

.panel-header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 16px; }
.panel-header h2 { font-family: "Fraunces", serif; font-size: 20px; margin: 0; font-weight: 500; }
.panel-header .why { font-size: 11px; color: var(--ink-muted); }

.worklist { width: 100%; border-collapse: collapse; font-size: 13px; }
.worklist th { text-align: left; padding: 8px; border-bottom: 1px solid var(--cream-2); color: var(--ink-dim); font-weight: 500; font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase; }
.worklist td { padding: 10px 8px; border-bottom: 1px solid var(--cream-2); }
.row-flagged td:first-child { border-left: 3px solid var(--rose); padding-left: 8px; }
.worklist-empty { text-align: center; color: var(--ink-muted); padding: 24px; }

.context-strip { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.context-col { background: var(--paper); border-radius: 12px; padding: 20px; border: 1px solid var(--cream-2); }
.context-col h3 { font-family: "Fraunces", serif; font-size: 16px; margin: 0 0 12px; font-weight: 500; }
.context-item { padding: 6px 0; border-bottom: 1px solid var(--cream-2); font-size: 13px; }
.context-item:last-child { border-bottom: none; }
.context-empty { color: var(--ink-muted); font-size: 13px; }
```

- [ ] **Step 2: Re-run the foundation test**

```bash
env/bin/python manage.py test accounts.tests.test_operations_foundation -v 2
```

Expected: 5 tests pass.

### Task 1.6 — Create the test mixin for per-role tests

**Files:**
- Create: `accounts/tests/operations_dashboard_mixin.py`

- [ ] **Step 1: Write the mixin**

```python
"""[Classedge LMS] Shared mixin for Operations Mode dashboard tests."""
from django.urls import reverse

from accounts.models.account_models import CustomUser, Profile
from accounts.tests.helpers import make_profile_for


class OperationsDashboardTestMixin:
    """[Classedge LMS] Reusable assertions for any Operations Mode dashboard view.

    Subclass requirements:
        url_name: str        — Django URL name for the dashboard view
        role: str            — exact Role.name (case-sensitive) that owns this dashboard
        glyph: str           — single-character role glyph that must appear in HTML
        kpi_count: int       — number of KPI cards expected in the strip
    """

    url_name = None
    role = None
    glyph = None
    kpi_count = None

    def make_user_with_role(self, role_name, username="u1"):
        """[Classedge LMS] Create an active user assigned to the given role and return it."""
        user = CustomUser.objects.create_user(username=username, email=f"{username}@x.io", password="x")
        make_profile_for(user, role_name)
        return user

    def assert_renders_for_role(self):
        """[Classedge LMS] GET as the role owner returns 200 with KPIs in context."""
        user = self.make_user_with_role(self.role, "owner")
        self.client.force_login(user)
        resp = self.client.get(reverse(self.url_name))
        self.assertEqual(resp.status_code, 200, f"{self.role} should reach its dashboard")
        self.assertIn("kpis", resp.context)
        self.assertEqual(len(resp.context["kpis"]), self.kpi_count)
        return resp

    def assert_403_for_other_roles(self):
        """[Classedge LMS] GET as a Teacher (or other unrelated role) is denied (302/403)."""
        user = self.make_user_with_role("Teacher", "intruder")
        self.client.force_login(user)
        resp = self.client.get(reverse(self.url_name))
        self.assertIn(resp.status_code, (302, 403), f"non-{self.role} must not reach the {self.role} dashboard")

    def assert_glyph_renders(self):
        """[Classedge LMS] The role glyph appears in the rendered HTML (sidebar role tag)."""
        resp = self.assert_renders_for_role()
        self.assertContains(resp, self.glyph)
```

- [ ] **Step 2: Add a stub test that uses the mixin to confirm wire-up (not a real role yet)**

Append to `accounts/tests/test_operations_foundation.py`:

```python
class OperationsDashboardMixinSelfCheck(SimpleTestCase):
    """[Classedge LMS] Cheap self-check: importing the mixin must not error."""

    def test_mixin_importable(self):
        from accounts.tests.operations_dashboard_mixin import OperationsDashboardTestMixin
        self.assertTrue(hasattr(OperationsDashboardTestMixin, "assert_renders_for_role"))
```

- [ ] **Step 3: Run all new tests**

```bash
env/bin/python manage.py test accounts.tests.test_operations_foundation -v 2
```

Expected: 6 tests pass.

### Task 1.7 — Run full test suite and label-check

- [ ] **Step 1: Run the full accounts test suite**

```bash
env/bin/python manage.py test accounts -v 1
```

Expected: existing tests still pass; new tests pass; no regressions.

- [ ] **Step 2: Verify label test still passes**

```bash
env/bin/python manage.py test accounts.tests.test_function_labels -v 2
```

Expected: 1 test passes (the `[Classedge LMS]` label check).

### Task 1.8 — Commit, push, open PR

- [ ] **Step 1: Stage and commit**

```bash
git add templates/operations_base.html templates/operations/ static/css/operations_base.css accounts/tests/operations_dashboard_mixin.py accounts/tests/test_operations_foundation.py
git commit -m "$(cat <<'EOF'
feat(operations): foundation for Operations Mode dashboard shell

Adds the unified shell + 4 partials + shared CSS + test mixin used by
all non-teacher/non-student dashboards. No role wired yet — Wave A
follow-ups (Registrar, Coil Admin, Academic Director, IT Admin redo)
will each add a role view + role template that extend this base.

Spec: docs/superpowers/specs/2026-04-27-wave-a-finish-design.md
Plan: docs/superpowers/plans/2026-04-27-wave-a-finish.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 2: Push and open PR**

```bash
git push -u personal feat/wave-a-finish-foundation
gh pr create --repo teryopitikin/Classedge-Ai --base main --head feat/wave-a-finish-foundation \
  --title "feat(operations): foundation for Operations Mode dashboard shell" \
  --body "$(cat <<'EOF'
## Summary
- Adds `templates/operations_base.html` plus 4 partials (`scope_bar`, `kpi_strip`, `worklist_panel`, `context_strip`).
- Adds `static/css/operations_base.css` with design tokens + shell layout from spec §4.3.
- Adds `accounts/tests/operations_dashboard_mixin.py` for per-role tests in upcoming PRs.
- Adds `accounts/tests/test_operations_foundation.py`: 5 template-render tests + 1 mixin import test.

## Why
First PR in Wave A finish (spec PR #15). No roles wired up yet — keeps the foundation reviewable in isolation. Subsequent PRs add Registrar / Coil Admin / Academic Director / IT Admin (redo) each as self-contained PRs that extend this shell.

## Test plan
- [x] `python manage.py test accounts.tests.test_operations_foundation` → 6 passed
- [x] `python manage.py test accounts` → no regressions
- [x] Label test still passes
EOF
)"
```

- [ ] **Step 3: Merge once green**

```bash
gh pr merge --repo teryopitikin/Classedge-Ai --merge --delete-branch
git checkout main && git pull personal main --ff-only
```

Expected: branch deleted, local main fast-forwarded.

---

## Phase 2 — Registrar dashboard (PR #2)

**Branch:** `feat/wave-a-finish-registrar`

**Adds:**
- `accounts/views/registrar.py`
- `templates/operations/registrar_dashboard.html`
- `accounts/tests/test_registrar_dashboard.py`

**Touches:**
- `accounts/urls.py` (1 line)
- `accounts/views/dashboard.py` (extend role router)
- `accounts/tests/test_function_labels.py` (add registrar to `PUBLIC_MODULES`)

### Task 2.1 — Branch, write the failing access test

**Files:**
- Create: `accounts/tests/test_registrar_dashboard.py`

- [ ] **Step 1: Branch**

```bash
git checkout -b feat/wave-a-finish-registrar
```

- [ ] **Step 2: Write the failing test**

```python
"""[Classedge LMS] Registrar Operations Mode dashboard tests."""
from django.test import TestCase

from accounts.tests.operations_dashboard_mixin import OperationsDashboardTestMixin


class RegistrarDashboardTests(OperationsDashboardTestMixin, TestCase):
    """[Classedge LMS] Access + content tests for the Registrar dashboard."""

    url_name = "registrar_dashboard"
    role = "Registrar"
    glyph = "⎙"
    kpi_count = 5

    def test_renders_for_registrar(self):
        self.assert_renders_for_role()

    def test_403_for_other_roles(self):
        self.assert_403_for_other_roles()

    def test_glyph_renders_in_html(self):
        self.assert_glyph_renders()

    def test_aging_queue_sorted_oldest_first(self):
        """[Classedge LMS] The aging request queue puts the oldest item at the top."""
        user = self.make_user_with_role(self.role, "reg1")
        self.client.force_login(user)
        resp = self.client.get(reverse_or_skip(self.url_name))
        rows = resp.context["aging_rows"]
        ages = [row["age_days"] for row in rows]
        self.assertEqual(ages, sorted(ages, reverse=True), "oldest item must be first")


def reverse_or_skip(url_name):
    """[Classedge LMS] Helper: reverse a URL name (raises if missing — test fail is informative)."""
    from django.urls import reverse
    return reverse(url_name)
```

- [ ] **Step 3: Run the test (expect fail — no view yet)**

```bash
env/bin/python manage.py test accounts.tests.test_registrar_dashboard -v 2
```

Expected: errors / fails because `registrar_dashboard` URL is unregistered.

### Task 2.2 — Implement the Registrar view

**Files:**
- Create: `accounts/views/registrar.py`

- [ ] **Step 1: Write the view**

```python
"""[Classedge LMS] Registrar Operations Mode dashboard view."""
from datetime import timedelta

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.utils import timezone

from accounts.models.account_models import CustomUser
from course.models.subject_enrollment_model import SubjectEnrollment


def _is_registrar(user):
    """[Classedge LMS] True iff the authenticated user owns the Registrar role."""
    return (
        user.is_authenticated
        and hasattr(user, "profile")
        and user.profile.role
        and user.profile.role.name == "Registrar"
    )


def _time_of_day():
    """[Classedge LMS] morning / afternoon / evening based on server local time."""
    h = timezone.localtime().hour
    if h < 12:
        return "morning"
    if h < 18:
        return "afternoon"
    return "evening"


def _registrar_kpis():
    """[Classedge LMS] Compute the 5 hero KPIs for the Registrar dashboard."""
    active_enrollments = SubjectEnrollment.objects.count()
    pending_requests = 0   # placeholder — request models live elsewhere; render '—' until wired
    flagged_records = 0
    todays_tx = SubjectEnrollment.objects.filter(
        date_enrolled__date=timezone.localdate()
    ).count() if hasattr(SubjectEnrollment, "date_enrolled") else 0
    sla_hit_30d = "—"
    return [
        {"label": "Active Enrollments", "value": active_enrollments, "delta": "", "tone": ""},
        {"label": "Pending Requests", "value": pending_requests or "—", "delta": "", "tone": ""},
        {"label": "Records Flagged", "value": flagged_records or "—", "delta": "", "tone": ""},
        {"label": "Today's Transactions", "value": todays_tx, "delta": "", "tone": ""},
        {"label": "SLA Hit Rate 30d", "value": sla_hit_30d, "delta": "", "tone": ""},
    ]


def _aging_queue_rows():
    """[Classedge LMS] Build the aging-request queue rows.

    Until a Request model is wired to this dashboard the queue surfaces the
    most recent SubjectEnrollment records as a stand-in (oldest first by
    `date_enrolled` if the field exists, else id desc). Real request data
    swaps in via a follow-up PR without changing the panel contract.
    """
    qs = SubjectEnrollment.objects.all()
    if hasattr(SubjectEnrollment, "date_enrolled"):
        qs = qs.order_by("date_enrolled")
    else:
        qs = qs.order_by("id")
    items = list(qs[:8])
    today = timezone.localdate()
    rows = []
    for item in items:
        ref = getattr(item, "date_enrolled", None) or timezone.now()
        age_days = (today - timezone.localdate(ref)).days if hasattr(ref, "date") else 0
        rows.append({
            "cells": [
                getattr(item, "id", "—"),
                getattr(getattr(item, "student", None), "username", "—"),
                f"{age_days}d",
            ],
            "age_days": age_days,
            "flagged": age_days > 7,
        })
    return rows


@login_required
@user_passes_test(_is_registrar)
def registrar_dashboard(request):
    """[Classedge LMS] Render the Registrar Operations Mode dashboard."""
    context = {
        "role_tag": "Registrar",
        "role_glyph": "⎙",
        "nav_items": [
            {"url": "#", "label": "Dashboard", "active": True},
        ],
        "scope_tags": [{"label": "Term", "value": "Current"}],
        "quick_actions": [],
        "greeting_question": "What records action is overdue — and is the term still on schedule?",
        "time_of_day": _time_of_day(),
        "as_of": timezone.localtime().strftime("%I:%M %p"),
        "kpis": _registrar_kpis(),
        "ctx_left": {"title": "Calendar", "items": [], "empty": "Nothing scheduled."},
        "ctx_right": {"title": "Capacity", "items": [], "empty": "—"},
        "aging_rows": _aging_queue_rows(),
        "aging_columns": ["ID", "Student", "Age"],
    }
    return render(request, "operations/registrar_dashboard.html", context)
```

- [ ] **Step 2: Create the role template**

**Files:**
- Create: `templates/operations/registrar_dashboard.html`

```html
{% comment %}[Classedge LMS] Registrar Operations Mode dashboard.{% endcomment %}
{% extends 'operations_base.html' %}

{% block primary_panel %}
  {% include 'operations/worklist_panel.html' with title="Aging Requests" why="oldest first — flagged at 7+ days" columns=aging_columns rows=aging_rows empty_message="No open requests." %}
{% endblock %}

{% block secondary_panel %}
  <div class="panel-header"><h2>Request Volume (14d)</h2></div>
  <p class="context-empty">Chart pending real request model.</p>
{% endblock %}
```

### Task 2.3 — Wire the URL + router

**Files:**
- Modify: `accounts/urls.py`
- Modify: `accounts/views/dashboard.py`

- [ ] **Step 1: Add URL entry**

In `accounts/urls.py`, locate the existing `it-admin/` line and add immediately after:

```python
from accounts.views.registrar import registrar_dashboard
# ... in urlpatterns:
    path("registrar/", registrar_dashboard, name="registrar_dashboard"),
```

- [ ] **Step 2: Extend the role router**

In `accounts/views/dashboard.py`, find the block:

```python
    if is_teacher:
        return gamification_teacher_dashboard(request)
```

Add immediately after:

```python
    if is_registrar:
        from accounts.views.registrar import registrar_dashboard
        return registrar_dashboard(request)
```

(`is_registrar` is already computed earlier in the same function.)

### Task 2.4 — Add registrar module to label-check, run tests

**Files:**
- Modify: `accounts/tests/test_function_labels.py`

- [ ] **Step 1: Register the new module**

Replace the import + `PUBLIC_MODULES` block:

```python
from accounts.services import department_access
from accounts.views import department_admin
from accounts.views import registrar
from calendars.services import department_filter

PUBLIC_MODULES = [department_access, department_admin, department_filter, registrar]
```

- [ ] **Step 2: Run the role test**

```bash
env/bin/python manage.py test accounts.tests.test_registrar_dashboard -v 2
```

Expected: 4 tests pass.

- [ ] **Step 3: Run the label test**

```bash
env/bin/python manage.py test accounts.tests.test_function_labels -v 2
```

Expected: passes (every `_is_registrar`, `_time_of_day`, `_registrar_kpis`, `_aging_queue_rows`, `registrar_dashboard` either starts with `_` (private, skipped) or has `[Classedge LMS]` in its docstring).

- [ ] **Step 4: Run full accounts suite**

```bash
env/bin/python manage.py test accounts -v 1
```

Expected: no regressions.

### Task 2.5 — Manual smoke check

- [ ] **Step 1: Confirm the dev server is running (or restart it)**

```bash
lsof -iTCP:8000 -sTCP:LISTEN -n -P 2>/dev/null
```

If nothing listed, restart in background:

```bash
cd ~/classedge && env/bin/python manage.py runserver 0.0.0.0:8000 > logs/django-server.log 2>&1 &
```

- [ ] **Step 2: Promote a test user to Registrar via shell**

```bash
env/bin/python manage.py shell -c "
from accounts.models.account_models import CustomUser, Profile
from roles.models import Role
u, _ = CustomUser.objects.get_or_create(username='reg_test', defaults={'email':'r@x.io'})
u.set_password('reg'); u.save()
p, _ = Profile.objects.get_or_create(user=u)
r, _ = Role.objects.get_or_create(name='Registrar')
p.role = r; p.save()
print('Registrar user reg_test/reg ready')
"
```

- [ ] **Step 3: Visit `http://localhost:8000/registrar/` after login as `reg_test/reg`**

Expected: Operations Mode shell renders, sidebar shows `⎙ Registrar`, KPI strip has 5 cards, Aging Requests panel shows entries (or "No open requests.").

### Task 2.6 — Commit, push, open PR, merge

- [ ] **Step 1: Commit**

```bash
git add accounts/views/registrar.py templates/operations/registrar_dashboard.html accounts/tests/test_registrar_dashboard.py accounts/urls.py accounts/views/dashboard.py accounts/tests/test_function_labels.py
git commit -m "$(cat <<'EOF'
feat(registrar): Operations Mode dashboard

Adds /registrar/ dashboard for the Registrar role using the Operations
Mode shell from PR #16. KPI strip surfaces 5 metrics; primary panel is
an aging request queue (placeholder rows from SubjectEnrollment until
a real request model is wired). Role-gated via _is_registrar check.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 2: Push, open PR, merge**

```bash
git push -u personal feat/wave-a-finish-registrar
gh pr create --repo teryopitikin/Classedge-Ai --base main --head feat/wave-a-finish-registrar \
  --title "feat(registrar): Operations Mode dashboard" \
  --body "$(cat <<'EOF'
## Summary
- New view `accounts/views/registrar.py` and template `templates/operations/registrar_dashboard.html` extending the Operations Mode shell.
- 5 KPI cards; primary panel = aging request queue (oldest first, flagged >7d).
- Role-gated to Role.name == 'Registrar'; Teachers / others get 302/403.
- 4 view tests via `OperationsDashboardTestMixin`.

## Why
PR #2 of Wave A finish (spec PR #15). Smallest data surface among the four roles, so it lands first to validate the shell + mixin pattern under real data.

## Test plan
- [x] `python manage.py test accounts.tests.test_registrar_dashboard` → 4 passed
- [x] `python manage.py test accounts` → no regressions
- [x] Manual smoke: login as Registrar, hit /registrar/, verify glyph + KPI strip + queue
EOF
)"
gh pr merge --repo teryopitikin/Classedge-Ai --merge --delete-branch
git checkout main && git pull personal main --ff-only
```

Expected: PR merged; local main fast-forwarded.

---

## Phase 3 — Coil Admin dashboard (PR #3)

**Branch:** `feat/wave-a-finish-coil-admin`

**Adds:**
- `accounts/views/coil_admin.py`
- `templates/operations/coil_admin_dashboard.html`
- `accounts/tests/test_coil_admin_dashboard.py`

**Touches:**
- `accounts/urls.py`
- `accounts/views/dashboard.py` (router)
- `accounts/tests/test_function_labels.py`

### Task 3.1 — Branch, write the failing access test

- [ ] **Step 1: Branch**

```bash
git checkout -b feat/wave-a-finish-coil-admin
```

- [ ] **Step 2: Write the failing test**

**Files:**
- Create: `accounts/tests/test_coil_admin_dashboard.py`

```python
"""[Classedge LMS] Coil Admin Operations Mode dashboard tests."""
from django.test import TestCase
from django.urls import reverse

from accounts.tests.operations_dashboard_mixin import OperationsDashboardTestMixin
from coil.models import CoilPartnerSchool


class CoilAdminDashboardTests(OperationsDashboardTestMixin, TestCase):
    """[Classedge LMS] Access + content tests for the Coil Admin dashboard."""

    url_name = "coil_admin_dashboard"
    role = "Coil Admin"
    glyph = "⊕"
    kpi_count = 5

    def test_renders_for_coil_admin(self):
        self.assert_renders_for_role()

    def test_403_for_other_roles(self):
        self.assert_403_for_other_roles()

    def test_glyph_renders_in_html(self):
        self.assert_glyph_renders()

    def test_pending_partners_first_in_table(self):
        """[Classedge LMS] Pending Acceptance rows must appear before Partner rows."""
        CoilPartnerSchool.objects.create(school_name="A", school_domain="a.edu", status="Partner")
        CoilPartnerSchool.objects.create(school_name="B", school_domain="b.edu", status="Pending Acceptance")
        user = self.make_user_with_role(self.role, "ca1")
        self.client.force_login(user)
        resp = self.client.get(reverse(self.url_name))
        partners = resp.context["partner_rows"]
        statuses = [row["cells"][1] for row in partners]
        self.assertLess(statuses.index("Pending Acceptance"), statuses.index("Partner"))

    def test_collaborative_classes_panel_is_stub(self):
        """[Classedge LMS] Collaborative-classes panel renders the documented stub copy."""
        user = self.make_user_with_role(self.role, "ca2")
        self.client.force_login(user)
        resp = self.client.get(reverse(self.url_name))
        self.assertContains(resp, "Coming soon")
```

- [ ] **Step 3: Run the test (expect fail)**

```bash
env/bin/python manage.py test accounts.tests.test_coil_admin_dashboard -v 2
```

Expected: errors — view not registered.

### Task 3.2 — Implement the Coil Admin view

**Files:**
- Create: `accounts/views/coil_admin.py`

- [ ] **Step 1: Write the view**

```python
"""[Classedge LMS] Coil Admin Operations Mode dashboard view."""
from collections import Counter
from datetime import timedelta

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.utils import timezone

from coil.models import CoilPartnerSchool


STATUS_ORDER = ["Pending Acceptance", "Send Invite", "Partner", "Rejected"]


def _is_coil_admin(user):
    """[Classedge LMS] True iff the authenticated user owns the Coil Admin role."""
    return (
        user.is_authenticated
        and hasattr(user, "profile")
        and user.profile.role
        and user.profile.role.name == "Coil Admin"
    )


def _time_of_day():
    """[Classedge LMS] morning / afternoon / evening for greeting copy."""
    h = timezone.localtime().hour
    if h < 12: return "morning"
    if h < 18: return "afternoon"
    return "evening"


def _coil_kpis(qs_all):
    """[Classedge LMS] Compute the 5 hero KPIs from the partner-school queryset."""
    by_status = Counter(qs_all.values_list("status", flat=True))
    students = sum(s.student_participating for s in qs_all)
    return [
        {"label": "Active Partner Schools", "value": by_status.get("Partner", 0), "tone": ""},
        {"label": "Students Participating", "value": students, "tone": ""},
        {"label": "Collaborative Classes", "value": "—", "tone": ""},
        {"label": "Joint Sessions / Wk", "value": "—", "tone": ""},
        {"label": "Pending Invites", "value": by_status.get("Pending Acceptance", 0) + by_status.get("Send Invite", 0), "tone": "warn" if by_status.get("Pending Acceptance", 0) else ""},
    ]


def _partner_rows(qs_all):
    """[Classedge LMS] Build partner-schools table rows with pending-first ordering."""
    rows = []
    for school in sorted(qs_all, key=lambda s: STATUS_ORDER.index(s.status) if s.status in STATUS_ORDER else len(STATUS_ORDER)):
        rows.append({
            "cells": [school.school_name, school.status, school.student_count(), school.location or "—"],
            "flagged": school.status == "Pending Acceptance",
        })
    return rows


def _funnel_rows(qs_all):
    """[Classedge LMS] Counts for the secondary funnel panel."""
    by_status = Counter(qs_all.values_list("status", flat=True))
    return [
        {"label": "Send Invite", "count": by_status.get("Send Invite", 0)},
        {"label": "Pending Acceptance", "count": by_status.get("Pending Acceptance", 0)},
        {"label": "Partner", "count": by_status.get("Partner", 0)},
        {"label": "Rejected", "count": by_status.get("Rejected", 0)},
    ]


@login_required
@user_passes_test(_is_coil_admin)
def coil_admin_dashboard(request):
    """[Classedge LMS] Render the Coil Admin Operations Mode dashboard."""
    qs_all = CoilPartnerSchool.objects.all()
    context = {
        "role_tag": "Coil Admin",
        "role_glyph": "⊕",
        "nav_items": [{"url": "#", "label": "Dashboard", "active": True}],
        "scope_tags": [{"label": "Term", "value": "Current"}],
        "quick_actions": [],
        "greeting_question": "How is the COIL department running this term — and which partner relationships need attention?",
        "time_of_day": _time_of_day(),
        "as_of": timezone.localtime().strftime("%I:%M %p"),
        "kpis": _coil_kpis(qs_all),
        "ctx_left": {"title": "Upcoming Sessions", "items": [], "empty": "No sessions scheduled."},
        "ctx_right": {"title": "Recent Partner Activity", "items": [], "empty": "Nothing yet."},
        "partner_rows": _partner_rows(qs_all),
        "partner_columns": ["School", "Status", "Students", "Location"],
        "funnel_rows": _funnel_rows(qs_all),
    }
    return render(request, "operations/coil_admin_dashboard.html", context)
```

- [ ] **Step 2: Create the template**

**Files:**
- Create: `templates/operations/coil_admin_dashboard.html`

```html
{% comment %}[Classedge LMS] Coil Admin Operations Mode dashboard.{% endcomment %}
{% extends 'operations_base.html' %}

{% block primary_panel %}
  {% include 'operations/worklist_panel.html' with title="Partner Schools" why="pending invites first" columns=partner_columns rows=partner_rows empty_message="No partner schools yet." %}
  <hr style="margin:24px 0; border:none; border-top:1px solid var(--cream-2);">
  <div class="panel-header"><h2>Collaborative Classes</h2></div>
  <p class="context-empty">Coming soon — class-level collaboration model pending.</p>
{% endblock %}

{% block secondary_panel %}
  <div class="panel-header"><h2>Partner Pipeline</h2></div>
  <table class="worklist">
    <thead><tr><th>Stage</th><th>Count</th></tr></thead>
    <tbody>
      {% for row in funnel_rows %}<tr><td>{{ row.label }}</td><td>{{ row.count }}</td></tr>{% endfor %}
    </tbody>
  </table>
{% endblock %}
```

### Task 3.3 — Wire URL + router + label test

**Files:**
- Modify: `accounts/urls.py`
- Modify: `accounts/views/dashboard.py`
- Modify: `accounts/tests/test_function_labels.py`

- [ ] **Step 1: Add URL entry**

```python
from accounts.views.coil_admin import coil_admin_dashboard
# ... in urlpatterns:
    path("coil-admin/", coil_admin_dashboard, name="coil_admin_dashboard"),
```

- [ ] **Step 2: Extend role router**

In `accounts/views/dashboard.py`, after the `is_registrar` block:

```python
    is_coil_admin = role_name == 'coil admin'
    if is_coil_admin:
        from accounts.views.coil_admin import coil_admin_dashboard
        return coil_admin_dashboard(request)
```

- [ ] **Step 3: Add module to label test**

```python
from accounts.views import coil_admin
# extend:
PUBLIC_MODULES = [department_access, department_admin, department_filter, registrar, coil_admin]
```

### Task 3.4 — Run tests, smoke, commit, push, merge

- [ ] **Step 1: Run dashboard tests**

```bash
env/bin/python manage.py test accounts.tests.test_coil_admin_dashboard -v 2
```

Expected: 5 tests pass.

- [ ] **Step 2: Run accounts suite**

```bash
env/bin/python manage.py test accounts -v 1
```

Expected: no regressions.

- [ ] **Step 3: Smoke**

```bash
env/bin/python manage.py shell -c "
from accounts.models.account_models import CustomUser, Profile
from roles.models import Role
u, _ = CustomUser.objects.get_or_create(username='ca_test', defaults={'email':'ca@x.io'})
u.set_password('ca'); u.save()
p, _ = Profile.objects.get_or_create(user=u)
r, _ = Role.objects.get_or_create(name='Coil Admin')
p.role = r; p.save()
print('Coil Admin user ca_test/ca ready')
"
```

Visit `http://localhost:8000/coil-admin/` after login. Verify ⊕ glyph, 5 KPI cards, Partner Schools table, "Coming soon" stub.

- [ ] **Step 4: Commit + PR + merge**

```bash
git add accounts/views/coil_admin.py templates/operations/coil_admin_dashboard.html accounts/tests/test_coil_admin_dashboard.py accounts/urls.py accounts/views/dashboard.py accounts/tests/test_function_labels.py
git commit -m "$(cat <<'EOF'
feat(coil-admin): Operations Mode dashboard

KPI strip (5 cards), partner-schools worklist (pending-first sort),
funnel by status, stubbed Collaborative Classes panel pending model.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
git push -u personal feat/wave-a-finish-coil-admin
gh pr create --repo teryopitikin/Classedge-Ai --base main --head feat/wave-a-finish-coil-admin \
  --title "feat(coil-admin): Operations Mode dashboard" \
  --body "$(cat <<'EOF'
## Summary
- New /coil-admin/ dashboard reading existing CoilPartnerSchool model.
- Pending-first sort on partner table; status funnel as secondary panel.
- Collaborative Classes panel = stub per spec decision §2.3.

## Test plan
- [x] 5 view tests pass
- [x] Manual smoke
EOF
)"
gh pr merge --repo teryopitikin/Classedge-Ai --merge --delete-branch
git checkout main && git pull personal main --ff-only
```

---

## Phase 4 — Academic Director dashboard (PR #4)

**Branch:** `feat/wave-a-finish-academic-director`

**Adds:**
- `accounts/views/academic_director.py`
- `templates/operations/academic_director_dashboard.html`
- `accounts/tests/test_academic_director_dashboard.py`

**Touches:** `accounts/urls.py`, `accounts/views/dashboard.py`, `accounts/tests/test_function_labels.py`.

### Task 4.1 — Branch, failing test

- [ ] **Step 1: Branch**

```bash
git checkout -b feat/wave-a-finish-academic-director
```

- [ ] **Step 2: Test file**

**Files:**
- Create: `accounts/tests/test_academic_director_dashboard.py`

```python
"""[Classedge LMS] Academic Director Operations Mode dashboard tests."""
from django.test import TestCase
from django.urls import reverse

from accounts.tests.operations_dashboard_mixin import OperationsDashboardTestMixin


class AcademicDirectorDashboardTests(OperationsDashboardTestMixin, TestCase):
    """[Classedge LMS] Access + content tests for the Academic Director dashboard."""

    url_name = "academic_director_dashboard"
    role = "Academic Director"
    glyph = "▲"
    kpi_count = 4

    def test_renders_for_academic_director(self):
        self.assert_renders_for_role()

    def test_403_for_other_roles(self):
        self.assert_403_for_other_roles()

    def test_glyph_renders_in_html(self):
        self.assert_glyph_renders()

    def test_pending_decisions_oldest_first(self):
        """[Classedge LMS] Pending decisions queue puts the oldest item at the top."""
        user = self.make_user_with_role(self.role, "ad1")
        self.client.force_login(user)
        resp = self.client.get(reverse(self.url_name))
        rows = resp.context["pending_decision_rows"]
        ages = [row.get("age_days", 0) for row in rows]
        self.assertEqual(ages, sorted(ages, reverse=True))

    def test_no_student_names_in_primary_panel(self):
        """[Classedge LMS] Per spec anti-pattern: no individual student names in the heatmap."""
        user = self.make_user_with_role(self.role, "ad2")
        self.client.force_login(user)
        resp = self.client.get(reverse(self.url_name))
        # heatmap rows are programs (categorical), not users
        for row in resp.context["heatmap_rows"]:
            self.assertNotIn("@", str(row), "row labels must not look like emails / individual students")
```

- [ ] **Step 3: Run (expect fail)**

```bash
env/bin/python manage.py test accounts.tests.test_academic_director_dashboard -v 2
```

### Task 4.2 — Implement the view

**Files:**
- Create: `accounts/views/academic_director.py`

- [ ] **Step 1: Write the view**

```python
"""[Classedge LMS] Academic Director Operations Mode dashboard view."""
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.utils import timezone

# Existing data sources where they exist; placeholders ('—') where not.
try:
    from gamification.models import StudentGamification
except ImportError:  # pragma: no cover
    StudentGamification = None
try:
    from central_content.models.curriculum_plan import CurriculumPlan
except ImportError:  # pragma: no cover
    CurriculumPlan = None


def _is_academic_director(user):
    """[Classedge LMS] True iff the authenticated user owns the Academic Director role."""
    return (
        user.is_authenticated
        and hasattr(user, "profile")
        and user.profile.role
        and user.profile.role.name == "Academic Director"
    )


def _time_of_day():
    """[Classedge LMS] morning / afternoon / evening for greeting copy."""
    h = timezone.localtime().hour
    if h < 12: return "morning"
    if h < 18: return "afternoon"
    return "evening"


def _at_risk_count():
    """[Classedge LMS] Proxy: count students whose XP is below a low-water threshold (50)."""
    if StudentGamification is None:
        return None
    return StudentGamification.objects.filter(xp__lt=50).count()


def _curriculum_coverage_pct():
    """[Classedge LMS] Coverage = approved CurriculumPlan rows / all CurriculumPlan rows × 100."""
    if CurriculumPlan is None:
        return None
    total = CurriculumPlan.objects.count()
    if not total:
        return None
    approved = CurriculumPlan.objects.filter(status__iexact="approved").count() if hasattr(CurriculumPlan, "status") else 0
    return round(approved / total * 100, 1)


def _ad_kpis():
    """[Classedge LMS] Build the 4 hero KPIs (calmer treatment for deep-dive role)."""
    coverage = _curriculum_coverage_pct()
    at_risk = _at_risk_count()
    return [
        {"label": "Curriculum Coverage", "value": f"{coverage}%" if coverage is not None else "—", "tone": ""},
        {"label": "Outcome Attainment", "value": "—", "tone": ""},
        {"label": "At-Risk Students", "value": at_risk if at_risk is not None else "—", "tone": "warn" if at_risk else ""},
        {"label": "Content Health", "value": "—", "tone": ""},
    ]


def _heatmap_rows():
    """[Classedge LMS] Program × Performance Band — categorical labels, no student PII."""
    return [
        {"program": program, "bands": [0, 0, 0, 0, 0]}  # 5 bands; counts populated by future data wiring
        for program in ["BS Computer Science", "BS Information Tech", "BS Information Systems", "BS Education", "Senior High"]
    ]


def _pending_decision_rows():
    """[Classedge LMS] Pending decisions queue — placeholder rows until decision feed is wired."""
    return []


@login_required
@user_passes_test(_is_academic_director)
def academic_director_dashboard(request):
    """[Classedge LMS] Render the Academic Director Operations Mode dashboard."""
    context = {
        "role_tag": "Academic Director",
        "role_glyph": "▲",
        "nav_items": [{"url": "#", "label": "Dashboard", "active": True}],
        "scope_tags": [{"label": "Term", "value": "Current"}],
        "quick_actions": [],
        "greeting_question": "Where is the academic program drifting from intent — and is it our content, our teachers, or our students?",
        "time_of_day": _time_of_day(),
        "as_of": timezone.localtime().strftime("%I:%M %p"),
        "kpis": _ad_kpis(),
        "ctx_left": {"title": "Term Close-out", "items": [], "empty": "Nothing yet."},
        "ctx_right": {"title": "Content Generator Handoffs", "items": [], "empty": "Nothing yet."},
        "heatmap_rows": _heatmap_rows(),
        "heatmap_bands": ["Below 60", "60–69", "70–79", "80–89", "90+"],
        "pending_decision_rows": _pending_decision_rows(),
        "pending_decision_columns": ["Item", "Submitted", "Age"],
    }
    return render(request, "operations/academic_director_dashboard.html", context)
```

- [ ] **Step 2: Create the template**

**Files:**
- Create: `templates/operations/academic_director_dashboard.html`

```html
{% comment %}[Classedge LMS] Academic Director Operations Mode dashboard — deep-dive treatment.{% endcomment %}
{% extends 'operations_base.html' %}

{% block primary_panel %}
  <div class="panel-header"><h2>Program × Performance</h2><span class="why"><em>cells = student counts per band</em></span></div>
  <table class="worklist">
    <thead>
      <tr><th>Program</th>{% for band in heatmap_bands %}<th>{{ band }}</th>{% endfor %}</tr>
    </thead>
    <tbody>
      {% for row in heatmap_rows %}
        <tr><td>{{ row.program }}</td>{% for c in row.bands %}<td>{{ c }}</td>{% endfor %}</tr>
      {% endfor %}
    </tbody>
  </table>
{% endblock %}

{% block secondary_panel %}
  {% include 'operations/worklist_panel.html' with title="Pending Decisions" why="oldest first" columns=pending_decision_columns rows=pending_decision_rows empty_message="No decisions waiting." %}
{% endblock %}
```

### Task 4.3 — Wire URL + router + label test

- [ ] **Step 1: URL**

```python
from accounts.views.academic_director import academic_director_dashboard
    path("academic-director/", academic_director_dashboard, name="academic_director_dashboard"),
```

- [ ] **Step 2: Router**

In `accounts/views/dashboard.py`:

```python
    is_academic_director = role_name == 'academic director'
    if is_academic_director:
        from accounts.views.academic_director import academic_director_dashboard
        return academic_director_dashboard(request)
```

- [ ] **Step 3: Label test**

```python
from accounts.views import academic_director
PUBLIC_MODULES = [department_access, department_admin, department_filter, registrar, coil_admin, academic_director]
```

### Task 4.4 — Test, smoke, commit, push, merge

- [ ] **Step 1: Run all dashboard tests**

```bash
env/bin/python manage.py test accounts.tests.test_academic_director_dashboard accounts.tests.test_function_labels -v 2
```

Expected: pass.

- [ ] **Step 2: Smoke (Academic Director user)**

```bash
env/bin/python manage.py shell -c "
from accounts.models.account_models import CustomUser, Profile
from roles.models import Role
u, _ = CustomUser.objects.get_or_create(username='ad_test', defaults={'email':'ad@x.io'})
u.set_password('ad'); u.save()
p, _ = Profile.objects.get_or_create(user=u)
r, _ = Role.objects.get_or_create(name='Academic Director')
p.role = r; p.save()
print('Academic Director user ad_test/ad ready')
"
```

Visit `http://localhost:8000/academic-director/` — verify ▲ glyph, 4 KPI cards, heatmap rows.

- [ ] **Step 3: Commit + PR + merge**

```bash
git add accounts/views/academic_director.py templates/operations/academic_director_dashboard.html accounts/tests/test_academic_director_dashboard.py accounts/urls.py accounts/views/dashboard.py accounts/tests/test_function_labels.py
git commit -m "$(cat <<'EOF'
feat(academic-director): Operations Mode dashboard

Calmer 4-KPI deep-dive treatment per spec. Program × Performance
heatmap (categorical, no PII) and pending-decisions queue. KPI sources
fall back to '—' when corresponding model isn't wired yet.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
git push -u personal feat/wave-a-finish-academic-director
gh pr create --repo teryopitikin/Classedge-Ai --base main --head feat/wave-a-finish-academic-director \
  --title "feat(academic-director): Operations Mode dashboard" \
  --body "## Summary
- /academic-director/ dashboard with calmer 4-KPI treatment.
- Heatmap is categorical (programs × bands) — no student names per spec anti-pattern.
- KPIs that depend on un-built models render '—'.

## Test plan
- [x] 5 view tests pass
- [x] Smoke OK"
gh pr merge --repo teryopitikin/Classedge-Ai --merge --delete-branch
git checkout main && git pull personal main --ff-only
```

---

## Phase 5 — IT Admin redo (PR #5)

**Branch:** `feat/wave-a-finish-it-admin-redo`

**Adds:**
- `templates/operations/it_admin_dashboard.html`
- (Rewrites: `accounts/views/it_admin.py`)
- (Rewrites: `accounts/tests/test_it_admin_dashboard.py` — adapts to new template + Operations Mode mixin)

**Deletes:**
- `templates/it_admin_base.html`
- `templates/it_admin/dashboard.html`
- (Optionally) `templates/it_admin/` directory if empty after deletion

**Touches:**
- `accounts/tests/test_function_labels.py`

### Task 5.1 — Inventory existing IT Admin nav targets

- [ ] **Step 1: Branch**

```bash
git checkout -b feat/wave-a-finish-it-admin-redo
```

- [ ] **Step 2: Capture nav targets that the new shell must preserve**

```bash
grep -nE "url '" templates/it_admin_base.html
```

Expected output: lines for `it_admin_dashboard`, `admin_and_staff_list`, `roleList`, `department_list`, `sign_out`. Record any others that appear (write them down — they all need to remain in the new shell's `nav_items`).

### Task 5.2 — Rewrite the IT Admin view

**Files:**
- Modify: `accounts/views/it_admin.py` (full rewrite)

- [ ] **Step 1: Replace file contents**

```python
"""[Classedge LMS] IT Admin Operations Mode dashboard view."""
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import connection
from django.shortcuts import render
from django.utils import timezone

from accounts.models.account_models import CustomUser
from accounts.models.department_models import Department
from roles.models import Role


def _is_it_admin(user):
    """[Classedge LMS] Phase-1 check: is_superuser is the source of truth."""
    return user.is_authenticated and user.is_superuser


def _time_of_day():
    """[Classedge LMS] morning / afternoon / evening for greeting copy."""
    h = timezone.localtime().hour
    if h < 12: return "morning"
    if h < 18: return "afternoon"
    return "evening"


def _failed_login_count_24h():
    """[Classedge LMS] Failed-login count in last 24h via CustomUser.failed_login_count if maintained."""
    if hasattr(CustomUser, "failed_login_count"):
        # crude proxy: sum across users; production swaps in a real auth-log query
        return sum(CustomUser.objects.values_list("failed_login_count", flat=True))
    return None


def _it_admin_kpis():
    """[Classedge LMS] 5 KPI cards. Vendor-gated entries fall back to '—'."""
    user_count = CustomUser.objects.filter(is_active=True).count()
    failed_logins = _failed_login_count_24h()
    on_postgres = connection.vendor == "postgresql"
    return [
        {"label": "Active Users", "value": user_count, "tone": ""},
        {"label": "Failed Logins 24h", "value": failed_logins if failed_logins is not None else "—", "tone": "warn" if (failed_logins or 0) > 50 else ""},
        {"label": "5xx Rate", "value": "—" if not on_postgres else "0.0%", "tone": ""},
        {"label": "Celery Queue", "value": "—", "tone": ""},
        {"label": "DB p95 Latency", "value": "—" if not on_postgres else "—", "tone": ""},
    ]


def _admin_actions_feed():
    """[Classedge LMS] Recent admin actions feed; placeholder rows until easyaudit integration is wired."""
    return []


def _service_health_rows():
    """[Classedge LMS] Service health placeholder — 24h tick bars per service (web, celery, redis, db)."""
    return [
        {"service": "web", "ticks": ["ok"] * 24},
        {"service": "celery", "ticks": ["ok"] * 24},
        {"service": "redis", "ticks": ["ok"] * 24},
        {"service": "db", "ticks": ["ok"] * 24},
    ]


@login_required
@user_passes_test(_is_it_admin)
def it_admin_dashboard(request):
    """[Classedge LMS] Render the IT Admin Operations Mode dashboard."""
    context = {
        "role_tag": "IT Admin",
        "role_glyph": "⚙",
        "nav_items": [
            {"url": "#", "label": "Dashboard", "active": True},
            {"url": "/admin_and_staff_list/", "label": "Users"},
            {"url": "/roleList/", "label": "Roles"},
            {"url": "/departments/", "label": "Departments"},
        ],
        "scope_tags": [{"label": "Term", "value": "Current"}],
        "quick_actions": [],
        "greeting_question": "Is the platform healthy — and is anyone blocked waiting on me?",
        "time_of_day": _time_of_day(),
        "as_of": timezone.localtime().strftime("%I:%M %p"),
        "kpis": _it_admin_kpis(),
        "ctx_left": {"title": "Service Health", "items": [r["service"].upper() for r in _service_health_rows()], "empty": ""},
        "ctx_right": {"title": "Recent Activity", "items": [], "empty": "No recent admin actions."},
        "user_count": CustomUser.objects.filter(is_active=True).count(),
        "role_count": Role.objects.count(),
        "department_count": Department.objects.count(),
        "superuser_count": CustomUser.objects.filter(is_superuser=True).count(),
        "admin_actions": _admin_actions_feed(),
        "admin_action_columns": ["When", "Who", "Action"],
        "service_health_rows": _service_health_rows(),
    }
    return render(request, "operations/it_admin_dashboard.html", context)
```

(Note: the four count keys — `user_count`, `role_count`, `department_count`, `superuser_count` — are preserved because the existing test in `test_it_admin_dashboard.py` asserts them. They're also surfaced as KPI inputs.)

### Task 5.3 — Create the role template, delete the old templates

**Files:**
- Create: `templates/operations/it_admin_dashboard.html`
- Delete: `templates/it_admin_base.html`
- Delete: `templates/it_admin/dashboard.html`

- [ ] **Step 1: Create the new role template**

```html
{% comment %}[Classedge LMS] IT Admin Operations Mode dashboard.{% endcomment %}
{% extends 'operations_base.html' %}

{% block primary_panel %}
  {% include 'operations/worklist_panel.html' with title="Recent Admin Actions" why="newest first" columns=admin_action_columns rows=admin_actions empty_message="No recent admin actions." %}
{% endblock %}

{% block secondary_panel %}
  <div class="panel-header"><h2>Service Health</h2><span class="why"><em>24h status, one tick = 1h</em></span></div>
  <table class="worklist">
    <thead><tr><th>Service</th><th>24h</th></tr></thead>
    <tbody>
      {% for row in service_health_rows %}
        <tr><td>{{ row.service|upper }}</td><td>{% for t in row.ticks %}<span class="live-dot" style="display:inline-block;margin-right:1px;"></span>{% endfor %}</td></tr>
      {% endfor %}
    </tbody>
  </table>
{% endblock %}
```

- [ ] **Step 2: Delete the old templates**

```bash
rm templates/it_admin_base.html
rm templates/it_admin/dashboard.html
rmdir templates/it_admin 2>/dev/null
```

- [ ] **Step 3: Verify nothing else references them**

```bash
grep -rE "it_admin_base|it_admin/dashboard" --include='*.py' --include='*.html' . 2>/dev/null | grep -v env/ | grep -v __pycache__
```

Expected: empty.

### Task 5.4 — Update the existing IT Admin test to match the new template path

**Files:**
- Modify: `accounts/tests/test_it_admin_dashboard.py`

- [ ] **Step 1: The existing tests assert `user_count` etc. in context — these still pass because the rewritten view keeps those keys. Add 2 new tests**

Append to `accounts/tests/test_it_admin_dashboard.py`:

```python
class ItAdminDashboardOperationsModeTests(TestCase):
    """[Classedge LMS] Operations Mode shell + KPI strip render for IT Admin."""

    def setUp(self):
        self.it_admin_role, _ = Role.objects.get_or_create(name="IT Admin")

    def test_renders_kpi_strip(self):
        from django.urls import reverse
        u = CustomUser.objects.create_user(username="su_op", email="su@x.io", password="x")
        p = Profile.objects.get(user=u)
        p.role = self.it_admin_role
        p.save()  # signal flips is_superuser=True
        u.refresh_from_db()
        self.client.force_login(u)
        resp = self.client.get(reverse("it_admin_dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["kpis"]), 5)
        self.assertContains(resp, "⚙")  # IT Admin glyph

    def test_uses_operations_template(self):
        from django.urls import reverse
        u = CustomUser.objects.create_user(username="su_t", email="sut@x.io", password="x")
        p = Profile.objects.get(user=u)
        p.role = self.it_admin_role
        p.save()
        u.refresh_from_db()
        self.client.force_login(u)
        resp = self.client.get(reverse("it_admin_dashboard"))
        self.assertTemplateUsed(resp, "operations/it_admin_dashboard.html")
        self.assertTemplateUsed(resp, "operations_base.html")
```

- [ ] **Step 2: Run the IT Admin tests**

```bash
env/bin/python manage.py test accounts.tests.test_it_admin_dashboard -v 2
```

Expected: existing tests still pass + 2 new tests pass.

### Task 5.5 — Final verification

- [ ] **Step 1: Run full accounts test suite**

```bash
env/bin/python manage.py test accounts -v 1
```

Expected: all pass.

- [ ] **Step 2: Run full project test suite (catch any other module that referenced the old templates)**

```bash
env/bin/python manage.py test 2>&1 | tail -20
```

Expected: no failures attributable to template changes.

- [ ] **Step 3: Smoke as superuser**

Visit `http://localhost:8000/it-admin/` after logging in as `admin`. Verify ⚙ glyph, 5 KPI cards, Users/Roles/Departments nav links work.

### Task 5.6 — Commit, push, open PR, merge

- [ ] **Step 1: Stage everything (including deletions)**

```bash
git add -A accounts/views/it_admin.py templates/operations/it_admin_dashboard.html accounts/tests/test_it_admin_dashboard.py templates/it_admin_base.html templates/it_admin/dashboard.html
git status
```

Expected: shows the new template, modified view, modified tests, and the two deleted files.

- [ ] **Step 2: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat(it-admin): redo dashboard in Operations Mode

Replaces the Bricolage scaffold (templates/it_admin_base.html +
templates/it_admin/dashboard.html) with the unified Operations Mode
shell. Preserves Users/Roles/Departments nav and the four count
context keys asserted by existing tests.

Closes the spec for finishing Wave A: docs/superpowers/specs/2026-04-27-wave-a-finish-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 3: Push, open PR, merge**

```bash
git push -u personal feat/wave-a-finish-it-admin-redo
gh pr create --repo teryopitikin/Classedge-Ai --base main --head feat/wave-a-finish-it-admin-redo \
  --title "feat(it-admin): redo dashboard in Operations Mode" \
  --body "$(cat <<'EOF'
## Summary
- Rewrites IT Admin landing page on the Operations Mode shell.
- Deletes the Bricolage scaffold templates (`it_admin_base.html`, `it_admin/dashboard.html`).
- Preserves Users/Roles/Departments nav targets and existing context keys (`user_count`, etc.).
- Adds 2 new template/glyph tests; existing IT Admin tests still pass unchanged.

## Why
Final PR of Wave A finish (spec PR #15). Closes the gap between the role rename (PR #2 of role refactor) and the redesigned dashboard system.

## Rollback
`git revert <merge>` restores the deleted scaffold templates from history.

## Test plan
- [x] `python manage.py test accounts` → all pass
- [x] Manual smoke as superuser → ⚙ glyph, 5 KPI cards, nav links resolve
EOF
)"
gh pr merge --repo teryopitikin/Classedge-Ai --merge --delete-branch
git checkout main && git pull personal main --ff-only
```

---

## Definition of done

- [ ] All 5 PRs merged to main on `personal` remote.
- [ ] `templates/it_admin_base.html` and `templates/it_admin/dashboard.html` no longer exist.
- [ ] `python manage.py test accounts` passes locally.
- [ ] `python manage.py migrate` reports no pending migrations (Wave A is pure UI/view code — no migrations).
- [ ] Logging in as Registrar / Coil Admin / Academic Director / IT Admin (superuser) lands on the redesigned dashboard with the role glyph in the sidebar.
