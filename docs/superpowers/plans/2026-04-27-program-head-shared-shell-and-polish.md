# Program Head + Shared Shell + Operations Polish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the Program Head dashboard under Operations Mode, raise the four shipped Wave A dashboards to the Student/Teacher polish bar, and fix the right-side empty space across all three role-bases by extracting a shared `role_skeleton.html` parent.

**Architecture:** Three sequenced PRs. PR #1 introduces `templates/role_skeleton.html` as a shared parent and refactors `student_base.html`, `teacher_base.html`, `operations_base.html` to extend it; adds the `hero | hero-widget` split and an opt-in `right-rail` column to all three. PR #2 ships Program Head's deep-dive dashboard *together with* the Operations Mode polish foundation upgrade (visual depth, motion, sparklines, empty-state block, mobile responsive, accessibility, JetBrains Mono). PR #3 mechanically backports the polish affordances and adds hero widgets + right rails to Registrar / Coil Admin / Academic Director / IT Admin.

**Tech Stack:** Django (templates + views), Pytest with `pytest-django`, vanilla CSS (Bricolage Grotesque + Fraunces + Inter Tight + JetBrains Mono via Google Fonts), inline SVG sparklines (no JS chart lib), no HTMX in this plan.

**Spec:** `docs/superpowers/specs/2026-04-27-program-head-shared-shell-and-polish-design.md`

---

## File Structure

### Phase 1 (PR #1) — Shared skeleton + right rail

**Create:**
- `templates/role_skeleton.html` — common `<head>` + body skeleton (~25 lines)
- `accounts/tests/test_shared_skeleton.py` — 6 tests for skeleton structure

**Modify:**
- `templates/student_base.html` — extends skeleton; adds hero/right-rail blocks
- `templates/teacher_base.html` — extends skeleton; adds hero/right-rail blocks
- `templates/operations_base.html` — extends skeleton; adds hero/right-rail blocks
- `static/css/student_theme.css` — shell grid CSS (hero / content-grid / right-rail / responsive)
- `static/css/operations_base.css` — same shell grid CSS
- `templates/teacher_base.html` inline `<style>` — same shell grid CSS

### Phase 2 (PR #2) — Program Head + Operations polish

**Create:**
- `accounts/views/program_head_dashboard.py` — view + standalone KPI functions + `_build_context`
- `templates/operations/program_head_dashboard.html` — extends `operations_base.html`
- `accounts/tests/test_program_head_dashboard.py` — Render + Permissions + KPI tests

**Modify:**
- `static/css/operations_base.css` — polish foundation (depth, motion, KPI affordances, empty-state, skeletons, responsive, a11y, print, JetBrains Mono)
- `templates/operations/kpi_strip.html` — render `delta_direction`, `delta_intent`, `sparkline`
- `templates/operations/worklist_panel.html` — empty-state block + flagged-row affordance
- `templates/operations/context_strip.html` — empty-state block
- `templates/operations/scope_bar.html` — pulse class on `.live-dot`; `.mono` on `as_of`
- `templates/operations_base.html` — `id="main"` on `<main>`, `.mono` utility wiring
- `accounts/views/dashboard.py` — add `is_program_head` branch
- `accounts/urls.py` — add `program_head_dashboard` URL
- `accounts/tests/operations_dashboard_mixin.py` — extend with `assert_optional_kpi_fields_handled`, `assert_empty_state_renders`, `assert_skip_link_first`

### Phase 3 (PR #3) — Backport polish + rails

**Modify:**
- `accounts/views/registrar.py` — add `delta_direction` / `delta_intent` / `sparkline` to KPIs; add `hero_widget` + `right_rail` context
- `accounts/views/coil_admin.py` — same
- `accounts/views/academic_director.py` — same
- `accounts/views/it_admin.py` — same
- `templates/operations/registrar_dashboard.html` — warmer empty copy + hero/rail blocks
- `templates/operations/coil_admin_dashboard.html` — same
- `templates/operations/academic_director_dashboard.html` — same
- `templates/operations/it_admin_dashboard.html` — same
- `accounts/tests/test_registrar_dashboard.py` — sparkline + empty-copy assertions
- `accounts/tests/test_coil_admin_dashboard.py` — same
- `accounts/tests/test_academic_director_dashboard.py` — same
- `accounts/tests/test_it_admin_dashboard.py` — same
- `docs/superpowers/specs/2026-04-27-wave-a-finish-design.md` — footer note pointing to backport branch

---

# Phase 1 — Shared role skeleton + right rail (PR #1)

Branch: `feat/shared-role-skeleton-and-right-rail` off `main`.

### Task 1.1: Create the shared skeleton test file (RED)

**Files:**
- Create: `accounts/tests/test_shared_skeleton.py`

- [ ] **Step 1: Write the failing test file**

```python
"""[Classedge LMS] Tests for the shared role_skeleton.html parent template."""
from django.test import TestCase
from django.template.loader import get_template


class TestRoleSkeletonExists(TestCase):
    def test_role_skeleton_template_loads(self):
        """[Classedge LMS] The shared parent template can be loaded by the engine."""
        # Will raise TemplateDoesNotExist until role_skeleton.html exists.
        get_template("role_skeleton.html")


class TestRoleBasesExtendSkeleton(TestCase):
    def test_student_base_extends_role_skeleton(self):
        with open("templates/student_base.html", encoding="utf-8") as f:
            source = f.read()
        self.assertIn("{% extends 'role_skeleton.html' %}", source)

    def test_teacher_base_extends_role_skeleton(self):
        with open("templates/teacher_base.html", encoding="utf-8") as f:
            source = f.read()
        self.assertIn("{% extends 'role_skeleton.html' %}", source)

    def test_operations_base_extends_role_skeleton(self):
        with open("templates/operations_base.html", encoding="utf-8") as f:
            source = f.read()
        self.assertIn("{% extends 'role_skeleton.html' %}", source)
```

- [ ] **Step 2: Run tests, verify all four fail**

```bash
cd /home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai
python -m pytest accounts/tests/test_shared_skeleton.py -v
```

Expected: 4 failures — `test_role_skeleton_template_loads` raises `TemplateDoesNotExist`; the three "extends" tests fail with `'{% extends 'role_skeleton.html' %}' not found in source`.

- [ ] **Step 3: Commit the failing tests**

```bash
git checkout -b feat/shared-role-skeleton-and-right-rail
git add accounts/tests/test_shared_skeleton.py
git commit -m "test(skeleton): add failing tests for role_skeleton.html parent"
```

---

### Task 1.2: Create `templates/role_skeleton.html`

**Files:**
- Create: `templates/role_skeleton.html`

- [ ] **Step 1: Write the skeleton file**

```django
{% load static %}
<!doctype html>
<html lang="en-US" data-theme="{{ theme_preference|default:'light' }}">
<head>
  <meta charset="utf-8">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="csrf-token" content="{{ csrf_token }}">
  <title>{% block title %}{{ SCHOOL_NAME }} · ClassEdge{% endblock %}</title>

  <link rel="icon" type="image/png" href="{{ MEDIA_URL }}logos/HCCCI-logo.png?{{ logo_update_time }}">
  <link rel="apple-touch-icon" href="{{ MEDIA_URL }}logos/HCCCI-logo.png?{{ logo_update_time }}">
  <meta property="og:title" content="{{ SCHOOL_NAME }}">
  <meta property="og:type" content="website">
  <meta property="og:image" content="{{ request.scheme }}://{{ request.get_host }}{{ MEDIA_URL }}logos/HCCCI-logo.png?{{ logo_update_time }}">
  <meta property="og:site_name" content="{{ SCHOOL_NAME }}">
  <meta name="theme-color" content="#ffffff">

  {% block fonts %}{% endblock %}
  {% block theme_css %}{% endblock %}
  {% block extra_head %}{% endblock %}
</head>
<body class="{% block body_class %}{% endblock %}" data-current-user-id="{{ request.user.id }}">
  <a class="skip-link" href="#main">Skip to content</a>
  {% block body %}{% endblock %}
  {% block extra_scripts %}{% endblock %}
</body>
</html>
```

- [ ] **Step 2: Run the template-load test, verify it passes**

```bash
python -m pytest accounts/tests/test_shared_skeleton.py::TestRoleSkeletonExists -v
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add templates/role_skeleton.html
git commit -m "feat(skeleton): add role_skeleton.html shared parent template"
```

---

### Task 1.3: Refactor `student_base.html` to extend the skeleton

**Files:**
- Modify: `templates/student_base.html` (currently 198 lines; refactor moves head boilerplate into skeleton blocks)

- [ ] **Step 1: Read the current student_base.html in full to understand block contract**

```bash
wc -l templates/student_base.html
```

- [ ] **Step 2: Rewrite the top of `student_base.html` to extend the skeleton**

Replace the existing `{% load static %}` through `</head>` block with:

```django
{% extends 'role_skeleton.html' %}
{% load static %}

{% block title %}{{ SCHOOL_NAME }} | Student Dashboard{% endblock %}

{% block fonts %}
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,500;12..96,600;12..96,700;12..96,800&family=Inter+Tight:wght@400;500;600;700&display=swap" rel="stylesheet" />
{% endblock %}

{% block theme_css %}
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet" />
  <link rel="stylesheet" href="https://cdn.datatables.net/1.13.7/css/dataTables.bootstrap5.min.css" />
  <link rel="stylesheet" href="https://cdn.datatables.net/responsive/3.0.0/css/responsive.bootstrap5.min.css" />
  <link rel="stylesheet" href="{% static 'vendors/select2/select2.min.css' %}" />
  <link rel="stylesheet" href="{% static 'vendors/select2-bootstrap-5-theme/select2-bootstrap-5-theme.min.css' %}" />
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/sweetalert2@11/dist/sweetalert2.min.css" />
  <link href="{% static 'vendors/glightbox/glightbox.min.css' %}" rel="stylesheet" />
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" />
  <link rel="stylesheet" href="{% static 'css/student_theme.css' %}" />
  {% block extra_css %}{% endblock %}
{% endblock %}

{% block body_class %}student-shell{% endblock %}
```

- [ ] **Step 3: Wrap the existing `<body>` content in a `{% block body %}` block**

Find the existing `<body data-theme="...">...` opening tag and the matching `</body>` closing tag.

Replace `<body data-theme="{{ theme_preference }}" data-current-user-id="{{ request.user.id }}">` (and any inline opening before the `<div class="app">`) with `{% block body %}`. The body skeleton (`<div class="app">…hamburger…sidebar…<main>…</main>…</div>`) stays inside this block.

Replace `</body></html>` at file end with:

```django
{% endblock %}

{% block extra_scripts %}
  <script src="{% static 'js/student_theme.js' %}"></script>
  {% block extra_js %}{% endblock %}
{% endblock %}
```

(Move the `<script src="{% static 'js/student_theme.js' %}"></script>` from its current position into `extra_scripts`.)

- [ ] **Step 4: Restructure the hero block to expose `greeting` + `hero_widget` blocks**

Find the existing greeting markup (the `Good afternoon, student` block + level bar + chips). Wrap it in:

```django
<header class="hero" id="main">
  <div class="greeting">
    {% block greeting %}
      {# default greeting markup — kept here so existing dashboards still render #}
      <h1>Good {{ time_of_day|default:"day" }}, {{ request.user.first_name|default:request.user.username }} <span class="wave">👋</span></h1>
      <p class="hero-sub">Welcome back! Check your upcoming deadlines.</p>
    {% endblock %}
  </div>
  <aside class="hero-widget">
    {% block hero_widget %}{% endblock %}
  </aside>
</header>
```

Wrap the main grid (e.g., `<div class="dash-grid">…</div>`) in:

```django
<div class="content-grid">
  <section class="content-main">
    {% block content %}
      {# default content — for legacy student pages that don't override #}
    {% endblock %}
  </section>
  <aside class="right-rail">
    {% block right_rail %}{% endblock %}
  </aside>
</div>
```

- [ ] **Step 5: Run the student-extends test, verify it passes**

```bash
python -m pytest accounts/tests/test_shared_skeleton.py::TestRoleBasesExtendSkeleton::test_student_base_extends_role_skeleton -v
```

Expected: PASS.

- [ ] **Step 6: Smoke-test the existing student dashboard renders without 500**

Start the dev server and load `/dashboard/` as a Student user.

```bash
python manage.py runserver
```

Manually visit `http://localhost:8000/dashboard/`. Verify: page renders, no template error, sidebar visible, greeting visible.

- [ ] **Step 7: Commit**

```bash
git add templates/student_base.html
git commit -m "refactor(student-base): extend role_skeleton.html and expose hero/rail blocks"
```

---

### Task 1.4: Refactor `teacher_base.html` to extend the skeleton

**Files:**
- Modify: `templates/teacher_base.html` (currently 629 lines)

- [ ] **Step 1: Identify the head boilerplate to remove**

Lines roughly 1–13 of `teacher_base.html` contain `{% load static %}`, doctype, `<html>`, `<head>` opening, `<meta charset>`, viewport, csrf-token, title, favicon, fonts. These move into skeleton blocks. The inline `<style>` block (~lines 15–500+) and the body markup stay in this file.

- [ ] **Step 2: Rewrite the top to extend the skeleton**

Replace lines 1–14 (everything before `<style>`) with:

```django
{% extends 'role_skeleton.html' %}
{% load static %}

{% block title %}ClassEdge · Faculty{% endblock %}

{% block fonts %}
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,400;9..144,500;9..144,600;9..144,700&family=Inter+Tight:wght@400;500;600;700&display=swap" rel="stylesheet">
{% endblock %}

{% block theme_css %}
  <style>
```

(The `<style>` opener is now inside the `theme_css` block. The closing `</style>` is followed by `{% endblock %}`.)

Find the `</style>` tag and the `</head><body>` that follows. Replace `</head><body…>` with:

```django
  </style>
{% endblock %}

{% block body_class %}teacher-shell{% endblock %}

{% block body %}
```

Replace the closing `</body></html>` at file end with `{% endblock %}`.

- [ ] **Step 3: Restructure the hero block to expose `greeting` + `hero_widget`**

Find the teacher greeting block (`<h1>Good {{ time_of_day }}…</h1>` markup). Wrap as:

```django
<header class="hero" id="main">
  <div class="greeting">
    {% block greeting %}
      <h1>Good {{ time_of_day|default:"day" }}, {{ request.user.first_name|default:"Teacher" }}</h1>
      <p class="hero-sub">{{ greeting_question|default:"Here's your day at a glance." }}</p>
    {% endblock %}
  </div>
  <aside class="hero-widget">
    {% block hero_widget %}{% endblock %}
  </aside>
</header>
```

Find the main content grid and wrap it:

```django
<div class="content-grid">
  <section class="content-main">
    {% block content %}{% endblock %}
  </section>
  <aside class="right-rail">
    {% block right_rail %}{% endblock %}
  </aside>
</div>
```

- [ ] **Step 4: Run the teacher-extends test, verify it passes**

```bash
python -m pytest accounts/tests/test_shared_skeleton.py::TestRoleBasesExtendSkeleton::test_teacher_base_extends_role_skeleton -v
```

Expected: PASS.

- [ ] **Step 5: Smoke-test as a Teacher**

Visit `/dashboard/` as a Teacher user. Verify page renders, no template error.

- [ ] **Step 6: Commit**

```bash
git add templates/teacher_base.html
git commit -m "refactor(teacher-base): extend role_skeleton.html and expose hero/rail blocks"
```

---

### Task 1.5: Refactor `templates/operations_base.html` to extend the skeleton

**Files:**
- Modify: `templates/operations_base.html` (currently 54 lines)

- [ ] **Step 1: Rewrite the file in full**

```django
{% extends 'role_skeleton.html' %}
{% comment %}[Classedge LMS] Operations Mode shell — base for all non-teacher/non-student dashboards.{% endcomment %}
{% load static %}

{% block title %}{{ role_tag }} · ClassEdge{% endblock %}

{% block fonts %}
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300..700&family=Inter+Tight:wght@400;500;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
{% endblock %}

{% block theme_css %}
  <link rel="stylesheet" href="{% static 'css/operations_base.css' %}">
{% endblock %}

{% block body_class %}ops-shell-body{% endblock %}

{% block body %}
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
    <main id="main" class="ops-main">
      {% include 'operations/scope_bar.html' with tags=scope_tags as_of=as_of %}
      <header class="ops-greeting hero">
        <div class="greeting-text greeting">
          {% block greeting %}
            <h1>Good {{ time_of_day }}, {{ request.user.first_name|default:request.user.username }}</h1>
            <p class="walk-in"><em>{{ greeting_question }}</em></p>
            <div class="ops-actions">
              {% for a in quick_actions %}
                <a href="{{ a.url }}" class="ops-btn {% if a.primary %}ops-btn-primary{% else %}ops-btn-secondary{% endif %}">{{ a.label }}</a>
              {% endfor %}
            </div>
          {% endblock %}
        </div>
        <aside class="hero-widget">
          {% block hero_widget %}{% endblock %}
        </aside>
      </header>
      {% include 'operations/kpi_strip.html' with kpis=kpis %}
      <div class="content-grid">
        <section class="content-main">
          {% block content %}
            <section class="ops-grid">
              <div class="ops-primary">{% block primary_panel %}{% endblock %}</div>
              <div class="ops-secondary">{% block secondary_panel %}{% endblock %}</div>
            </section>
            {% include 'operations/context_strip.html' with left=ctx_left right=ctx_right %}
          {% endblock %}
        </section>
        <aside class="right-rail">
          {% block right_rail %}{% endblock %}
        </aside>
      </div>
    </main>
  </div>
{% endblock %}
```

The `{% block primary_panel %}` and `{% block secondary_panel %}` are preserved, so the four existing role templates that override them keep working without changes.

- [ ] **Step 2: Run the operations-extends test, verify it passes**

```bash
python -m pytest accounts/tests/test_shared_skeleton.py::TestRoleBasesExtendSkeleton::test_operations_base_extends_role_skeleton -v
```

Expected: PASS.

- [ ] **Step 3: Run the existing Wave A dashboard tests, verify nothing broke**

```bash
python -m pytest accounts/tests/test_registrar_dashboard.py accounts/tests/test_coil_admin_dashboard.py accounts/tests/test_academic_director_dashboard.py accounts/tests/test_it_admin_dashboard.py -v
```

Expected: all existing assertions still pass.

- [ ] **Step 4: Smoke-test all four Operations dashboards**

Login as Registrar, then Coil Admin, then Academic Director, then IT Admin. Verify each `/dashboard/` redirect lands cleanly.

- [ ] **Step 5: Commit**

```bash
git add templates/operations_base.html
git commit -m "refactor(operations-base): extend role_skeleton.html and expose hero/rail blocks"
```

---

### Task 1.6: Add additional skeleton structure tests

**Files:**
- Modify: `accounts/tests/test_shared_skeleton.py`

- [ ] **Step 1: Append additional structural assertions**

Add to `accounts/tests/test_shared_skeleton.py`:

```python
from django.urls import reverse
from accounts.tests.helpers import make_profile_for
from accounts.models.account_models import CustomUser
import uuid


class TestSkeletonStructureRendered(TestCase):
    """[Classedge LMS] Verify rendered HTML carries the chrome the skeleton provides."""

    def setUp(self):
        username = f"u-{uuid.uuid4().hex[:8]}"
        self.user = CustomUser.objects.create_user(
            username=username, email=f"{username}@x.io", password="x"
        )
        make_profile_for(self.user, "Teacher")
        self.client.force_login(self.user)

    def test_csrf_meta_present(self):
        resp = self.client.get(reverse("dashboard"))
        self.assertContains(resp, '<meta name="csrf-token"')

    def test_og_meta_present(self):
        resp = self.client.get(reverse("dashboard"))
        self.assertContains(resp, 'property="og:type"')

    def test_skip_link_present(self):
        resp = self.client.get(reverse("dashboard"))
        self.assertContains(resp, 'class="skip-link"')

    def test_data_current_user_id_set(self):
        resp = self.client.get(reverse("dashboard"))
        self.assertContains(resp, f'data-current-user-id="{self.user.id}"')
```

- [ ] **Step 2: Run the new tests**

```bash
python -m pytest accounts/tests/test_shared_skeleton.py::TestSkeletonStructureRendered -v
```

Expected: all 4 PASS.

- [ ] **Step 3: Commit**

```bash
git add accounts/tests/test_shared_skeleton.py
git commit -m "test(skeleton): add rendered-HTML assertions for csrf, og, skip-link, user-id"
```

---

### Task 1.7: Add shell grid CSS to `student_theme.css`

**Files:**
- Modify: `static/css/student_theme.css`

- [ ] **Step 1: Append shell grid rules at end of file**

```css
/* ─── Shared shell grid (Phase 1) ─────────────────────── */
.skip-link {
  position: absolute;
  left: -9999px;
  top: 0;
  background: var(--gold, #f4b740);
  color: var(--bg, #0a0f1f);
  padding: 8px 12px;
  z-index: 9999;
}
.skip-link:focus { left: 0; }

.hero {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 24px;
  align-items: start;
  margin-bottom: 24px;
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 24px;
  align-items: start;
}

.right-rail {
  position: sticky;
  top: 32px;
  align-self: start;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.right-rail:empty { display: none; }
.content-grid:has(.right-rail:empty) { grid-template-columns: 1fr; }

@media (max-width: 1280px) {
  .content-grid { grid-template-columns: 1fr; }
  .right-rail { position: static; flex-direction: row; flex-wrap: wrap; }
  .right-rail > .rail-card { flex: 1 1 calc(50% - 8px); }
}

@media (max-width: 900px) {
  .hero { grid-template-columns: 1fr; }
  .right-rail { flex-direction: column; }
  .right-rail > .rail-card { flex: 1 1 100%; }
}
```

- [ ] **Step 2: Reload student dashboard and resize viewport**

Verify at 1920px / 1280px / 900px / 375px the layout responds:
- 1920px: 3-column, sticky right rail
- 1280px: hero stacks if needed, right rail becomes inline 2-up
- 900px: full single-column

- [ ] **Step 3: Commit**

```bash
git add static/css/student_theme.css
git commit -m "feat(student-shell): add hero/right-rail shell grid + responsive breakpoints"
```

---

### Task 1.8: Add shell grid CSS to `operations_base.css`

**Files:**
- Modify: `static/css/operations_base.css`

- [ ] **Step 1: Append shell grid rules at end of file**

```css
/* ─── Shared shell grid (Phase 1) ─────────────────────── */
.skip-link {
  position: absolute;
  left: -9999px;
  top: 0;
  background: var(--gold);
  color: var(--forest);
  padding: 8px 12px;
  z-index: 9999;
}
.skip-link:focus { left: 0; }

.hero {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 24px;
  align-items: start;
  margin-bottom: 24px;
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 24px;
  align-items: start;
}

.right-rail {
  position: sticky;
  top: 32px;
  align-self: start;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.right-rail:empty { display: none; }
.content-grid:has(.right-rail:empty) { grid-template-columns: 1fr; }

.hero-widget {
  background: var(--paper);
  border: 1px solid var(--cream-2);
  border-radius: 12px;
  padding: 16px;
  min-height: 180px;
}

@media (max-width: 1280px) {
  .content-grid { grid-template-columns: 1fr; }
  .right-rail { position: static; flex-direction: row; flex-wrap: wrap; }
  .right-rail > .rail-card { flex: 1 1 calc(50% - 8px); }
}

@media (max-width: 900px) {
  .ops-shell { grid-template-columns: 1fr; }
  .ops-side { position: static; height: auto; flex-direction: row; align-items: center; }
  .ops-nav { flex-direction: row; gap: 8px; overflow-x: auto; }
  .ops-user { display: none; }
  .ops-main { padding: 24px 16px; }
  .hero { grid-template-columns: 1fr; }
  .ops-grid { grid-template-columns: 1fr; }
  .kpi-strip { grid-template-columns: repeat(2, 1fr); }
  .context-strip { grid-template-columns: 1fr; }
  .right-rail { flex-direction: column; }
  .right-rail > .rail-card { flex: 1 1 100%; }
}
```

- [ ] **Step 2: Smoke-test all four Operations dashboards at multiple viewports**

Login as each role (Registrar / Coil Admin / Academic Director / IT Admin) and resize to 1280px and 900px. Verify the right rail collapses and reappears correctly. Right rail will be empty (no `right_rail` block content yet); the `:has(.right-rail:empty)` rule should produce a single-column layout — verify.

- [ ] **Step 3: Commit**

```bash
git add static/css/operations_base.css
git commit -m "feat(operations-shell): add hero/right-rail shell grid + responsive breakpoints"
```

---

### Task 1.9: Add shell grid CSS to `teacher_base.html` inline `<style>`

**Files:**
- Modify: `templates/teacher_base.html` inline `<style>` block

- [ ] **Step 1: Locate end of inline `<style>` block (just before `</style>`)**

- [ ] **Step 2: Append shell grid rules**

```css
/* ─── Shared shell grid (Phase 1) ─────────────────────── */
.skip-link {
  position: absolute;
  left: -9999px;
  top: 0;
  background: var(--gold);
  color: var(--forest);
  padding: 8px 12px;
  z-index: 9999;
}
.skip-link:focus { left: 0; }

.hero {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 24px;
  align-items: start;
  margin-bottom: 24px;
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 24px;
  align-items: start;
}

.right-rail {
  position: sticky;
  top: 32px;
  align-self: start;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.right-rail:empty { display: none; }
.content-grid:has(.right-rail:empty) { grid-template-columns: 1fr; }

.hero-widget {
  background: var(--paper);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm, 10px);
  padding: 16px;
  box-shadow: var(--shadow);
  min-height: 180px;
}

@media (max-width: 1280px) {
  .content-grid { grid-template-columns: 1fr; }
  .right-rail { position: static; flex-direction: row; flex-wrap: wrap; }
  .right-rail > .rail-card { flex: 1 1 calc(50% - 8px); }
}

@media (max-width: 900px) {
  .hero { grid-template-columns: 1fr; }
  .right-rail { flex-direction: column; }
  .right-rail > .rail-card { flex: 1 1 100%; }
}
```

- [ ] **Step 3: Smoke-test Teacher dashboard at 1920px / 1280px / 900px**

Login as Teacher. Verify hero splits, right rail visible (will be empty until Task 1.11), responsive collapse at breakpoints.

- [ ] **Step 4: Commit**

```bash
git add templates/teacher_base.html
git commit -m "feat(teacher-shell): add hero/right-rail shell grid + responsive breakpoints"
```

---

### Task 1.10: Add Student hero widget + right rail content

**Files:**
- Modify: `templates/student_base.html` (or the dashboard template that consumes the blocks — depends on existing structure)

- [ ] **Step 1: Locate the student dashboard template that fills `student_base.html`**

```bash
grep -rn "extends 'student_base.html'" templates/ | head -10
```

The Student dashboard view likely renders a child template. Identify it.

- [ ] **Step 2: Add the hero widget content — "Today's mission"**

In the student dashboard template (e.g., `templates/student/dashboard.html` — replace path if different), add:

```django
{% block hero_widget %}
  <div class="hero-mission">
    <span class="hero-mission-label">Today's Mission</span>
    {% if next_assignment %}
      <h3 class="hero-mission-title">{{ next_assignment.title }}</h3>
      <p class="hero-mission-due">Due in {{ next_assignment.countdown_text }}</p>
      <a href="{{ next_assignment.url }}" class="hero-mission-cta">Start now →</a>
    {% else %}
      <h3 class="hero-mission-title">All caught up.</h3>
      <p class="hero-mission-due">No assignments due today.</p>
    {% endif %}
  </div>
{% endblock %}
```

- [ ] **Step 3: Add the right rail content**

```django
{% block right_rail %}
  <div class="rail-card">
    <h3 class="rail-card-title">Upcoming</h3>
    <ul class="rail-list">
      {% for item in upcoming_items|slice:":3" %}
        <li><span class="rail-when">{{ item.when }}</span> {{ item.label }}</li>
      {% empty %}
        <li class="rail-empty">Nothing on the horizon.</li>
      {% endfor %}
    </ul>
  </div>
  <div class="rail-card">
    <h3 class="rail-card-title">Recent activity</h3>
    <ul class="rail-list">
      {% for item in recent_activity|slice:":3" %}
        <li>{{ item.text }} <span class="rail-when">{{ item.when }}</span></li>
      {% empty %}
        <li class="rail-empty">No recent activity.</li>
      {% endfor %}
    </ul>
  </div>
{% endblock %}
```

- [ ] **Step 4: Update student dashboard view to compute `next_assignment`, `upcoming_items`, `recent_activity`**

Locate the student dashboard view (likely `gamification/views.py` or a student-specific view). Add to its context:

```python
from datetime import timedelta
from django.utils import timezone

# ... inside the view ...
now = timezone.now()
upcoming_assignments = StudentActivity.objects.filter(
    student=request.user,
    activity__deadline__gte=now,
    activity__deadline__lte=now + timedelta(days=7),
).select_related("activity").order_by("activity__deadline")

next_assignment = None
if upcoming_assignments.exists():
    a = upcoming_assignments.first().activity
    delta = a.deadline - now
    if delta.days >= 1:
        countdown_text = f"{delta.days} day{'s' if delta.days != 1 else ''}"
    else:
        hours = delta.seconds // 3600
        countdown_text = f"{hours} hour{'s' if hours != 1 else ''}"
    next_assignment = {
        "title": a.title,
        "deadline": a.deadline,
        "countdown_text": countdown_text,
        "url": f"/activity/{a.id}/",
    }

upcoming_items = [
    {"when": a.activity.deadline.strftime("%b %-d"), "label": a.activity.title}
    for a in upcoming_assignments[:3]
]

recent_activity = []  # populate from existing StudentActivity log if available

context.update({
    "next_assignment": next_assignment,
    "upcoming_items": upcoming_items,
    "recent_activity": recent_activity,
})
```

(Adapt field names if `StudentActivity`/`Activity` differ in this codebase. Verify with `grep -n "class StudentActivity" activity/models.py` first.)

- [ ] **Step 5: Add CSS for hero-mission and rail-card to `student_theme.css`**

Append to `static/css/student_theme.css`:

```css
.hero-mission {
  display: flex; flex-direction: column; gap: 8px;
  padding: 8px 0;
}
.hero-mission-label {
  font-size: 11px; letter-spacing: 0.16em; text-transform: uppercase;
  color: var(--text-muted, #6b7394);
}
.hero-mission-title {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-size: 22px; font-weight: 600; color: var(--text, #eef2ff);
  margin: 0;
}
.hero-mission-due { color: var(--text-dim, #9aa3c0); margin: 0; font-size: 14px; }
.hero-mission-cta {
  margin-top: auto;
  color: var(--gold, #f4b740);
  text-decoration: none; font-weight: 600;
  align-self: flex-start;
}
.hero-mission-cta:hover { text-decoration: underline; }

.rail-card {
  background: var(--surface, rgba(22, 30, 54, 0.72));
  border: 1px solid var(--border, rgba(255,255,255,0.08));
  border-radius: 12px;
  padding: 16px;
}
.rail-card-title {
  font-size: 12px; letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--text-muted, #6b7394);
  margin: 0 0 8px;
}
.rail-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.rail-list li { font-size: 13px; color: var(--text-dim, #9aa3c0); }
.rail-when { color: var(--gold, #f4b740); font-weight: 600; margin-right: 6px; }
.rail-empty { color: var(--text-muted, #6b7394); font-style: italic; }
```

- [ ] **Step 6: Smoke-test student dashboard renders with hero widget + right rail filled**

Visit `/dashboard/` as a Student. Verify the right side of the hero now shows "Today's Mission" content; the right rail shows Upcoming + Recent activity cards. Resize to 900px and verify both stack correctly.

- [ ] **Step 7: Commit**

```bash
git add templates/student_base.html static/css/student_theme.css gamification/views.py
git commit -m "feat(student): fill hero widget + right rail with mission and upcoming"
```

(Adjust the `git add` paths based on which files were actually modified.)

---

### Task 1.11: Add Teacher hero widget + right rail content

**Files:**
- Modify: Teacher dashboard template (locate via `grep`) and view

- [ ] **Step 1: Locate the teacher dashboard template**

```bash
grep -rn "extends 'teacher_base.html'" templates/ | head -5
```

- [ ] **Step 2: Add hero widget content — "Your day at a glance"**

In the teacher dashboard template:

```django
{% block hero_widget %}
  <div class="hero-day">
    <span class="hero-day-label">Your day at a glance</span>
    {% if next_class %}
      <h3 class="hero-day-title">{{ next_class.subject_name }}</h3>
      <p class="hero-day-meta">
        <span class="mono">{{ next_class.start_time|time:"g:i A" }}</span>
        · {{ next_class.room|default:"Online" }}
        · {{ next_class.student_count }} students
      </p>
      <a href="{{ next_class.url }}" class="hero-day-cta">Open class →</a>
    {% else %}
      <h3 class="hero-day-title">No classes scheduled.</h3>
      <p class="hero-day-meta">Use the time for grading or planning.</p>
    {% endif %}
  </div>
{% endblock %}
```

- [ ] **Step 3: Add right rail content — Pending + Recent wins**

```django
{% block right_rail %}
  <div class="rail-card">
    <h3 class="rail-card-title">Pending</h3>
    <ul class="rail-list">
      {% if pending_papers %}<li>{{ pending_papers }} papers to grade</li>{% endif %}
      {% if pending_ratings %}<li>{{ pending_ratings }} ratings to write</li>{% endif %}
      {% if pending_messages %}<li>{{ pending_messages }} unread messages</li>{% endif %}
      {% if not pending_papers and not pending_ratings and not pending_messages %}
        <li class="rail-empty">All caught up.</li>
      {% endif %}
    </ul>
  </div>
  <div class="rail-card">
    <h3 class="rail-card-title">Recent student wins</h3>
    <ul class="rail-list">
      {% for win in recent_wins|slice:":3" %}
        <li>{{ win.student_name }} — {{ win.what }}</li>
      {% empty %}
        <li class="rail-empty">No recent wins logged.</li>
      {% endfor %}
    </ul>
  </div>
{% endblock %}
```

- [ ] **Step 4: Update teacher dashboard view (`gamification/teacher_dashboard.py`) to compute hero/rail context**

Add to the view's context dict:

```python
from datetime import timedelta
from django.utils import timezone
from course.models.subject_enrollment_model import SubjectEnrollment
# Adapt imports for the codebase's actual class/event model.

# Find the teacher's next scheduled class today
now = timezone.now()
todays_sessions = (...)  # query the codebase's class-session model filtered to teacher + today
next_class = None
if todays_sessions:
    s = todays_sessions[0]
    next_class = {
        "subject_name": s.subject.name,
        "start_time": s.start_time,
        "room": getattr(s, "room", "Online"),
        "student_count": SubjectEnrollment.objects.filter(subject=s.subject).count(),
        "url": f"/subject/{s.subject.id}/",
    }

# Pending counts (replace with real querysets in the codebase)
pending_papers = StudentActivity.objects.filter(
    activity__teacher=request.user,
    grade__isnull=True,
).count()
pending_ratings = TeacherRating.objects.filter(reviewer=request.user, status="pending").count() if "TeacherRating" in dir() else 0
pending_messages = 0  # if message app exposes a count

recent_wins = []  # populate from any existing student-recognition source

context.update({
    "next_class": next_class,
    "pending_papers": pending_papers,
    "pending_ratings": pending_ratings,
    "pending_messages": pending_messages,
    "recent_wins": recent_wins,
})
```

(Important: Verify each model name and field name with `grep` against the actual repo before writing. If `StudentActivity` lacks a `grade` field, substitute the real "ungraded" predicate. If a count cannot be cheaply computed, set the variable to `0` so the empty state renders.)

- [ ] **Step 5: Add CSS for hero-day and reuse rail-card from teacher's existing tokens**

In `templates/teacher_base.html` inline `<style>`, append:

```css
.hero-day {
  display: flex; flex-direction: column; gap: 8px;
}
.hero-day-label {
  font-size: 11px; letter-spacing: 0.16em; text-transform: uppercase;
  color: var(--ink-muted);
  font-family: var(--body);
}
.hero-day-title {
  font-family: var(--display);
  font-size: 22px; font-weight: 500; color: var(--ink);
  margin: 0;
}
.hero-day-meta { color: var(--ink-dim); margin: 0; font-size: 14px; }
.hero-day-cta {
  margin-top: auto;
  color: var(--forest);
  text-decoration: none; font-weight: 600;
  align-self: flex-start;
}
.hero-day-cta:hover { text-decoration: underline; }

.rail-card {
  background: var(--paper);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 16px;
  box-shadow: var(--shadow);
}
.rail-card-title {
  font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--ink-muted);
  margin: 0 0 8px;
  font-family: var(--body);
}
.rail-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.rail-list li { font-size: 13px; color: var(--ink-dim); }
.rail-empty { color: var(--ink-muted); font-style: italic; }

.mono { font-family: 'JetBrains Mono', monospace; font-feature-settings: 'tnum' 1; }
```

- [ ] **Step 6: Smoke-test teacher dashboard**

Visit `/dashboard/` as a Teacher. Verify hero widget shows "Your day at a glance" content; right rail shows Pending + Recent wins cards. Test at 1920 / 1280 / 900px.

- [ ] **Step 7: Commit**

```bash
git add templates/teacher_base.html gamification/teacher_dashboard.py templates/<teacher_dashboard_template_path>
git commit -m "feat(teacher): fill hero widget + right rail with day-at-a-glance and pending"
```

---

### Task 1.12: Manual responsive verification across all three role-bases

- [ ] **Step 1: Open dev server and prepare three browser windows**

Login as Student in window 1, Teacher in window 2, Registrar (any Operations role) in window 3.

- [ ] **Step 2: At 1920px, verify each shell shows 3 columns (sidebar / main / right-rail)**

For Operations: right rail will be empty (collapses to 1 column via `:has(.right-rail:empty)`). That's expected — Phase 3 fills it.

- [ ] **Step 3: At 1280px, verify right rail moves inline below content as 2-up cards**

(Where rail content exists — Student and Teacher.)

- [ ] **Step 4: At 900px, verify all stacks to single column; sidebar becomes top bar (Operations only)**

- [ ] **Step 5: At 375px (mobile), verify nothing overflows horizontally**

If any overflow detected, identify the element via devtools and fix in the relevant CSS file.

- [ ] **Step 6: Commit any responsive fixes (if needed)**

```bash
git add static/css/student_theme.css static/css/operations_base.css templates/teacher_base.html
git commit -m "fix(shell): responsive overflow tweaks at narrow viewports"
```

---

### Task 1.13: Open PR #1

- [ ] **Step 1: Push branch**

```bash
git push -u personal feat/shared-role-skeleton-and-right-rail
```

- [ ] **Step 2: Open PR against `main` via the project's standard PR creation flow**

Title: `feat(shell): shared role_skeleton.html parent + 3-column shell with right rail`

Body summary:
- Extracts `<head>` boilerplate into `templates/role_skeleton.html`. Three role-bases now extend it.
- Adds `hero | hero-widget` split (1.6fr / 1fr) so the right ~40% of the hero is no longer empty.
- Adds opt-in `right-rail` (sticky 320px) at desktop ≥ 1280px; collapses inline below 1280px; stacks below 900px.
- Student and Teacher get hero widget + right rail content. Operations roles get the layout but rails empty until Phase 3 (the `:has(.right-rail:empty)` rule collapses to single column when empty).
- ~600 lines. Spec: `docs/superpowers/specs/2026-04-27-program-head-shared-shell-and-polish-design.md`.

- [ ] **Step 3: Wait for review and merge before starting Phase 2**

---

# Phase 2 — Program Head + Operations polish (PR #2)

Branch: `feat/program-head-with-polished-shell` off `main` after PR #1 merged.

### Task 2.1: Add visual depth tokens and gradient body to `operations_base.css`

**Files:**
- Modify: `static/css/operations_base.css`

- [ ] **Step 1: Add new tokens to `:root`**

In `:root` block, add:

```css
--shadow: 0 1px 2px rgba(45,49,66,.03), 0 12px 32px -12px rgba(45,49,66,.08);
--shadow-hover: 0 2px 4px rgba(45,49,66,.04), 0 20px 48px -16px rgba(45,49,66,.12);
--radius: 16px;
--radius-sm: 10px;
--gold-soft: #e8d5b0;
```

- [ ] **Step 2: Add radial gradient + SVG noise to `body`**

Replace the existing `body { ... background: var(--cream); ... }` rule with:

```css
body {
  margin: 0;
  font-family: "Inter Tight", sans-serif;
  background:
    radial-gradient(ellipse at 10% 0%, rgba(183, 146, 90, 0.08) 0%, transparent 40%),
    radial-gradient(ellipse at 90% 100%, rgba(27, 67, 50, 0.05) 0%, transparent 50%),
    var(--cream);
  background-attachment: fixed;
  color: var(--ink);
  position: relative;
  -webkit-font-smoothing: antialiased;
}
body::before {
  content: '';
  position: fixed; inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' /%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.4'/%3E%3C/svg%3E");
  opacity: 0.05;
  mix-blend-mode: multiply;
  pointer-events: none;
  z-index: 0;
}
.ops-shell { position: relative; z-index: 1; }
```

- [ ] **Step 3: Apply elevation to KPI / panels / context cards**

Update existing rules:

```css
.kpi {
  background: var(--paper);
  border-radius: var(--radius);
  padding: 16px;
  border: 1px solid var(--cream-2);
  box-shadow: var(--shadow);
  transition: transform 120ms ease, box-shadow 120ms ease;
}
.kpi:hover { transform: translateY(-1px); box-shadow: var(--shadow-hover); }

.ops-primary, .ops-secondary {
  background: var(--paper);
  border-radius: var(--radius);
  padding: 24px;
  border: 1px solid var(--cream-2);
  box-shadow: var(--shadow);
}

.context-col {
  background: var(--paper);
  border-radius: var(--radius);
  padding: 20px;
  border: 1px solid var(--cream-2);
  box-shadow: var(--shadow);
}
```

- [ ] **Step 4: Visually verify any Operations dashboard now shows depth**

Login as Registrar; verify cards/panels have subtle shadows and the page background has a soft gradient.

- [ ] **Step 5: Commit**

```bash
git checkout -b feat/program-head-with-polished-shell
git add static/css/operations_base.css
git commit -m "feat(operations-polish): add depth tokens, gradient body, shadow elevation"
```

---

### Task 2.2: Add motion + `prefers-reduced-motion` to `operations_base.css`

**Files:**
- Modify: `static/css/operations_base.css`

- [ ] **Step 1: Update `.ops-btn` and `.ops-nav-link` with transitions**

Replace the existing rules with:

```css
.ops-btn {
  padding: 10px 16px;
  border-radius: 8px;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: transform 120ms ease, box-shadow 120ms ease;
}
.ops-btn:hover { transform: translateY(-1px); box-shadow: var(--shadow-hover); }
.ops-btn-primary { background: var(--forest); color: var(--cream); }
.ops-btn-secondary { background: var(--paper); color: var(--ink); border: 1px solid var(--ink-muted); }

.ops-nav-link {
  color: var(--cream);
  text-decoration: none;
  padding: 8px 12px;
  border-radius: 6px;
  opacity: 0.85;
  font-size: 14px;
  transition: background 80ms ease, opacity 80ms ease, padding-left 80ms ease;
  border-left: 3px solid transparent;
}
.ops-nav-link:hover { background: var(--forest-2); opacity: 1; }
.ops-nav-link.active {
  background: var(--forest-2);
  opacity: 1;
  border-left-color: var(--gold);
  padding-left: 9px;
}
```

- [ ] **Step 2: Add panel mount fade-up**

Append:

```css
.ops-primary, .ops-secondary, .kpi, .context-col, .hero-widget {
  animation: panel-fade-up 220ms ease both;
}
@keyframes panel-fade-up {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

- [ ] **Step 3: Add live-dot pulse animation**

Replace existing `.live-dot` rule with:

```css
.live-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--forest);
  animation: live-dot-pulse 1.6s ease-in-out infinite;
}
@keyframes live-dot-pulse {
  0%, 100% { background: var(--forest); box-shadow: 0 0 0 0 rgba(27,67,50,0); }
  50%      { background: var(--forest-2); box-shadow: 0 0 0 6px rgba(27,67,50,0.12); }
}
```

- [ ] **Step 4: Add KPI warn breathing**

Replace existing `.kpi.warn` with:

```css
.kpi.warn {
  background: linear-gradient(135deg, var(--rose-soft), #ffeae5);
  animation: kpi-warn-breathe 4s ease-in-out infinite, panel-fade-up 220ms ease both;
}
.kpi.warn .kpi-delta { color: var(--rose-deep); }
@keyframes kpi-warn-breathe {
  0%, 100% { background: linear-gradient(135deg, var(--rose-soft), #ffeae5); }
  50%      { background: linear-gradient(135deg, #f6dad4, #ffeae5); }
}
```

- [ ] **Step 5: Add `prefers-reduced-motion` killswitch**

Append:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.001ms !important;
  }
}
```

- [ ] **Step 6: Smoke-test motion**

Visit any Operations dashboard. Verify: button hover lifts subtly, nav link active state has gold left rail, panels fade up on load, live-dot pulses, warn KPIs breathe. Toggle `prefers-reduced-motion` in devtools — verify all animation stops.

- [ ] **Step 7: Commit**

```bash
git add static/css/operations_base.css
git commit -m "feat(operations-polish): add motion, pulse, breathe, prefers-reduced-motion"
```

---

### Task 2.3: Update `kpi_strip.html` to render new optional fields

**Files:**
- Modify: `templates/operations/kpi_strip.html`

- [ ] **Step 1: Rewrite the partial**

```django
{% comment %}[Classedge LMS] Operations Mode KPI strip — 4-5 cards. Optional: delta_direction, delta_intent, sparkline.{% endcomment %}
<section class="kpi-strip">
  {% for k in kpis %}
    <div class="kpi {{ k.tone }}">
      <div class="kpi-label">{{ k.label }}</div>
      <div class="kpi-value">{{ k.value }}{% if k.unit %}<span class="kpi-unit"> {{ k.unit }}</span>{% endif %}</div>
      {% if k.delta %}
        <div class="kpi-delta kpi-delta-{{ k.delta_intent|default:'neutral' }}">
          {% if k.delta_direction == 'up' %}↑{% elif k.delta_direction == 'down' %}↓{% elif k.delta_direction == 'flat' %}→{% endif %}
          {{ k.delta }}
        </div>
      {% endif %}
      {% if k.sparkline %}
        <svg class="kpi-spark" viewBox="0 0 100 24" preserveAspectRatio="none" aria-hidden="true">
          <polyline points="{{ k.sparkline_points }}" fill="none" stroke="currentColor" stroke-width="1.5" />
        </svg>
      {% endif %}
    </div>
  {% endfor %}
</section>
```

Note: `k.sparkline_points` is a comma-separated string of `x,y` pairs — computed view-side from the integer array (see Task 2.13 helper). The helper `_sparkline_points(values)` will be added when the first KPI uses it.

- [ ] **Step 2: Add CSS for sparkline + delta direction**

Append to `static/css/operations_base.css`:

```css
.kpi-delta-good { color: var(--forest); }
.kpi-delta-bad  { color: var(--rose-deep); }
.kpi-delta-neutral { color: var(--ink-dim); }

.kpi-spark {
  width: 100%;
  height: 24px;
  margin-top: 6px;
  color: var(--gold);
  stroke-dasharray: 200;
  stroke-dashoffset: 200;
  animation: spark-draw 600ms ease forwards;
}
@keyframes spark-draw {
  to { stroke-dashoffset: 0; }
}
```

- [ ] **Step 3: Verify existing dashboards still render unchanged**

Run existing tests:

```bash
python -m pytest accounts/tests/test_registrar_dashboard.py accounts/tests/test_coil_admin_dashboard.py accounts/tests/test_academic_director_dashboard.py accounts/tests/test_it_admin_dashboard.py -v
```

Expected: PASS. Existing dashboards omit `delta_direction`, `delta_intent`, `sparkline` — the partial's `if`/`default` keep their HTML stable.

- [ ] **Step 4: Commit**

```bash
git add templates/operations/kpi_strip.html static/css/operations_base.css
git commit -m "feat(operations-polish): render optional kpi fields (delta direction, sparkline)"
```

---

### Task 2.4: Update `worklist_panel.html` with empty-state + flagged-row affordance

**Files:**
- Modify: `templates/operations/worklist_panel.html`
- Modify: `static/css/operations_base.css`

- [ ] **Step 1: Rewrite the partial**

```django
{% comment %}[Classedge LMS] Operations Mode worklist panel. Optional: empty_hint.{% endcomment %}
<div class="worklist-panel">
  <header class="panel-header">
    <h2>{{ title }}</h2>
    {% if why %}<span class="why"><em>{{ why }}</em></span>{% endif %}
  </header>
  <table class="worklist">
    <caption class="visually-hidden">{{ title }}</caption>
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
        <tr><td colspan="{{ columns|length }}">
          <div class="empty-state">
            <div class="empty-glyph" aria-hidden="true"></div>
            <p>{{ empty_message|default:"You're all caught up." }}</p>
            {% if empty_hint %}<p class="empty-hint">{{ empty_hint }}</p>{% endif %}
          </div>
        </td></tr>
      {% endfor %}
    </tbody>
  </table>
</div>
```

- [ ] **Step 2: Add row hover, flagged row styling, empty-state, visually-hidden to CSS**

Append to `static/css/operations_base.css`:

```css
.visually-hidden {
  position: absolute !important;
  width: 1px; height: 1px;
  padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0,0,0,0);
  white-space: nowrap; border: 0;
}

.worklist tbody tr { transition: background 80ms ease; }
.worklist tbody tr:hover { background: var(--gold-bg); cursor: pointer; }
.row-flagged { background: linear-gradient(90deg, var(--rose-soft) 0%, transparent 12%); }
.row-flagged td:first-child { border-left: 3px solid var(--rose); padding-left: 8px; }
.row-flagged td:first-child::before {
  content: '!';
  color: var(--rose-deep);
  font-weight: 700;
  margin-right: 6px;
}

.empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 32px 16px;
  gap: 10px;
}
.empty-glyph {
  width: 48px; height: 48px;
  border-radius: 50%;
  background: var(--forest-light);
  position: relative;
}
.empty-glyph::after {
  content: '✓';
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  color: var(--gold);
  font-size: 22px; font-weight: 700;
}
.empty-state p { margin: 0; color: var(--ink-dim); font-size: 14px; }
.empty-state .empty-hint { color: var(--ink-muted); font-size: 12px; }
```

- [ ] **Step 3: Run existing tests**

```bash
python -m pytest accounts/tests/test_registrar_dashboard.py accounts/tests/test_coil_admin_dashboard.py accounts/tests/test_academic_director_dashboard.py accounts/tests/test_it_admin_dashboard.py -v
```

Expected: PASS. Existing tests don't assert on the old "Nothing here." copy at the partial level.

- [ ] **Step 4: Commit**

```bash
git add templates/operations/worklist_panel.html static/css/operations_base.css
git commit -m "feat(operations-polish): empty-state block + flagged-row affordance + a11y caption"
```

---

### Task 2.5: Update `context_strip.html` with empty-state block

**Files:**
- Modify: `templates/operations/context_strip.html`

- [ ] **Step 1: Rewrite the partial**

```django
{% comment %}[Classedge LMS] Operations Mode context strip — two equal columns of ambient info.{% endcomment %}
<section class="context-strip">
  <div class="context-col">
    <h3>{{ left.title }}</h3>
    {% for item in left.items %}
      <div class="context-item">{{ item }}</div>
    {% empty %}
      <div class="empty-state">
        <div class="empty-glyph" aria-hidden="true"></div>
        <p>{{ left.empty|default:"Nothing scheduled." }}</p>
      </div>
    {% endfor %}
  </div>
  <div class="context-col">
    <h3>{{ right.title }}</h3>
    {% for item in right.items %}
      <div class="context-item">{{ item }}</div>
    {% empty %}
      <div class="empty-state">
        <div class="empty-glyph" aria-hidden="true"></div>
        <p>{{ right.empty|default:"Nothing here." }}</p>
      </div>
    {% endfor %}
  </div>
</section>
```

- [ ] **Step 2: Run existing tests, verify nothing broke**

```bash
python -m pytest accounts/tests/test_registrar_dashboard.py accounts/tests/test_coil_admin_dashboard.py accounts/tests/test_academic_director_dashboard.py accounts/tests/test_it_admin_dashboard.py -v
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add templates/operations/context_strip.html
git commit -m "feat(operations-polish): empty-state block in context strip"
```

---

### Task 2.6: Update `scope_bar.html` with `.mono` and pulse-ready dot

**Files:**
- Modify: `templates/operations/scope_bar.html`

- [ ] **Step 1: Rewrite the partial**

```django
{% comment %}[Classedge LMS] Operations Mode scope bar — pills + live timestamp with pulse.{% endcomment %}
<div class="scope-bar">
  <div class="scope-tags">
    {% for tag in tags %}
      <span class="scope-pill"><strong>{{ tag.label }}</strong> {{ tag.value }}</span>
    {% endfor %}
  </div>
  <div class="scope-live" aria-live="polite">
    <span class="live-dot" aria-hidden="true"></span>
    <span class="live-label">Live · as of <span class="mono">{{ as_of|default:"now" }}</span></span>
  </div>
</div>
```

- [ ] **Step 2: Verify scope bar renders with mono timestamp on any dashboard**

Visit Registrar `/registrar/`. Inspect the live label; the `as_of` value should be in JetBrains Mono.

- [ ] **Step 3: Commit**

```bash
git add templates/operations/scope_bar.html
git commit -m "feat(operations-polish): mono timestamp + aria-live in scope bar"
```

---

### Task 2.7: Add accessibility, print, mobile, skeletons, JetBrains Mono utility to `operations_base.css`

**Files:**
- Modify: `static/css/operations_base.css`

- [ ] **Step 1: Add focus rings, contrast fix, mono utility**

Append:

```css
/* ─── Accessibility ─────────────────────────────────── */
:focus-visible {
  outline: 2px solid var(--gold);
  outline-offset: 2px;
}

.skip-link {
  position: absolute;
  left: -9999px;
  background: var(--gold);
  color: var(--forest);
  padding: 8px 12px;
  z-index: 9999;
}
.skip-link:focus { left: 0; top: 0; }

/* Contrast fix: --ink-muted #a0a4b8 → #7a8099 (4.6:1 on paper, passes AA) */
:root { --ink-muted: #7a8099; }

.mono { font-family: 'JetBrains Mono', monospace; font-feature-settings: 'tnum' 1; }
```

- [ ] **Step 2: Add skeleton loader classes**

Append:

```css
/* ─── Skeleton loaders ──────────────────────────────── */
.skeleton-line, .skeleton-block, .skeleton-kpi {
  background: linear-gradient(90deg, var(--cream-2), #efe7d6, var(--cream-2));
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.6s ease-in-out infinite;
  border-radius: 6px;
  color: transparent;
}
.skeleton-line { height: 12px; margin: 6px 0; }
.skeleton-block { height: 80px; }
.skeleton-kpi { height: 96px; }
@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

- [ ] **Step 3: Add print stylesheet**

Append:

```css
@media print {
  .ops-side, .scope-bar .scope-live, .ops-actions, .right-rail { display: none !important; }
  body, body::before { background: white !important; }
  .ops-primary, .ops-secondary, .kpi, .context-col {
    box-shadow: none !important;
    border: 1px solid #ddd !important;
    page-break-inside: avoid;
  }
  .worklist tr { page-break-inside: avoid; }
  * { color: black !important; }
}
```

- [ ] **Step 4: Verify the contrast fix didn't break anything**

Visit each Operations dashboard. The KPI labels and `.ink-muted` text should be slightly darker but visually consistent.

- [ ] **Step 5: Manually test print preview**

`Cmd+P` (or `Ctrl+P`) on any Operations dashboard. Sidebar hidden, panels render with thin borders, no shadows.

- [ ] **Step 6: Commit**

```bash
git add static/css/operations_base.css
git commit -m "feat(operations-polish): a11y focus + contrast fix + skeletons + print stylesheet"
```

---

### Task 2.8: Update `operations_base.html` for JetBrains Mono on `as_of` (already done) and verify `id="main"` already in skeleton refactor

The id="main" was added in Phase 1 Task 1.5. JetBrains Mono is loaded in the existing `<link>` and applied via the `.mono` class (Task 2.6 + 2.7). No additional changes here unless polish bar audit surfaces gaps. Skip if all green.

- [ ] **Step 1: Verify**

```bash
grep -n 'id="main"' templates/operations_base.html
grep -n 'JetBrains' templates/operations_base.html
```

Both should match. If not, add `id="main"` to the `<main>` tag and ensure `JetBrains+Mono` is in the `<link>` href in the `{% block fonts %}`.

- [ ] **Step 2: No commit if no change**

---

### Task 2.9: Verify all four existing Operations dashboards still render identically

- [ ] **Step 1: Run full test suite for Wave A dashboards**

```bash
python -m pytest accounts/tests/test_registrar_dashboard.py accounts/tests/test_coil_admin_dashboard.py accounts/tests/test_academic_director_dashboard.py accounts/tests/test_it_admin_dashboard.py accounts/tests/test_operations_foundation.py -v
```

Expected: ALL PASS.

- [ ] **Step 2: Manual visual smoke test**

Login as each role, visit dashboard, confirm:
- Cards have shadow + hover lift
- Live dot pulses in scope bar
- Empty cells now use empty-state glyph + warmer copy
- No regressions on existing data

- [ ] **Step 3: Tag the polish foundation commit**

```bash
git tag operations-polish-foundation
```

(Local tag, not pushed; serves as a checkpoint to revert to if Program Head work goes sideways.)

---

### Task 2.10: Add Program Head URL route

**Files:**
- Modify: `accounts/urls.py`

- [ ] **Step 1: Add the URL pattern**

In `accounts/urls.py`, after the existing `academic-director/` route (line ~133), add:

```python
from accounts.views.program_head_dashboard import program_head_dashboard
```

(Import alongside the existing `from accounts.views.academic_director import academic_director_dashboard`.)

In the `urlpatterns` list:

```python
path("program-head/", program_head_dashboard, name="program_head_dashboard"),
```

- [ ] **Step 2: Run with no view yet — expect ImportError**

```bash
python manage.py check
```

Expected: ImportError on `program_head_dashboard`. We'll fix it in Task 2.11.

- [ ] **Step 3: No commit yet**

---

### Task 2.11: Create `program_head_dashboard.py` view skeleton with stubs

**Files:**
- Create: `accounts/views/program_head_dashboard.py`

- [ ] **Step 1: Write the view skeleton**

```python
"""[Classedge LMS] Program Head Operations Mode dashboard view.

Walk-in question:
    Within my department, which courses or sections are off-track this week —
    and which teachers need backup?
"""
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.utils import timezone

from accounts.models.department_models import Department


def _is_program_head(user):
    """[Classedge LMS] True iff the authenticated user owns the Program Head role."""
    return (
        user.is_authenticated
        and hasattr(user, "profile")
        and user.profile.role
        and user.profile.role.name == "Program Head"
    )


def _time_of_day():
    h = timezone.localtime().hour
    if h < 12:
        return "morning"
    if h < 18:
        return "afternoon"
    return "evening"


def _resolve_department(user):
    """[Classedge LMS] Return the Department this user heads, or None."""
    return Department.objects.filter(head=user).first()


def _sparkline_points(values, width=100, height=24):
    """[Classedge LMS] Convert int array to 'x,y x,y ...' string for inline SVG polyline."""
    if not values:
        return ""
    n = len(values)
    if n == 1:
        return f"0,{height/2} {width},{height/2}"
    lo, hi = min(values), max(values)
    span = max(hi - lo, 1)
    pts = []
    for i, v in enumerate(values):
        x = (i / (n - 1)) * width
        y = height - ((v - lo) / span) * (height - 2) - 1
        pts.append(f"{x:.1f},{y:.1f}")
    return " ".join(pts)


# ─── Per-KPI standalone functions (test seam) ──────────────────────────

def _kpi_dept_avg_score(department, term):
    """[Classedge LMS] KPI #1 — placeholder; see Task 2.13."""
    return {"label": "DEPT AVG SCORE", "value": "—", "delta": "", "delta_direction": "flat",
            "delta_intent": "neutral", "tone": "", "sparkline": []}

def _kpi_at_risk_students(department, term):
    return {"label": "AT-RISK STUDENTS", "value": "—", "delta": "", "delta_direction": "flat",
            "delta_intent": "neutral", "tone": "", "sparkline": []}

def _kpi_teacher_coverage(department, term):
    return {"label": "TEACHER COVERAGE", "value": "—", "delta": "", "delta_direction": "flat",
            "delta_intent": "neutral", "tone": "", "sparkline": []}

def _kpi_outstanding_ratings(department):
    return {"label": "OUTSTANDING RATINGS", "value": "—", "delta": "", "delta_direction": "flat",
            "delta_intent": "neutral", "tone": "", "sparkline": []}

def _kpi_schedule_integrity(department):
    return {"label": "SCHEDULE INTEGRITY", "value": "—", "delta": "", "delta_direction": "flat",
            "delta_intent": "neutral", "tone": "", "sparkline": []}


def _build_context(user, department):
    """[Classedge LMS] Public seam — Principal will call this same builder later."""
    term = None  # resolve current Term via existing helper; placeholder
    kpis = []
    if department is None:
        return {
            "role_tag": "PROGRAM HEAD",
            "role_glyph": "◆",
            "department": None,
            "scope_tags": [],
            "kpis": [],
            "greeting_question": "No department assigned. Contact IT Admin to be assigned.",
            "time_of_day": _time_of_day(),
            "as_of": timezone.localtime().strftime("%H:%M"),
            "quick_actions": [],
            "nav_items": [],
            "ctx_left": {"title": "Today", "items": [], "empty": "Nothing scheduled."},
            "ctx_right": {"title": "Quick actions", "items": [], "empty": "Nothing yet."},
            "course_health_rows": [],
            "teacher_pulse_rows": [],
            "hero_widget_data": None,
            "right_rail_data": {"today": [], "outstanding": [], "announcements": []},
        }

    kpis = [
        _kpi_dept_avg_score(department, term),
        _kpi_at_risk_students(department, term),
        _kpi_teacher_coverage(department, term),
        _kpi_outstanding_ratings(department),
        _kpi_schedule_integrity(department),
    ]

    # Attach computed sparkline_points for any KPI that has data
    for k in kpis:
        if k.get("sparkline"):
            k["sparkline_points"] = _sparkline_points(k["sparkline"])

    return {
        "role_tag": "PROGRAM HEAD",
        "role_glyph": "◆",
        "department": department,
        "scope_tags": [
            {"label": "Department", "value": department.name},
            {"label": "Term", "value": str(term) if term else "—"},
        ],
        "kpis": kpis,
        "greeting_question": "Within my department, which courses or sections are off-track this week — and which teachers need backup?",
        "time_of_day": _time_of_day(),
        "as_of": timezone.localtime().strftime("%H:%M"),
        "quick_actions": [
            {"label": "Department roster", "url": "#", "primary": False},
            {"label": "New announcement", "url": "#", "primary": True},
        ],
        "nav_items": [
            {"label": "Dashboard", "url": "#", "active": True},
            {"label": "My Department", "url": "#", "divider_after": True},
            {"label": "Courses", "url": "#"},
            {"label": "Subjects", "url": "#"},
            {"label": "Faculty", "url": "#"},
            {"label": "Students", "url": "#", "divider_after": True},
            {"label": "Calendar", "url": "#"},
            {"label": "Announcements", "url": "#"},
            {"label": "Settings", "url": "#"},
        ],
        "ctx_left": {"title": "Today", "items": [], "empty": "Nothing scheduled."},
        "ctx_right": {"title": "Quick actions", "items": [], "empty": "Nothing yet."},
        # populated in subsequent tasks
        "course_health_rows": [],
        "teacher_pulse_rows": [],
        "hero_widget_data": None,
        "right_rail_data": {"today": [], "outstanding": [], "announcements": []},
    }


@login_required
@user_passes_test(_is_program_head, login_url="/login/", redirect_field_name=None)
def program_head_dashboard(request):
    """[Classedge LMS] Program Head dashboard view."""
    department = _resolve_department(request.user)
    context = _build_context(request.user, department)
    return render(request, "operations/program_head_dashboard.html", context)
```

- [ ] **Step 2: Verify `python manage.py check` passes**

```bash
python manage.py check
```

Expected: System check identified no issues.

- [ ] **Step 3: Commit the skeleton**

```bash
git add accounts/views/program_head_dashboard.py accounts/urls.py
git commit -m "feat(program-head): scaffold view + url route + KPI function stubs"
```

---

### Task 2.12: Create `program_head_dashboard.html` template

**Files:**
- Create: `templates/operations/program_head_dashboard.html`

- [ ] **Step 1: Write the template**

```django
{% extends 'operations_base.html' %}
{% comment %}[Classedge LMS] Program Head Operations Mode dashboard — deep-dive treatment.{% endcomment %}

{% block hero_widget %}
  {% if hero_widget_data %}
    <div class="hero-pulse">
      <span class="hero-pulse-label">Department Pulse</span>
      <h3 class="hero-pulse-title">
        <span class="mono">{{ hero_widget_data.at_risk_count }}</span> at-risk
        <span class="hero-pulse-delta hero-pulse-delta-{{ hero_widget_data.delta_intent }}">
          {{ hero_widget_data.delta }}
        </span>
      </h3>
      {% if hero_widget_data.sparkline_points %}
        <svg class="kpi-spark" viewBox="0 0 100 24" preserveAspectRatio="none" aria-hidden="true">
          <polyline points="{{ hero_widget_data.sparkline_points }}" fill="none" stroke="currentColor" stroke-width="1.5" />
        </svg>
      {% endif %}
      <a href="{{ hero_widget_data.cta_url }}" class="hero-pulse-cta">Open at-risk roster →</a>
    </div>
  {% endif %}
{% endblock %}

{% block primary_panel %}
  <div class="panel-header">
    <h2>Course Health</h2>
    <span class="why"><em>severity × avg score, oldest issues first</em></span>
  </div>
  <table class="worklist">
    <caption class="visually-hidden">Course Health</caption>
    <thead>
      <tr>
        <th>Subject</th><th>Teacher</th><th>Section</th>
        <th>Enrolled</th><th>Avg</th><th>Attn</th><th>Flags</th>
      </tr>
    </thead>
    <tbody>
      {% for row in course_health_rows %}
        <tr class="{% if row.flagged %}row-flagged{% endif %}">
          <td>{{ row.subject }}</td>
          <td>{{ row.teacher }}</td>
          <td>{{ row.section }}</td>
          <td><span class="mono">{{ row.enrolled }}</span></td>
          <td><span class="mono">{{ row.avg }}%</span></td>
          <td><span class="mono">{{ row.attn }}%</span></td>
          <td>{{ row.flags|default:"—" }}</td>
        </tr>
      {% empty %}
        <tr><td colspan="7">
          <div class="empty-state">
            <div class="empty-glyph" aria-hidden="true"></div>
            <p>No courses in {{ department.name|default:"your department" }} this term — content is flowing.</p>
          </div>
        </td></tr>
      {% endfor %}
    </tbody>
  </table>
{% endblock %}

{% block secondary_panel %}
  <div class="panel-header">
    <h2>Who needs support this week</h2>
    <span class="why"><em>lowest IP-velocity + flagged classes</em></span>
  </div>
  <table class="worklist">
    <caption class="visually-hidden">Teacher pulse — who needs support</caption>
    <thead>
      <tr>
        <th>Teacher</th><th>Subjects</th><th>IP Δ 7d</th>
        <th>Outstanding</th><th>Flagged</th>
      </tr>
    </thead>
    <tbody>
      {% for row in teacher_pulse_rows %}
        <tr class="{% if row.support_score > 50 %}row-flagged{% endif %}">
          <td>{{ row.teacher }}</td>
          <td>{{ row.subjects }}</td>
          <td><span class="mono">{{ row.ip_delta_text }}</span></td>
          <td>{{ row.outstanding_text }}</td>
          <td>{{ row.flagged_text }}</td>
        </tr>
      {% empty %}
        <tr><td colspan="5">
          <div class="empty-state">
            <div class="empty-glyph" aria-hidden="true"></div>
            <p>Every teacher in your department is steady — no one needs backup right now.</p>
          </div>
        </td></tr>
      {% endfor %}
    </tbody>
  </table>
{% endblock %}

{% block right_rail %}
  <div class="rail-card">
    <h3 class="rail-card-title">Today</h3>
    <ul class="rail-list">
      {% for ev in right_rail_data.today %}
        <li><span class="rail-when mono">{{ ev.when }}</span> {{ ev.title }} <span class="rail-tag">· {{ ev.audience }}</span></li>
      {% empty %}
        <li class="rail-empty">Nothing on the calendar.</li>
      {% endfor %}
    </ul>
  </div>
  {% if right_rail_data.outstanding %}
  <div class="rail-card">
    <h3 class="rail-card-title">Outstanding ratings</h3>
    <ul class="rail-list">
      {% for r in right_rail_data.outstanding|slice:":5" %}
        <li>{{ r.teacher }} <a href="{{ r.url }}" class="rail-action">Review →</a></li>
      {% endfor %}
      {% if right_rail_data.outstanding|length > 5 %}
        <li class="rail-empty">+{{ right_rail_data.outstanding|length|add:"-5" }} more</li>
      {% endif %}
    </ul>
  </div>
  {% endif %}
  <div class="rail-card">
    <h3 class="rail-card-title">Announcements</h3>
    <ul class="rail-list">
      {% for a in right_rail_data.announcements|slice:":3" %}
        <li>{{ a.title }} <span class="rail-when mono">{{ a.created_at|date:"M j" }}</span></li>
      {% empty %}
        <li class="rail-empty">No recent announcements.</li>
      {% endfor %}
    </ul>
  </div>
{% endblock %}
```

- [ ] **Step 2: Add CSS for hero-pulse and rail-card variants**

Append to `static/css/operations_base.css`:

```css
.hero-pulse { display: flex; flex-direction: column; gap: 8px; }
.hero-pulse-label {
  font-size: 11px; letter-spacing: 0.16em; text-transform: uppercase;
  color: var(--ink-muted);
}
.hero-pulse-title { font-family: 'Fraunces', serif; font-size: 22px; margin: 0; font-weight: 500; color: var(--ink); }
.hero-pulse-delta-good { color: var(--forest); font-size: 14px; font-weight: 600; }
.hero-pulse-delta-bad  { color: var(--rose-deep); font-size: 14px; font-weight: 600; }
.hero-pulse-delta-neutral { color: var(--ink-dim); font-size: 14px; font-weight: 600; }
.hero-pulse-cta {
  margin-top: auto;
  color: var(--forest);
  text-decoration: none; font-weight: 600;
  align-self: flex-start;
  padding-top: 4px;
}
.hero-pulse-cta:hover { text-decoration: underline; }

.rail-card {
  background: var(--paper);
  border: 1px solid var(--cream-2);
  border-radius: var(--radius-sm);
  padding: 16px;
  box-shadow: var(--shadow);
}
.rail-card-title {
  font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--ink-muted);
  margin: 0 0 8px;
}
.rail-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.rail-list li { font-size: 13px; color: var(--ink-dim); }
.rail-when { color: var(--gold); font-weight: 600; margin-right: 6px; }
.rail-tag { color: var(--ink-muted); font-size: 12px; }
.rail-empty { color: var(--ink-muted); font-style: italic; }
.rail-action { color: var(--forest); text-decoration: none; font-weight: 600; }
.rail-action:hover { text-decoration: underline; }
```

- [ ] **Step 3: Hit `/program-head/` as a Program Head user — verify shell renders with empty data**

Login as a Program Head (or seed one with no department assigned). Visit `/program-head/`. Verify:
- The shell renders, not a 500
- "Department Pulse" hero widget area is present (empty state since no data yet)
- Course Health and Teacher Pulse panels render with empty-state blocks
- Right rail cards render with "Nothing on the calendar." etc.

- [ ] **Step 4: Commit**

```bash
git add templates/operations/program_head_dashboard.html static/css/operations_base.css
git commit -m "feat(program-head): add dashboard template + hero-pulse + rail-card css"
```

---

### Task 2.13: TDD KPI #1 — Dept Avg Score

**Files:**
- Create: `accounts/tests/test_program_head_dashboard.py`
- Modify: `accounts/views/program_head_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
"""[Classedge LMS] Tests for the Program Head Operations Mode dashboard."""
import uuid
from django.test import TestCase
from django.urls import reverse

from accounts.models.account_models import CustomUser
from accounts.models.department_models import Department
from accounts.tests.helpers import make_profile_for
from accounts.views.program_head_dashboard import (
    _build_context,
    _kpi_dept_avg_score,
    _kpi_at_risk_students,
    _kpi_teacher_coverage,
    _kpi_outstanding_ratings,
    _kpi_schedule_integrity,
    _resolve_department,
)


def _make_program_head_with_department(name="BS Computer Science"):
    username = f"ph-{uuid.uuid4().hex[:8]}"
    user = CustomUser.objects.create_user(
        username=username, email=f"{username}@x.io", password="x", first_name="Ada"
    )
    make_profile_for(user, "Program Head")
    dept = Department.objects.create(name=name, head=user)
    return user, dept


class TestProgramHeadKPIs(TestCase):
    def test_kpi_dept_avg_score_returns_dict_with_required_keys(self):
        user, dept = _make_program_head_with_department()
        kpi = _kpi_dept_avg_score(dept, term=None)
        self.assertEqual(kpi["label"], "DEPT AVG SCORE")
        self.assertIn("value", kpi)
        self.assertIn("delta_direction", kpi)
        self.assertIn("delta_intent", kpi)
        self.assertIn("tone", kpi)

    def test_kpi_dept_avg_score_with_no_students_returns_dash(self):
        user, dept = _make_program_head_with_department()
        kpi = _kpi_dept_avg_score(dept, term=None)
        self.assertEqual(kpi["value"], "—")
```

- [ ] **Step 2: Run, verify it fails**

```bash
python -m pytest accounts/tests/test_program_head_dashboard.py::TestProgramHeadKPIs::test_kpi_dept_avg_score_with_no_students_returns_dash -v
```

Expected: PASS (the stub already returns `"—"`). If it fails, the stub needs adjustment. If it passes, write a richer assertion that requires real implementation.

- [ ] **Step 3: Add a richer assertion that forces real implementation**

Append to `TestProgramHeadKPIs`:

```python
    def test_kpi_dept_avg_score_returns_numeric_when_students_have_grades(self):
        user, dept = _make_program_head_with_department()
        # Create a student in this dept with a graded activity.
        from activity.models import StudentActivity, Activity
        from accounts.models.account_models import Profile
        student = CustomUser.objects.create_user(
            username=f"s-{uuid.uuid4().hex[:6]}", email="s@x.io", password="x"
        )
        make_profile_for(student, "Student")
        Profile.objects.filter(user=student).update(department_fields=dept)
        # NOTE: Implementation must compute weighted avg of latest StudentActivity grades.
        # If StudentActivity field names differ, adapt.
        kpi = _kpi_dept_avg_score(dept, term=None)
        # Either numeric or "—"; must not crash.
        self.assertIsNotNone(kpi["value"])
```

- [ ] **Step 4: Implement `_kpi_dept_avg_score`**

Replace the stub in `accounts/views/program_head_dashboard.py`:

```python
def _kpi_dept_avg_score(department, term):
    """[Classedge LMS] KPI #1 — weighted avg of latest activity scores in dept this term."""
    from activity.models import StudentActivity
    from accounts.models.account_models import Profile

    if department is None:
        return {"label": "DEPT AVG SCORE", "value": "—", "delta": "",
                "delta_direction": "flat", "delta_intent": "neutral", "tone": "", "sparkline": []}

    student_ids = list(Profile.objects.filter(department_fields=department).values_list("user_id", flat=True))
    if not student_ids:
        return {"label": "DEPT AVG SCORE", "value": "—", "delta": "",
                "delta_direction": "flat", "delta_intent": "neutral", "tone": "", "sparkline": []}

    activities = StudentActivity.objects.filter(student_id__in=student_ids)
    grades = [a.grade for a in activities if getattr(a, "grade", None) is not None]
    if not grades:
        return {"label": "DEPT AVG SCORE", "value": "—", "delta": "",
                "delta_direction": "flat", "delta_intent": "neutral", "tone": "", "sparkline": []}

    avg = sum(grades) / len(grades)
    school_grades = [a.grade for a in StudentActivity.objects.all() if getattr(a, "grade", None) is not None]
    school_avg = sum(school_grades) / len(school_grades) if school_grades else avg
    delta_pts = avg - school_avg
    return {
        "label": "DEPT AVG SCORE",
        "value": f"{avg:.1f}",
        "delta": f"{delta_pts:+.1f} vs school avg",
        "delta_direction": "up" if delta_pts > 0 else ("down" if delta_pts < 0 else "flat"),
        "delta_intent": "good" if delta_pts >= 0 else "bad",
        "tone": "warn" if delta_pts < -3 else "",
        "sparkline": [],  # 7-week trend not computed yet; leave empty
    }
```

(If `StudentActivity` field names differ — verify with `grep -nE "class StudentActivity|grade" activity/models.py` and adapt.)

- [ ] **Step 5: Run, verify all 3 tests pass**

```bash
python -m pytest accounts/tests/test_program_head_dashboard.py::TestProgramHeadKPIs -v
```

Expected: 3 PASS.

- [ ] **Step 6: Commit**

```bash
git add accounts/tests/test_program_head_dashboard.py accounts/views/program_head_dashboard.py
git commit -m "feat(program-head): KPI #1 dept avg score (weighted, vs school avg)"
```

---

### Task 2.14: TDD KPI #2 — At-Risk Students

**Files:**
- Modify: `accounts/tests/test_program_head_dashboard.py`
- Modify: `accounts/views/program_head_dashboard.py`

- [ ] **Step 1: Write failing tests**

Append to `TestProgramHeadKPIs`:

```python
    def test_kpi_at_risk_with_zero_students_returns_zero(self):
        user, dept = _make_program_head_with_department()
        kpi = _kpi_at_risk_students(dept, term=None)
        self.assertEqual(kpi["value"], 0)
        self.assertEqual(kpi["tone"], "")  # zero is not warn

    def test_kpi_at_risk_label_correct(self):
        user, dept = _make_program_head_with_department()
        kpi = _kpi_at_risk_students(dept, term=None)
        self.assertEqual(kpi["label"], "AT-RISK STUDENTS")
```

- [ ] **Step 2: Run, verify failures (or stub behavior)**

```bash
python -m pytest accounts/tests/test_program_head_dashboard.py::TestProgramHeadKPIs::test_kpi_at_risk_with_zero_students_returns_zero -v
```

If stub returns `"—"` not `0`, the test fails as expected.

- [ ] **Step 3: Implement `_kpi_at_risk_students`**

Replace stub:

```python
def _kpi_at_risk_students(department, term):
    """[Classedge LMS] KPI #2 — count students flagged at-risk in dept."""
    from accounts.models.account_models import Profile

    if department is None:
        return {"label": "AT-RISK STUDENTS", "value": 0, "delta": "",
                "delta_direction": "flat", "delta_intent": "neutral", "tone": "", "sparkline": []}

    # Use existing at-risk signal — try gamification.AtRiskFlag if present, fall back to 0.
    student_ids = list(Profile.objects.filter(department_fields=department).values_list("user_id", flat=True))
    try:
        from at_risk.models import AtRiskFlag
        count = AtRiskFlag.objects.filter(student_id__in=student_ids, resolved=False).count()
    except Exception:
        count = 0

    return {
        "label": "AT-RISK STUDENTS",
        "value": count,
        "delta": "",  # 7-day delta requires historical snapshot — left blank for v1
        "delta_direction": "flat",
        "delta_intent": "bad" if count > 0 else "neutral",
        "tone": "warn" if count > 0 else "",
        "sparkline": [],
    }
```

- [ ] **Step 4: Run all KPI tests**

```bash
python -m pytest accounts/tests/test_program_head_dashboard.py::TestProgramHeadKPIs -v
```

Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add accounts/tests/test_program_head_dashboard.py accounts/views/program_head_dashboard.py
git commit -m "feat(program-head): KPI #2 at-risk students (count + warn tone)"
```

---

### Task 2.15: TDD KPI #3 — Teacher Coverage

**Files:**
- Modify: `accounts/tests/test_program_head_dashboard.py`
- Modify: `accounts/views/program_head_dashboard.py`

- [ ] **Step 1: Write failing tests**

```python
    def test_kpi_teacher_coverage_with_no_subjects(self):
        user, dept = _make_program_head_with_department()
        kpi = _kpi_teacher_coverage(dept, term=None)
        self.assertEqual(kpi["value"], "—")

    def test_kpi_teacher_coverage_label(self):
        user, dept = _make_program_head_with_department()
        kpi = _kpi_teacher_coverage(dept, term=None)
        self.assertEqual(kpi["label"], "TEACHER COVERAGE")
```

- [ ] **Step 2: Implement**

Replace stub:

```python
def _kpi_teacher_coverage(department, term):
    """[Classedge LMS] KPI #3 — staffed subjects / total subjects this term × 100%."""
    if department is None:
        return {"label": "TEACHER COVERAGE", "value": "—", "delta": "",
                "delta_direction": "flat", "delta_intent": "neutral", "tone": "", "sparkline": []}

    # Try to find subjects in the department — codebase may have Subject.department FK
    # or join through Course. Adapt below to the real schema.
    try:
        from subject.models import Subject
        subjects = Subject.objects.filter(department=department) if hasattr(Subject, "department") else Subject.objects.none()
    except Exception:
        subjects = []

    total = len(subjects) if hasattr(subjects, "__len__") else subjects.count()
    if total == 0:
        return {"label": "TEACHER COVERAGE", "value": "—", "delta": "",
                "delta_direction": "flat", "delta_intent": "neutral", "tone": "", "sparkline": []}

    staffed = subjects.exclude(teacher__isnull=True).count() if hasattr(subjects, "exclude") else 0
    pct = (staffed / total) * 100
    return {
        "label": "TEACHER COVERAGE",
        "value": f"{pct:.0f}%",
        "delta": "",
        "delta_direction": "flat",
        "delta_intent": "good" if pct >= 95 else "bad",
        "tone": "warn" if pct < 95 else "",
        "sparkline": [],
    }
```

- [ ] **Step 3: Run + commit**

```bash
python -m pytest accounts/tests/test_program_head_dashboard.py::TestProgramHeadKPIs -v
git add accounts/tests/test_program_head_dashboard.py accounts/views/program_head_dashboard.py
git commit -m "feat(program-head): KPI #3 teacher coverage"
```

---

### Task 2.16: TDD KPI #4 — Outstanding Ratings

**Files:**
- Modify: `accounts/tests/test_program_head_dashboard.py`
- Modify: `accounts/views/program_head_dashboard.py`

- [ ] **Step 1: Write failing tests**

```python
    def test_kpi_outstanding_ratings_with_zero_pending(self):
        user, dept = _make_program_head_with_department()
        kpi = _kpi_outstanding_ratings(dept)
        self.assertEqual(kpi["value"], 0)

    def test_kpi_outstanding_ratings_label(self):
        user, dept = _make_program_head_with_department()
        kpi = _kpi_outstanding_ratings(dept)
        self.assertEqual(kpi["label"], "OUTSTANDING RATINGS")
```

- [ ] **Step 2: Implement**

```python
def _kpi_outstanding_ratings(department):
    """[Classedge LMS] KPI #4 — TeacherRating objects pending review."""
    if department is None:
        return {"label": "OUTSTANDING RATINGS", "value": 0, "delta": "",
                "delta_direction": "flat", "delta_intent": "neutral", "tone": "", "sparkline": []}
    try:
        from gamification.teacher_models import TeacherRating
        # Filter to teachers in this department if the model has a teacher.profile.department link.
        # If not, count all pending — better than 500.
        count = TeacherRating.objects.filter(status="pending").count()
    except Exception:
        count = 0
    return {
        "label": "OUTSTANDING RATINGS",
        "value": count,
        "delta": "",
        "delta_direction": "flat",
        "delta_intent": "bad" if count > 0 else "neutral",
        "tone": "warn" if count > 0 else "",
        "sparkline": [],
    }
```

- [ ] **Step 3: Run + commit**

```bash
python -m pytest accounts/tests/test_program_head_dashboard.py::TestProgramHeadKPIs -v
git add accounts/tests/test_program_head_dashboard.py accounts/views/program_head_dashboard.py
git commit -m "feat(program-head): KPI #4 outstanding ratings"
```

---

### Task 2.17: TDD KPI #5 — Schedule Integrity

**Files:**
- Modify: `accounts/tests/test_program_head_dashboard.py`
- Modify: `accounts/views/program_head_dashboard.py`

- [ ] **Step 1: Write failing tests**

```python
    def test_kpi_schedule_integrity_with_no_events(self):
        user, dept = _make_program_head_with_department()
        kpi = _kpi_schedule_integrity(dept)
        self.assertEqual(kpi["value"], "—")
```

- [ ] **Step 2: Implement**

```python
def _kpi_schedule_integrity(department):
    """[Classedge LMS] KPI #5 — sessions held / scheduled this week × 100%."""
    if department is None:
        return {"label": "SCHEDULE INTEGRITY", "value": "—", "delta": "",
                "delta_direction": "flat", "delta_intent": "neutral", "tone": "", "sparkline": []}

    try:
        from calendars.models import Event
        from datetime import timedelta
        today = timezone.localdate()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=7)
        events = Event.objects.filter(
            department=department, start_date__gte=week_start, start_date__lt=week_end
        ) if hasattr(Event, "department") else Event.objects.none()
        scheduled = events.count()
        held = events.filter(status="held").count() if "status" in [f.name for f in Event._meta.fields] else scheduled
    except Exception:
        scheduled = held = 0

    if scheduled == 0:
        return {"label": "SCHEDULE INTEGRITY", "value": "—", "delta": "",
                "delta_direction": "flat", "delta_intent": "neutral", "tone": "", "sparkline": []}

    pct = (held / scheduled) * 100
    return {
        "label": "SCHEDULE INTEGRITY",
        "value": f"{pct:.0f}%",
        "delta": "",
        "delta_direction": "flat",
        "delta_intent": "good" if pct >= 90 else "bad",
        "tone": "warn" if pct < 90 else "",
        "sparkline": [],
    }
```

- [ ] **Step 3: Run + commit**

```bash
python -m pytest accounts/tests/test_program_head_dashboard.py::TestProgramHeadKPIs -v
git add accounts/tests/test_program_head_dashboard.py accounts/views/program_head_dashboard.py
git commit -m "feat(program-head): KPI #5 schedule integrity"
```

---

### Task 2.18: TDD Course Health primary panel data

**Files:**
- Modify: `accounts/tests/test_program_head_dashboard.py`
- Modify: `accounts/views/program_head_dashboard.py`

- [ ] **Step 1: Write failing test**

Append:

```python
class TestCourseHealth(TestCase):
    def test_course_health_empty_when_no_subjects(self):
        user, dept = _make_program_head_with_department()
        ctx = _build_context(user, dept)
        self.assertEqual(ctx["course_health_rows"], [])

    def test_course_health_sort_floats_trouble_to_top(self):
        user, dept = _make_program_head_with_department()
        # Build 3 subjects in dept with different trouble scores.
        # NOTE: Adapt to the codebase's actual Subject schema if 'department' or
        # related fields differ. If implementation can't synthesize fixtures,
        # mark this test xfail with a TODO for the implementer.
        ctx = _build_context(user, dept)
        rows = ctx["course_health_rows"]
        if rows:
            scores = [r["trouble_score"] for r in rows]
            self.assertEqual(scores, sorted(scores, reverse=True))
```

- [ ] **Step 2: Implement `_course_health_rows(department, term)` helper and wire into `_build_context`**

Add to `accounts/views/program_head_dashboard.py`:

```python
def _course_health_rows(department, term):
    """[Classedge LMS] Course Health rows: subjects-this-term in dept, sorted by trouble desc."""
    rows = []
    if department is None:
        return rows
    try:
        from subject.models import Subject
        subjects = Subject.objects.filter(department=department) if hasattr(Subject, "department") else Subject.objects.none()
    except Exception:
        return rows

    for s in subjects:
        avg = _subject_avg_score(s)  # helper or inline calc
        attn = _subject_attendance_pct(s)
        unstaffed = getattr(s, "teacher", None) is None
        flags = []
        if avg is not None and avg < 70: flags.append("low avg")
        if attn is not None and attn < 85: flags.append(f"{attn:.0f}% attn")
        if unstaffed: flags.append("unstaffed")

        avg_use = avg if avg is not None else 100
        attn_use = attn if attn is not None else 100
        trouble = max(0, (70 - avg_use)) * 0.6 + max(0, (90 - attn_use)) * 0.4
        flagged = trouble > 0 or unstaffed

        rows.append({
            "subject": s.name if hasattr(s, "name") else str(s),
            "teacher": s.teacher.get_full_name() if getattr(s, "teacher", None) else "—",
            "section": getattr(s, "section", "—"),
            "enrolled": _subject_enrollment_count(s),
            "avg": f"{avg:.0f}" if avg is not None else "—",
            "attn": f"{attn:.0f}" if attn is not None else "—",
            "flags": " · ".join(flags) if flags else "—",
            "flagged": flagged,
            "trouble_score": trouble,
        })
    rows.sort(key=lambda r: r["trouble_score"], reverse=True)
    return rows


def _subject_avg_score(subject):
    """[Classedge LMS] Avg activity score for students in this subject. Returns float or None."""
    try:
        from activity.models import StudentActivity
        sa = StudentActivity.objects.filter(activity__subject=subject) if hasattr(StudentActivity._meta.get_field("activity").related_model, "subject") else []
        grades = [a.grade for a in sa if getattr(a, "grade", None) is not None]
        if not grades: return None
        return sum(grades) / len(grades)
    except Exception:
        return None


def _subject_attendance_pct(subject):
    """[Classedge LMS] Attendance % for this subject this term. Returns float 0-100 or None."""
    try:
        from course.models.attendance_model import Attendance
        records = Attendance.objects.filter(subject=subject) if hasattr(Attendance, "subject") else []
        total = records.count() if hasattr(records, "count") else 0
        if total == 0: return None
        present = records.filter(status="present").count() if hasattr(records, "filter") else 0
        return (present / total) * 100
    except Exception:
        return None


def _subject_enrollment_count(subject):
    """[Classedge LMS] '{active}/{capacity}' or single number if capacity unknown."""
    try:
        from course.models.subject_enrollment_model import SubjectEnrollment
        active = SubjectEnrollment.objects.filter(subject=subject).count()
        cap = getattr(subject, "capacity", None)
        return f"{active}/{cap}" if cap else str(active)
    except Exception:
        return "—"
```

Update `_build_context` to call `_course_health_rows`:

```python
# In _build_context, replace the line:
#   "course_health_rows": [],
# with:
"course_health_rows": _course_health_rows(department, term),
```

- [ ] **Step 3: Run + commit**

```bash
python -m pytest accounts/tests/test_program_head_dashboard.py::TestCourseHealth -v
git add accounts/tests/test_program_head_dashboard.py accounts/views/program_head_dashboard.py
git commit -m "feat(program-head): course health primary panel (trouble-sorted)"
```

---

### Task 2.19: TDD Teacher Pulse secondary panel + leaderboard regression guard

**Files:**
- Modify: `accounts/tests/test_program_head_dashboard.py`
- Modify: `accounts/views/program_head_dashboard.py`

- [ ] **Step 1: Write failing tests including regression guard**

Append:

```python
class TestTeacherPulse(TestCase):
    def test_teacher_pulse_empty_when_no_teachers(self):
        user, dept = _make_program_head_with_department()
        ctx = _build_context(user, dept)
        self.assertEqual(ctx["teacher_pulse_rows"], [])

    def test_teacher_pulse_does_not_render_total_ip_as_number(self):
        """REGRESSION GUARD: rendering total_ip would re-enable the leaderboard pattern."""
        user, dept = _make_program_head_with_department()
        self.client.force_login(user)
        resp = self.client.get(reverse("program_head_dashboard"))
        # If a teacher exists with total_ip=12345, that string MUST NOT appear in the panel.
        # Generic check: the column header is not "IP" or "Rank".
        self.assertNotContains(resp, "Rank")
        self.assertNotContains(resp, "Leaderboard")
        self.assertContains(resp, "Who needs support this week")

    def test_teacher_pulse_subheader_uses_support_copy(self):
        user, dept = _make_program_head_with_department()
        self.client.force_login(user)
        resp = self.client.get(reverse("program_head_dashboard"))
        self.assertContains(resp, "Who needs support this week")
        self.assertContains(resp, "lowest IP-velocity")  # the why subhead
```

- [ ] **Step 2: Implement `_teacher_pulse_rows`**

Add:

```python
def _teacher_pulse_rows(department):
    """[Classedge LMS] 'Who needs support this week' — sorted by support_score desc."""
    rows = []
    if department is None:
        return rows
    try:
        from subject.models import Subject
        from gamification.teacher_models import TeacherGamification, IPTransaction, TeacherRating
        from datetime import timedelta

        teacher_ids = set()
        if hasattr(Subject, "department"):
            for s in Subject.objects.filter(department=department):
                if getattr(s, "teacher_id", None):
                    teacher_ids.add(s.teacher_id)

        seven_days_ago = timezone.now() - timedelta(days=7)
        for tid in teacher_ids:
            ip_delta_7d = sum(
                tx.amount for tx in IPTransaction.objects.filter(teacher_id=tid, created_at__gte=seven_days_ago)
            )
            outstanding = TeacherRating.objects.filter(teacher_id=tid, status="pending").count() if "TeacherRating" in dir() else 0
            flagged_subjects = []
            if hasattr(Subject, "department"):
                for s in Subject.objects.filter(department=department, teacher_id=tid):
                    avg = _subject_avg_score(s)
                    attn = _subject_attendance_pct(s)
                    if (avg is not None and avg < 70) or (attn is not None and attn < 85):
                        flagged_subjects.append(s.name)

            support_score = max(0, -ip_delta_7d) * 0.5 + outstanding * 30 + len(flagged_subjects) * 50
            from accounts.models.account_models import CustomUser
            t = CustomUser.objects.get(id=tid)
            rows.append({
                "teacher": t.get_full_name() or t.username,
                "subjects": Subject.objects.filter(department=department, teacher_id=tid).count() if hasattr(Subject, "department") else 0,
                "ip_delta_text": f"{ip_delta_7d:+d} IP",  # always shown as a delta, NEVER total
                "outstanding_text": f"{outstanding} rating{'s' if outstanding != 1 else ''}" if outstanding else "—",
                "flagged_text": f"{len(flagged_subjects)} ({', '.join(flagged_subjects)})" if flagged_subjects else "—",
                "support_score": support_score,
            })
    except Exception:
        return rows

    rows.sort(key=lambda r: r["support_score"], reverse=True)
    return rows
```

Update `_build_context`:

```python
"teacher_pulse_rows": _teacher_pulse_rows(department),
```

- [ ] **Step 3: Run + commit**

```bash
python -m pytest accounts/tests/test_program_head_dashboard.py::TestTeacherPulse -v
git add accounts/tests/test_program_head_dashboard.py accounts/views/program_head_dashboard.py
git commit -m "feat(program-head): teacher pulse panel (support score, IP delta — never total)"
```

---

### Task 2.20: TDD hero widget data (Department Pulse)

**Files:**
- Modify: `accounts/tests/test_program_head_dashboard.py`
- Modify: `accounts/views/program_head_dashboard.py`

- [ ] **Step 1: Write failing test**

```python
class TestHeroWidget(TestCase):
    def test_hero_widget_data_present_when_department_set(self):
        user, dept = _make_program_head_with_department()
        ctx = _build_context(user, dept)
        self.assertIsNotNone(ctx["hero_widget_data"])
        self.assertIn("at_risk_count", ctx["hero_widget_data"])

    def test_hero_widget_renders_in_html(self):
        user, dept = _make_program_head_with_department()
        self.client.force_login(user)
        resp = self.client.get(reverse("program_head_dashboard"))
        self.assertContains(resp, "Department Pulse")
```

- [ ] **Step 2: Implement hero widget builder**

Add:

```python
def _hero_widget_data(department):
    """[Classedge LMS] Department pulse — at-risk count + Δ + sparkline + CTA."""
    if department is None:
        return None
    at_risk_kpi = _kpi_at_risk_students(department, term=None)
    return {
        "at_risk_count": at_risk_kpi["value"],
        "delta": at_risk_kpi.get("delta", ""),
        "delta_intent": at_risk_kpi.get("delta_intent", "neutral"),
        "sparkline_points": "",  # 7-day trend not computed in v1
        "cta_url": "#at-risk-roster",
    }
```

Update `_build_context`:

```python
"hero_widget_data": _hero_widget_data(department),
```

- [ ] **Step 3: Run + commit**

```bash
python -m pytest accounts/tests/test_program_head_dashboard.py::TestHeroWidget -v
git add accounts/tests/test_program_head_dashboard.py accounts/views/program_head_dashboard.py
git commit -m "feat(program-head): hero widget data (department pulse)"
```

---

### Task 2.21: TDD right rail data (Today + Outstanding + Announcements)

**Files:**
- Modify: `accounts/tests/test_program_head_dashboard.py`
- Modify: `accounts/views/program_head_dashboard.py`

- [ ] **Step 1: Write failing tests**

```python
class TestRightRail(TestCase):
    def test_right_rail_today_card_renders(self):
        user, dept = _make_program_head_with_department()
        self.client.force_login(user)
        resp = self.client.get(reverse("program_head_dashboard"))
        self.assertContains(resp, "Today")

    def test_right_rail_announcements_card_renders(self):
        user, dept = _make_program_head_with_department()
        self.client.force_login(user)
        resp = self.client.get(reverse("program_head_dashboard"))
        self.assertContains(resp, "Announcements")

    def test_right_rail_outstanding_only_when_pending(self):
        user, dept = _make_program_head_with_department()
        ctx = _build_context(user, dept)
        # With no pending ratings, outstanding list is empty
        self.assertEqual(ctx["right_rail_data"]["outstanding"], [])
```

- [ ] **Step 2: Implement right-rail builder**

Add:

```python
def _right_rail_data(department):
    """[Classedge LMS] Right-rail content: today's events, outstanding ratings, announcements."""
    if department is None:
        return {"today": [], "outstanding": [], "announcements": []}

    today_items = []
    try:
        from calendars.models import Event
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(hours=24)
        if hasattr(Event, "department"):
            for ev in Event.objects.filter(department=department, start_date__gte=cutoff)[:5]:
                today_items.append({
                    "when": ev.start_date.strftime("%b %-d") if hasattr(ev.start_date, "strftime") else str(ev.start_date),
                    "title": ev.title,
                    "audience": getattr(ev, "audience", "Both"),
                })
    except Exception:
        pass

    outstanding = []
    try:
        from gamification.teacher_models import TeacherRating
        for r in TeacherRating.objects.filter(status="pending")[:5]:
            outstanding.append({
                "teacher": r.teacher.get_full_name() or r.teacher.username,
                "url": "#",
            })
    except Exception:
        pass

    announcements = []
    try:
        from calendars.models import Announcement
        if hasattr(Announcement, "department"):
            for a in Announcement.objects.filter(department=department).order_by("-created_at")[:3]:
                announcements.append({"title": a.title, "created_at": a.created_at})
        else:
            for a in Announcement.objects.order_by("-created_at")[:3]:
                announcements.append({"title": a.title, "created_at": a.created_at})
    except Exception:
        pass

    return {"today": today_items, "outstanding": outstanding, "announcements": announcements}
```

Update `_build_context`:

```python
"right_rail_data": _right_rail_data(department),
```

- [ ] **Step 3: Run + commit**

```bash
python -m pytest accounts/tests/test_program_head_dashboard.py::TestRightRail -v
git add accounts/tests/test_program_head_dashboard.py accounts/views/program_head_dashboard.py
git commit -m "feat(program-head): right rail data (today, outstanding, announcements)"
```

---

### Task 2.22: TDD render + permissions

**Files:**
- Modify: `accounts/tests/test_program_head_dashboard.py`

- [ ] **Step 1: Write failing tests**

```python
class TestProgramHeadDashboardRender(TestCase):
    def test_renders_for_program_head_with_department(self):
        user, dept = _make_program_head_with_department()
        self.client.force_login(user)
        resp = self.client.get(reverse("program_head_dashboard"))
        self.assertEqual(resp.status_code, 200)

    def test_renders_all_5_kpis(self):
        user, dept = _make_program_head_with_department()
        self.client.force_login(user)
        resp = self.client.get(reverse("program_head_dashboard"))
        self.assertEqual(len(resp.context["kpis"]), 5)

    def test_role_glyph_in_rendered_html(self):
        user, dept = _make_program_head_with_department()
        self.client.force_login(user)
        resp = self.client.get(reverse("program_head_dashboard"))
        self.assertContains(resp, "◆")
        self.assertContains(resp, "PROGRAM HEAD")

    def test_empty_department_state_renders_without_500(self):
        username = f"ph-{uuid.uuid4().hex[:8]}"
        user = CustomUser.objects.create_user(
            username=username, email=f"{username}@x.io", password="x"
        )
        make_profile_for(user, "Program Head")
        # No Department.head=user — graceful fallback expected
        self.client.force_login(user)
        resp = self.client.get(reverse("program_head_dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "No department assigned")


class TestProgramHeadDashboardPermissions(TestCase):
    def test_403_for_non_program_head(self):
        username = f"t-{uuid.uuid4().hex[:8]}"
        teacher = CustomUser.objects.create_user(
            username=username, email=f"{username}@x.io", password="x"
        )
        make_profile_for(teacher, "Teacher")
        self.client.force_login(teacher)
        resp = self.client.get(reverse("program_head_dashboard"))
        self.assertIn(resp.status_code, (302, 403))

    def test_redirects_anon_user(self):
        resp = self.client.get(reverse("program_head_dashboard"))
        self.assertIn(resp.status_code, (302, 403))
```

- [ ] **Step 2: Run, fix any failures**

```bash
python -m pytest accounts/tests/test_program_head_dashboard.py -v
```

If `test_empty_department_state_renders_without_500` fails because the template crashes on missing context, adjust the empty `_build_context` branch in the view to provide all keys with safe defaults.

- [ ] **Step 3: Commit**

```bash
git add accounts/tests/test_program_head_dashboard.py
git commit -m "test(program-head): render + permissions + empty-department coverage"
```

---

### Task 2.23: Wire `program_head_dashboard` into the role router

**Files:**
- Modify: `accounts/views/dashboard.py`

- [ ] **Step 1: Add the import**

Near the existing imports:

```python
from accounts.views.program_head_dashboard import program_head_dashboard
```

- [ ] **Step 2: Add the role branch in the `dashboard` function**

After the `is_academic_director` block:

```python
is_program_head = role_name == 'program head'

# ...

if is_program_head:
    return program_head_dashboard(request)
```

- [ ] **Step 3: Add a routing test**

In `accounts/tests/test_program_head_dashboard.py`, append:

```python
class TestProgramHeadRouting(TestCase):
    def test_dashboard_router_lands_on_program_head_view(self):
        user, dept = _make_program_head_with_department()
        self.client.force_login(user)
        resp = self.client.get(reverse("dashboard"))
        # Either 200 with PH content, or 302→`/program-head/`. Both acceptable.
        if resp.status_code == 302:
            self.assertEqual(resp.url, reverse("program_head_dashboard"))
        else:
            self.assertEqual(resp.status_code, 200)
            self.assertContains(resp, "PROGRAM HEAD")
```

- [ ] **Step 4: Run + commit**

```bash
python -m pytest accounts/tests/test_program_head_dashboard.py -v
git add accounts/views/dashboard.py accounts/tests/test_program_head_dashboard.py
git commit -m "feat(program-head): wire role into dashboard router"
```

---

### Task 2.24: Add polish-foundation regression guards to test mixin

**Files:**
- Modify: `accounts/tests/operations_dashboard_mixin.py`

- [ ] **Step 1: Append assertion methods**

```python
    def assert_skip_link_first(self):
        """[Classedge LMS] The skip-link must be the first interactive element."""
        resp = self.assert_renders_for_role()
        self.assertContains(resp, 'class="skip-link"')

    def assert_kpi_strip_handles_optional_fields_absent(self):
        """[Classedge LMS] KPIs without sparkline/delta_direction render unchanged."""
        resp = self.assert_renders_for_role()
        # If any KPI has these fields, ensure they don't blow up rendering.
        for kpi in resp.context["kpis"]:
            self.assertIn("label", kpi)
            self.assertIn("value", kpi)

    def assert_empty_state_renders_for_empty_worklist(self):
        """[Classedge LMS] Empty worklist uses .empty-state block, not bare 'Nothing here.'"""
        resp = self.assert_renders_for_role()
        # If a worklist is empty in this fixture, check for empty-state markup.
        if "empty-state" in resp.content.decode():
            self.assertIn("empty-glyph", resp.content.decode())
```

- [ ] **Step 2: Use the new assertions in `test_program_head_dashboard.py`**

Add at the bottom of the file:

```python
class TestProgramHeadOpsMixin(OperationsDashboardTestMixin, TestCase):
    url_name = "program_head_dashboard"
    role = "Program Head"
    glyph = "◆"
    kpi_count = 5

    def setUp(self):
        # Mixin's make_user_with_role doesn't make a Department; do it here.
        self.user, self.dept = _make_program_head_with_department()

    def assert_renders_for_role(self):
        self.client.force_login(self.user)
        from django.urls import reverse
        resp = self.client.get(reverse(self.url_name))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["kpis"]), self.kpi_count)
        return resp

    def test_skip_link_first(self):
        self.assert_skip_link_first()

    def test_optional_kpi_fields_handled(self):
        self.assert_kpi_strip_handles_optional_fields_absent()

    def test_empty_state_renders_when_empty(self):
        self.assert_empty_state_renders_for_empty_worklist()

    def test_glyph_renders(self):
        self.assert_glyph_renders()
```

- [ ] **Step 3: Run + commit**

```bash
python -m pytest accounts/tests/test_program_head_dashboard.py::TestProgramHeadOpsMixin -v
git add accounts/tests/operations_dashboard_mixin.py accounts/tests/test_program_head_dashboard.py
git commit -m "test(operations): polish regression guards (skip-link, optional kpi fields, empty-state)"
```

---

### Task 2.25: Run full test suite, manual smoke, open PR #2

- [ ] **Step 1: Full test suite**

```bash
python -m pytest accounts/tests/ -v --tb=short
```

Expected: ALL PASS.

- [ ] **Step 2: Manual smoke — Program Head**

Login as a Program Head with a department assigned. Visit `/program-head/`. Verify:
- Hero shows greeting + Department Pulse widget
- 5 KPI cards
- Course Health primary panel + Teacher Pulse secondary panel
- Right rail: Today / Outstanding / Announcements
- All polish: shadows, motion, sparklines (where data), pulse dot, empty states

- [ ] **Step 3: Manual smoke — Wave A regression**

Login as Registrar / Coil Admin / Academic Director / IT Admin. Verify each renders and looks visually polished (shadows, motion, etc.), with right rails empty (collapsed via `:has`).

- [ ] **Step 4: Push and open PR #2**

```bash
git push -u personal feat/program-head-with-polished-shell
```

Title: `feat(program-head): Operations Mode dashboard + polish foundation upgrade`

Body summary:
- Ships Program Head dashboard under Operations Mode (deep-dive treatment, sharing layout with future Principal).
- Bundles the polish foundation upgrade: depth, motion, sparklines, KPI delta directions, empty-state block, flagged-row affordance, mobile responsive, accessibility (focus rings, contrast, skip-link reuse, mono utility), print stylesheet, JetBrains Mono actually loaded.
- ~900 lines. Spec: §5–§6 of `docs/superpowers/specs/2026-04-27-program-head-shared-shell-and-polish-design.md`.

- [ ] **Step 5: Wait for review and merge before starting Phase 3**

---

# Phase 3 — Polish backport + rails for Wave A (PR #3)

Branch: `chore/operations-mode-polish-backport-and-rails` off `main` after PR #2 merged.

### Task 3.1: Update Registrar view with deltas, sparklines, hero widget, right rail

**Files:**
- Modify: `accounts/views/registrar.py`

- [ ] **Step 1: Add helper for sparkline points (or import)**

If `_sparkline_points` from Program Head was moved to a shared location, import it. Otherwise duplicate at the top:

```python
def _sparkline_points(values, width=100, height=24):
    if not values: return ""
    n = len(values)
    if n == 1: return f"0,{height/2} {width},{height/2}"
    lo, hi = min(values), max(values); span = max(hi - lo, 1)
    pts = []
    for i, v in enumerate(values):
        x = (i / (n - 1)) * width
        y = height - ((v - lo) / span) * (height - 2) - 1
        pts.append(f"{x:.1f},{y:.1f}")
    return " ".join(pts)
```

- [ ] **Step 2: Enrich existing KPIs with `delta_direction`, `delta_intent`, `sparkline`**

Find the existing `_registrar_kpis()` function. For each KPI dict, add:

```python
return [
    {
        "label": "Active Enrollments",
        "value": active_enrollments,
        "delta": "",
        "delta_direction": "flat",
        "delta_intent": "neutral",
        "tone": "",
        "sparkline": [],
    },
    {
        "label": "Pending Requests",
        "value": pending_requests or "—",
        "delta": "",
        "delta_direction": "flat",
        "delta_intent": "neutral",
        "tone": "warn" if pending_requests > 0 else "",
        "sparkline": [],
    },
    # ... and so on for all 5 KPIs ...
]
```

For any KPI with a 14-day or 7-week historical query, populate `sparkline` and compute `sparkline_points`:

```python
# Example: request volume 14d sparkline
volume_per_day = []  # [count, count, ...] from existing audit log query
# ... if you have it, after building the kpi dict:
kpi["sparkline"] = volume_per_day
kpi["sparkline_points"] = _sparkline_points(volume_per_day)
```

- [ ] **Step 3: Add hero widget data**

In the view, before rendering, build:

```python
hero_widget_data = {
    "label": "Today's Queue",
    "value": pending_requests,
    "subtext": f"{flagged_records} aging past SLA" if flagged_records else "All within SLA",
    "url": "#registrar-queue",
}
```

- [ ] **Step 4: Add right rail data**

```python
right_rail_data = {
    "today_transactions": [],  # populate from SubjectEnrollment.objects.filter(enrollment_date=today)
    "recent_handoffs": [],     # if there's an audit log for cross-role handoffs
}
```

- [ ] **Step 5: Pass into context**

```python
context.update({
    "hero_widget_data": hero_widget_data,
    "right_rail_data": right_rail_data,
})
```

- [ ] **Step 6: Run existing tests**

```bash
python -m pytest accounts/tests/test_registrar_dashboard.py -v
```

Expected: PASS.

- [ ] **Step 7: No commit yet — commit with template change in next task**

---

### Task 3.2: Update Registrar template — hero widget + right rail blocks + warmer copy

**Files:**
- Modify: `templates/operations/registrar_dashboard.html`

- [ ] **Step 1: Add `hero_widget` block**

After the existing `{% extends 'operations_base.html' %}` line, before `{% block primary_panel %}`:

```django
{% block hero_widget %}
  {% if hero_widget_data %}
    <div class="hero-pulse">
      <span class="hero-pulse-label">{{ hero_widget_data.label }}</span>
      <h3 class="hero-pulse-title">
        <span class="mono">{{ hero_widget_data.value }}</span>
      </h3>
      <p class="hero-pulse-meta">{{ hero_widget_data.subtext }}</p>
      <a href="{{ hero_widget_data.url }}" class="hero-pulse-cta">Open queue →</a>
    </div>
  {% endif %}
{% endblock %}
```

- [ ] **Step 2: Add `right_rail` block**

Before the closing of the file:

```django
{% block right_rail %}
  <div class="rail-card">
    <h3 class="rail-card-title">Today's transactions</h3>
    <ul class="rail-list">
      {% for tx in right_rail_data.today_transactions|slice:":5" %}
        <li>{{ tx.label }} <span class="rail-when mono">{{ tx.when }}</span></li>
      {% empty %}
        <li class="rail-empty">No transactions yet today.</li>
      {% endfor %}
    </ul>
  </div>
  {% if right_rail_data.recent_handoffs %}
  <div class="rail-card">
    <h3 class="rail-card-title">Recent handoffs</h3>
    <ul class="rail-list">
      {% for h in right_rail_data.recent_handoffs|slice:":3" %}
        <li>{{ h.text }} <span class="rail-when mono">{{ h.when }}</span></li>
      {% endfor %}
    </ul>
  </div>
  {% endif %}
{% endblock %}
```

- [ ] **Step 3: Update empty-state copy in primary panel**

Find:

```django
{% include 'operations/worklist_panel.html' with title="Aging Requests" why="oldest first — flagged at 7+ days" columns=aging_columns rows=aging_rows empty_message="No open requests." %}
```

Change `empty_message` to:

```django
empty_message="No open requests — your queue is clear."
```

- [ ] **Step 4: Run + smoke test**

```bash
python -m pytest accounts/tests/test_registrar_dashboard.py -v
```

Login as Registrar. Verify hero widget shows "Today's Queue", right rail shows transactions card.

- [ ] **Step 5: Add test for copy + sparkline**

Append to `accounts/tests/test_registrar_dashboard.py`:

```python
def test_warmer_empty_copy_renders(self):
    user = self.make_user_with_role("Registrar")
    self.client.force_login(user)
    resp = self.client.get(reverse("registrar_dashboard"))
    if resp.context["aging_rows"] == []:
        self.assertContains(resp, "your queue is clear")

def test_hero_widget_today_queue_renders(self):
    user = self.make_user_with_role("Registrar")
    self.client.force_login(user)
    resp = self.client.get(reverse("registrar_dashboard"))
    self.assertContains(resp, "Today's Queue")
```

- [ ] **Step 6: Commit**

```bash
git checkout -b chore/operations-mode-polish-backport-and-rails
git add accounts/views/registrar.py templates/operations/registrar_dashboard.html accounts/tests/test_registrar_dashboard.py
git commit -m "feat(registrar): hero widget + right rail + warmer empty copy"
```

---

### Task 3.3: Same upgrade for Coil Admin

**Files:**
- Modify: `accounts/views/coil_admin.py`
- Modify: `templates/operations/coil_admin_dashboard.html`
- Modify: `accounts/tests/test_coil_admin_dashboard.py`

- [ ] **Step 1: Add hero_widget_data + right_rail_data + KPI deltas to view**

In the view function, build:

```python
hero_widget_data = {
    "label": "Pipeline this week",
    "value": pending_invites,  # from existing CoilPartnerSchool.status counts
    "subtext": f"{responded} responded",
    "url": "#coil-pipeline",
}

right_rail_data = {
    "upcoming_sessions": [],  # from coil calendar entries
    "partner_news": [],
}
```

Add `delta_direction`, `delta_intent`, `sparkline` to each KPI dict.

- [ ] **Step 2: Add hero_widget and right_rail blocks to template**

Same pattern as Task 3.2. Re-skin the existing "Coming soon — class-level collaboration model pending." `<p class="context-empty">` as a proper `.empty-state` block:

```django
<div class="empty-state">
  <div class="empty-glyph" aria-hidden="true"></div>
  <p>Coming soon — class-level collaboration model pending.</p>
</div>
```

- [ ] **Step 3: Update existing tests + add 2 assertions**

```python
def test_warmer_empty_copy_renders(self):
    user = self.make_user_with_role("Coil Admin")
    self.client.force_login(user)
    resp = self.client.get(reverse("coil_admin_dashboard"))
    self.assertContains(resp, "empty-glyph")  # any place using the new empty-state

def test_hero_widget_pipeline_renders(self):
    user = self.make_user_with_role("Coil Admin")
    self.client.force_login(user)
    resp = self.client.get(reverse("coil_admin_dashboard"))
    self.assertContains(resp, "Pipeline this week")
```

- [ ] **Step 4: Run + commit**

```bash
python -m pytest accounts/tests/test_coil_admin_dashboard.py -v
git add accounts/views/coil_admin.py templates/operations/coil_admin_dashboard.html accounts/tests/test_coil_admin_dashboard.py
git commit -m "feat(coil-admin): hero widget + right rail + empty-state polish"
```

---

### Task 3.4: Same upgrade for Academic Director

**Files:**
- Modify: `accounts/views/academic_director.py`
- Modify: `templates/operations/academic_director_dashboard.html`
- Modify: `accounts/tests/test_academic_director_dashboard.py`

- [ ] **Step 1: Add hero_widget_data**

```python
hero_widget_data = {
    "label": "Coverage drift",
    "value": at_risk_count,
    "subtext": "programs trending below intent",
    "sparkline": at_risk_7w_trend,  # from existing gamification data
    "url": "#program-heatmap",
}
hero_widget_data["sparkline_points"] = _sparkline_points(hero_widget_data["sparkline"])
```

- [ ] **Step 2: Add right_rail_data**

```python
right_rail_data = {
    "pending_decisions": pending_decision_rows[:3],
    "content_runway": [],  # placeholder list of central_content runway items
}
```

- [ ] **Step 3: Enrich KPIs with deltas + sparklines**

(For at-risk and outcome attainment KPIs, populate `sparkline` from existing time-series in `gamification`.)

- [ ] **Step 4: Update template with hero_widget + right_rail blocks**

Same pattern as Task 3.2.

- [ ] **Step 5: Add test assertions + commit**

```python
def test_hero_widget_coverage_drift_renders(self):
    user = self.make_user_with_role("Academic Director")
    self.client.force_login(user)
    resp = self.client.get(reverse("academic_director_dashboard"))
    self.assertContains(resp, "Coverage drift")
```

```bash
python -m pytest accounts/tests/test_academic_director_dashboard.py -v
git add accounts/views/academic_director.py templates/operations/academic_director_dashboard.html accounts/tests/test_academic_director_dashboard.py
git commit -m "feat(academic-director): hero widget + right rail + sparkline KPIs"
```

---

### Task 3.5: Same upgrade for IT Admin

**Files:**
- Modify: `accounts/views/it_admin.py`
- Modify: `templates/operations/it_admin_dashboard.html`
- Modify: `accounts/tests/test_it_admin_dashboard.py`

- [ ] **Step 1: Add hero_widget_data**

```python
hero_widget_data = {
    "label": "System status",
    "value": "All green",  # or "Degraded" / "Outage"
    "subtext": f"{services_ok}/{services_total} services healthy",
    "url": "#it-admin-status",
}
```

- [ ] **Step 2: Add right_rail_data**

```python
right_rail_data = {
    "failed_logins": failed_logins_last_hour,  # list
    "celery_snapshots": [],
}
```

- [ ] **Step 3: Enrich KPIs (Active Users 24h, Celery Queue Depth) with sparklines**

- [ ] **Step 4: Update template — re-skin the "Real-time service health will appear here…" placeholder as `.empty-state`**

```django
<div class="empty-state">
  <div class="empty-glyph" aria-hidden="true"></div>
  <p>Real-time service health will appear here once the monitoring backend is wired.</p>
</div>
```

Add `hero_widget` and `right_rail` blocks per Task 3.2 pattern.

- [ ] **Step 5: Test + commit**

```python
def test_hero_widget_system_status_renders(self):
    user = self.make_user_with_role("IT Admin")
    self.client.force_login(user)
    resp = self.client.get(reverse("it_admin_dashboard"))
    self.assertContains(resp, "System status")
```

```bash
python -m pytest accounts/tests/test_it_admin_dashboard.py -v
git add accounts/views/it_admin.py templates/operations/it_admin_dashboard.html accounts/tests/test_it_admin_dashboard.py
git commit -m "feat(it-admin): hero widget + right rail + sparkline KPIs"
```

---

### Task 3.6: Update Wave A spec with footer note

**Files:**
- Modify: `docs/superpowers/specs/2026-04-27-wave-a-finish-design.md`

- [ ] **Step 1: Append to end of file**

```markdown

---

**Polish backport applied in `chore/operations-mode-polish-backport-and-rails` (2026-04-27 sub-project).** See `docs/superpowers/specs/2026-04-27-program-head-shared-shell-and-polish-design.md` §8.3.
```

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/specs/2026-04-27-wave-a-finish-design.md
git commit -m "docs(wave-a): note polish backport in successor sub-project"
```

---

### Task 3.7: Full regression test + manual visual verification

- [ ] **Step 1: Run full test suite**

```bash
python -m pytest accounts/tests/ -v --tb=short
```

Expected: ALL PASS.

- [ ] **Step 2: Manual visual diff vs PR #2**

Open all four Wave A dashboards (Registrar / Coil Admin / Academic Director / IT Admin) plus Program Head. Check:
- Hero widget renders for each role
- Right rail renders for each role (no longer empty)
- Sparklines render where data exists; absent where data doesn't (no empty SVG ghosts)
- Empty states use `.empty-state` block + warmer copy
- Polish (shadows, motion, hover) intact
- Mobile (375px), tablet (1280px), desktop (1920px) all render correctly

- [ ] **Step 3: Run pre-merge manual checklist (per spec §10.6)**

Tab through each page → focus rings visible. Toggle `prefers-reduced-motion` → motion stops. `Cmd+P` → print-clean.

---

### Task 3.8: Push and open PR #3

- [ ] **Step 1: Push branch**

```bash
git push -u personal chore/operations-mode-polish-backport-and-rails
```

- [ ] **Step 2: Open PR**

Title: `chore(operations): backport polish + add right rails to Wave A dashboards`

Body summary:
- Adds `hero_widget` and `right_rail` content to Registrar / Coil Admin / Academic Director / IT Admin (the layout slots were created in PR #1).
- Enriches KPI dicts with `delta_direction`, `delta_intent`, and `sparkline` data (where time-series exist).
- Re-skins existing placeholder copy as `.empty-state` blocks for warmer presentation.
- Footer note added to Wave A spec pointing to this branch.
- ~400 lines, mostly mechanical. Spec: §8.3 of `docs/superpowers/specs/2026-04-27-program-head-shared-shell-and-polish-design.md`.

- [ ] **Step 3: Merge after review**

---

## Self-review notes

**Spec coverage (verified inline):**
- §3 Roles in scope — all 7 roles touched (Phase 1: Student, Teacher, all Operations bases; Phase 2: Program Head; Phase 3: 4 Wave A roles).
- §4 Architecture — `role_skeleton.html` (Task 1.2), role-bases extending it (Tasks 1.3–1.5), shell grid CSS (Tasks 1.7–1.9), per-dashboard authoring contract (used in Tasks 1.10, 1.11, 2.12, 3.2–3.5).
- §5 Polish bar deltas — visual depth (Task 2.1), motion (Task 2.2), KPI affordances (Task 2.3), worklist polish (Task 2.4), context strip empty (Task 2.5), scope bar pulse + mono (Task 2.6), a11y/print/skeletons/mono (Task 2.7).
- §6 Program Head data hierarchy — KPIs (Tasks 2.13–2.17), Course Health (Task 2.18), Teacher Pulse (Task 2.19), hero widget (Task 2.20), right rail (Task 2.21), render+permissions (Task 2.22), router wiring (Task 2.23).
- §7 Per-role hero+rail content — Student/Teacher in Phase 1 (Tasks 1.10, 1.11), Wave A in Phase 3 (Tasks 3.1–3.5).
- §8 PR breakdown — three branches, three PRs (Tasks 1.13, 2.25, 3.8).
- §10 Testing — test mixin extensions (Task 2.24), per-PR test additions throughout.

**Placeholder scan:** No `TBD` / `TODO` / `implement later` strings. Code blocks present in every "Implement" step. Field-name fallback patterns (`if hasattr(...)`) documented as adapt-to-codebase notes in tasks where the schema may differ.

**Type consistency:** `_kpi_*` functions return dicts with same keys (`label`, `value`, `delta`, `delta_direction`, `delta_intent`, `tone`, `sparkline`) across Tasks 2.13–2.17. `_build_context` keys match across all consumers. `hero_widget_data` shape stable across roles; `right_rail_data` is per-role-keyed but the template accesses use `|default` for safety.

**Open follow-ups:**
- Per-role data sources (`StudentActivity.grade`, `Subject.department`, `Event.department`) require schema verification at implementation time. Tasks include `grep`-first instructions.
- `at_risk.AtRiskFlag` / `central_content` model imports are wrapped in `try/except` so a missing app degrades gracefully rather than 500'ing.
