# Program Head + Shared Role Skeleton + Operations Polish — Design

**System:** Classedge LMS
**Status:** Drafted 2026-04-27
**Parent specs:**
- `docs/superpowers/specs/2026-04-25-non-teacher-student-dashboard-redesign-design.md` — locks the Operations Mode design system and Program Head's data hierarchy.
- `docs/superpowers/specs/2026-04-27-wave-a-finish-design.md` — Wave A foundation + 4 dashboards already shipped (PRs #16–#22).
- `docs/superpowers/specs/2026-04-17-student-dashboard-redesign-design.md` — Student gamified shell.
- `docs/superpowers/specs/2026-04-18-teacher-dashboard-sp{1,2,3}-design.md` — Teacher editorial shell.

**Sub-project of:** the broader dashboard redesign initiative.

---

## 1. Why this sub-project

Three things need to happen together because they share architecture:

1. **Program Head dashboard.** It is the only role from the user's stated set (admin, teacher, student, registrar, program head, academic director) without a redesigned dashboard. The parent spec locked its data hierarchy as a "deep-dive" treatment sharing layout with the (future) Principal dashboard.
2. **Operations Mode polish.** Wave A (Registrar / Coil Admin / Academic Director / IT Admin) shipped functionally but ~10x below the Student/Teacher polish bar — flat backgrounds, almost no motion, no skeletons, dry empty states, no mobile responsive, missing focus rings, contrast issues, JetBrains Mono declared but never loaded, sparklines specified but never built.
3. **Right-side empty space across all three shells.** The Student dashboard hero block leaves the right ~40% as bare navy; Teacher has the same shape of waste; Operations was never structured to use it. Fixing this at the per-shell level would re-introduce the drift the dashboard redesign initiative was meant to remove. The fix belongs at a shared-base layer.

The cleanest solution is one design that delivers all three, sequenced as three PRs that build on each other.

## 2. Locked decisions

| # | Decision |
|---|----------|
| 1 | **Operations Mode is the teacher design language for back-office roles.** Wave A stays. No re-platforming onto `teacher_base.html`. Program Head joins Operations Mode under the same shell, applying the parent spec's "deep-dive" treatment. |
| 2 | **Right-side empty space is fixed at the shared-base level.** Each role-base (`student_base.html`, `teacher_base.html`, `operations_base.html`) gains a `hero | hero-widget` split and an opt-in `right-rail` column. Implemented via a new shared parent template `role_skeleton.html` so block names are identical across all three role-bases. |
| 3 | **`role_skeleton.html` is new; legacy `base.html` is untouched.** Legacy Bootstrap pages (gradebook, IDE, calendars, modules) keep their current chrome. The skeleton holds doctype/viewport/CSRF/favicon/OG only — no layout, no theme. |
| 4 | **No gamification language outside Teacher and Student.** Reaffirmed from parent spec §5.3. Program Head's "Teacher Pulse" is a "who needs support this week" intervention queue, never a leaderboard. IP/rank values are read but never rendered as numbers in this surface. |
| 5 | **Polish foundation lands with a real consumer.** PR #2 ships the polish upgrade *together with* Program Head, so every new CSS rule is exercised by Program Head's render. PR #3 mechanically backports the polish affordances to the four Wave A dashboards. |
| 6 | **No new Django apps, no new models, no migrations.** All data sources exist (`Department`, `Profile`, `Subject`, `SubjectEnrollment`, `TeacherGamification`, `TeacherRating`, `Event`, `Announcement`, `Semester`/`Term`, `gamification.AtRiskFlag`). |
| 7 | **Two-PR cadence per concern.** Foundation (skeleton + right-rail layout) ships first as a structural-only refactor; visible behavior unchanged for Student/Teacher except the hero gets a right-side container. Polish + Program Head ships next. Backport ships last. |
| 8 | **Principal dashboard is NOT in scope.** Program Head's view module exposes `_build_context(user, department)` so a future Principal view can call it with different `glyph` / `role_tag` / scope copy — design coupling locked, build deferred. |
| 9 | **No HTMX / async loading wired up.** Skeleton CSS classes (`.skeleton-line`, `.skeleton-block`, `.skeleton-kpi`) ship for future use but the PRs render server-side as today. |
| 10 | **No dark mode for Operations Mode.** Student keeps its dark/light toggle. Teacher and Operations stay cream-only. Revisit only if a specific role (e.g., IT Admin night shift) explicitly requests it. |

## 3. Roles in scope

| Role | Status entering this sub-project | Status after this sub-project |
|---|---|---|
| Student | Gamified shell shipped; hero has empty right space | Hero `greeting | hero-widget` split; right rail with upcoming + activity |
| Teacher | Editorial shell shipped; hero has empty right space | Hero split + right rail with pending grading + student wins |
| Registrar | Operations Mode shipped (PR #18) | Polish backported; right rail with today's transactions + handoffs |
| Coil Admin | Operations Mode shipped (PR #20) | Polish backported; right rail with upcoming joint sessions + partner news |
| Academic Director | Operations Mode shipped (PR #21) | Polish backported; right rail with pending decisions + content runway |
| IT Admin | Operations Mode shipped (PR #22) | Polish backported; right rail with failed-login + Celery snapshots |
| **Program Head** | **No dashboard** | **Operations Mode deep-dive shipped, with hero widget and right rail** |
| Principal | (out of scope) | (out of scope — design seam reserved) |

## 4. Architecture

### 4.1 Shared skeleton — `templates/role_skeleton.html`

Holds only the truly common chrome: doctype, viewport, CSRF token meta, favicon, Open Graph, theme color, skip-link, and a small set of blocks the role-bases fill in.

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
  <meta property="og:title" content="{{ SCHOOL_NAME }}">
  <meta property="og:type" content="website">
  <meta property="og:image" content="{{ request.scheme }}://{{ request.get_host }}{{ MEDIA_URL }}logos/HCCCI-logo.png?{{ logo_update_time }}">
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

The skeleton does not know about Teacher/Student/Operations. No conditional logic. Roughly 25 lines.

### 4.2 Each role-base extends the skeleton

Same block contract across all three role-bases:

```django
{% extends 'role_skeleton.html' %}
{% block fonts %}…{% endblock %}        {# role-specific fonts #}
{% block theme_css %}…{% endblock %}    {# role-specific theme stylesheet #}
{% block body %}
  <div class="app">
    <aside class="sidebar">…role's sidebar treatment…</aside>
    <main id="main" class="content">
      <header class="hero">
        <div class="greeting">{% block greeting %}{% endblock %}</div>
        <aside class="hero-widget">{% block hero_widget %}{% endblock %}</aside>
      </header>
      <div class="content-grid">
        <section class="content-main">{% block content %}{% endblock %}</section>
        <aside class="right-rail">{% block right_rail %}{% endblock %}</aside>
      </div>
    </main>
  </div>
{% endblock %}
```

Per-role differences live entirely in `{% block fonts %}`, `{% block theme_css %}`, and the `<aside class="sidebar">` content + CSS. Block names exposed to dashboards (`greeting`, `hero_widget`, `content`, `right_rail`) are identical across all three.

For Operations Mode the body block additionally renders the scope bar above the hero and the KPI strip + context strip in the appropriate slots — preserving the Wave A authoring contract.

### 4.3 Shell grid CSS

Lives in each role's stylesheet (so Bricolage / Fraunces / Operations spacing tokens stay independent) but the structural rules are identical:

```css
.app { display: grid; grid-template-columns: 240px 1fr; min-height: 100vh; }

.content { display: grid; grid-template-rows: auto 1fr; padding: 32px 40px; }

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

.right-rail { position: sticky; top: 32px; align-self: start; }
.right-rail:empty { display: none; }
.content-grid:has(.right-rail:empty) { grid-template-columns: 1fr; }

@media (max-width: 1280px) {
  .content-grid { grid-template-columns: 1fr; }
  .right-rail { position: static; }
  .right-rail .rail-card { display: inline-block; width: 48%; }
}

@media (max-width: 900px) {
  .app { grid-template-columns: 1fr; }
  .hero { grid-template-columns: 1fr; }
  .right-rail .rail-card { display: block; width: 100%; }
}
```

If a dashboard does not provide a `right_rail` block, `.right-rail` is empty and the `:has` rule collapses the grid to one column — **right rail is opt-in, never mandatory**.

### 4.4 Per-dashboard authoring contract

```django
{% extends 'student_base.html' %}      {# or teacher_base.html / operations_base.html #}
{% block greeting %}…{% endblock %}
{% block hero_widget %}…{% endblock %}
{% block content %}…{% endblock %}
{% block right_rail %}…{% endblock %}
```

Existing dashboards that do not yet fill `hero_widget` / `right_rail` continue to render — the blocks are empty by default.

## 5. Operations Mode polish bar deltas

These upgrades land in PR #2 (alongside Program Head) by editing `static/css/operations_base.css` and the four shared partials. PR #3 is a mechanical backport for the four Wave A dashboards.

### 5.1 Visual depth

New tokens added to `operations_base.css`:

```css
--shadow: 0 1px 2px rgba(45,49,66,.03), 0 12px 32px -12px rgba(45,49,66,.08);
--shadow-hover: 0 2px 4px rgba(45,49,66,.04), 0 20px 48px -16px rgba(45,49,66,.12);
--radius: 16px;
--radius-sm: 10px;
```

- `body` gets a radial-gradient + SVG-noise overlay matching `teacher_base.html`.
- `.kpi`, `.ops-primary`, `.ops-secondary`, `.context-col` get `box-shadow: var(--shadow)`, hover lift to `var(--shadow-hover)`.
- Sidebar gains a 1px gold rule on the brand block.

### 5.2 Motion

Single `prefers-reduced-motion` rule zeros out everything below.

| Element | Behavior |
|---|---|
| `.ops-btn` hover | 120ms `translateY(-1px)` + shadow lift |
| `.ops-nav-link` hover | 80ms ease bg + 4px gold left-rail slide-in for `.active` |
| Panel mount | 220ms fade-up on first paint |
| `.live-dot` | 1.6s ease pulse (forest → forest-2 → forest) |
| `.kpi.warn` | 4s ease-in-out gradient breathing (4% opacity range) |
| Sparkline | 600ms `stroke-dashoffset` draw on mount |

### 5.3 KPI affordances

Each KPI dict gains three optional keys; existing dashboards omitting them render identically.

```python
{
    'label': 'AT-RISK STUDENTS',
    'value': 23,
    'unit': '',
    'delta': '+4 vs last week',
    'delta_direction': 'up',     # NEW: 'up' | 'down' | 'flat'
    'delta_intent': 'bad',       # NEW: 'good' | 'bad' | 'neutral'
    'tone': 'warn',              # existing
    'sparkline': [12,14,16,15,18,21,23],  # NEW: optional 7–30 ints
}
```

Template renders a directional glyph (`↑` / `↓` / `→`) tinted by intent, plus an inline `<svg class="kpi-spark">` when `sparkline` is non-empty.

### 5.4 Worklist row affordances

```css
.worklist tbody tr { transition: background 80ms ease; }
.worklist tbody tr:hover { background: var(--gold-bg); cursor: pointer; }
.row-flagged { background: linear-gradient(90deg, var(--rose-soft) 0%, transparent 12%); }
.row-flagged td:first-child { border-left: 3px solid var(--rose); }
.row-flagged td:first-child::before { content: '!'; color: var(--rose-deep); font-weight: 700; margin-right: 6px; }
```

### 5.5 Empty states

```html
<div class="empty-state">
  <div class="empty-glyph" aria-hidden="true"></div>
  <p>{{ empty_message|default:"You're all caught up." }}</p>
  {% if empty_hint %}<p class="empty-hint">{{ empty_hint }}</p>{% endif %}
</div>
```

`.empty-glyph` is a 48px circle with forest-light fill and an inset gold checkmark — pure CSS, no asset.

### 5.6 Skeleton loaders

`.skeleton-line`, `.skeleton-block`, `.skeleton-kpi` ship with a 1.6s shimmer animation. Not used in this PR's dashboards (data is server-rendered today). Available for future HTMX upgrades.

### 5.7 Mobile responsive

Single 900px breakpoint matching Teacher's. Below it: sidebar collapses to top bar; `.kpi-strip` wraps to `repeat(2, 1fr)`; `.ops-grid` stacks; `.context-strip` stacks; right rail moves to bottom.

### 5.8 Accessibility

- Skip-to-content link as first body child (provided by `role_skeleton.html`).
- Custom focus ring: `outline: 2px solid var(--gold); outline-offset: 2px;` on every `:focus-visible`.
- Contrast fix: `--ink-muted` darkened from `#a0a4b8` (3.4:1, fails WCAG AA) to `#7a8099` (4.6:1, passes).
- Icon-only buttons get `aria-label`.
- `<table>` worklists get `<caption class="visually-hidden">{{ title }}</caption>`.
- `aria-live="polite"` on the live-dot timestamp.

### 5.9 Print stylesheet

`@media print { … }` hides sidebar, scope-bar live indicator, and quick-actions; forces white background, drops shadows and gradients; applies `page-break-inside: avoid` per worklist row.

### 5.10 JetBrains Mono actually loaded

Already declared in `<link>` in operations_base. CSS gets `.mono { font-family: 'JetBrains Mono', monospace; font-feature-settings: 'tnum' 1; }`. Applied to: live-dot timestamp, IT Admin IP/ID columns, attendance-day labels, future log surfaces.

## 6. Program Head dashboard

### 6.1 Identity

| Field | Value |
|---|---|
| Glyph | `◆` |
| Role tag | `PROGRAM HEAD` |
| Walk-in question | *Within my department, which courses or sections are off-track this week — and which teachers need backup?* |
| Department resolution | `Department.objects.filter(head=request.user)` — falls back to a graceful "no department assigned" empty-shell state. |
| Greeting | `Good {time_of_day}, {first_name}` |

### 6.2 Scope bar

Three pills computed view-side:

- **Department** · `{department.name}` (e.g., `BS Computer Science`)
- **Term** · `{current_term.label}`
- **Cadence** · `{department.cadence}` (only if set)

Right-aligned: live timestamp + pulsing dot.

### 6.3 Hero KPIs (5)

Locked at 5 per parent spec §5.1 (deep-dive treatment).

| # | Label | Value | Delta | Tone | Sparkline |
|---|---|---|---|---|---|
| 1 | DEPT AVG SCORE | weighted avg of latest activity scores in dept (current term) | vs school avg same term | `warn` if `< school_avg − 3` | 7-week dept avg trend |
| 2 | AT-RISK STUDENTS | count of dept students flagged by existing at-risk signal | vs 7d ago | `warn` if `Δ > 0` | 7-week count |
| 3 | TEACHER COVERAGE | `staffed / total subjects this term × 100`% | vs last term | `warn` if `< 95%` | none |
| 4 | OUTSTANDING RATINGS | `TeacherRating` pending review | vs 7d ago | `warn` if `> 0` | none |
| 5 | SCHEDULE INTEGRITY | `sessions_held / sessions_scheduled this week × 100`% | vs last week | `warn` if `< 90%` | 4-week trend |

KPIs 3 and 4 are administrative state, not trended quantities — sparkline omitted intentionally. Each KPI is a top-level function in the view module (`_kpi_dept_avg_score(department, term)`, etc.) so tests call it directly without rendering.

### 6.4 Hero widget — "Department pulse"

Right of greeting. Compact card with at-risk count + Δ + 7-day sparkline + a single CTA: *Open at-risk roster*. ~280px tall. Same data source as KPI #2 — purposefully the highest-priority anomaly surfaced both as a KPI and at the page's most-attentive zone.

### 6.5 Primary panel — Course Health

Note: parent spec calls these "CourseOfferings"; in this repo the equivalent is **Subject in current Term** (subjects belong to a Course/program, scheduled per term via `SubjectEnrollment`). Panel header reads "Course Health"; rows are subjects-this-term filtered to the head's department.

**Columns:** Subject · Teacher · Section · Enrolled (`{active}/{capacity}`) · Avg · Attn · Flags
**Sort:** by *trouble score* desc, where `trouble = max(0, (70 − avg_score)) × 0.6 + max(0, (90 − attn_pct)) × 0.4`. Anything `> 0` flags the row.
**Flag rules:** `avg < 70` OR `attn < 85%` OR `unstaffed` OR `≥ 2 missing submissions today`.
**Click target:** existing course/subject detail page.
**Empty state:** *"No courses in {department.name} this term — content is flowing."* with the empty-glyph.

### 6.6 Secondary panel — Teacher Pulse ("who needs support this week")

Reframing locked by parent spec §5.1: **NOT a leaderboard.** Same `TeacherGamification` data read inversely.

**Columns:** Teacher · Subjects · IP Δ 7d · Outstanding ratings · Flagged classes
**Sort:** `support_score = max(0, −ip_delta_7d) × 0.5 + outstanding × 30 + flagged_count × 50` desc. Top 5 visible; `▼ show all` toggle.
**Sub-header copy:** literal italic "*who needs support this week*". Never "leaderboard", "top teachers", "rank".
**Click target:** existing teacher detail view.
**Empty state:** *"Every teacher in your department is steady — no one needs backup right now."*

`total_ip` is read but **never rendered as a number in this panel** — re-rendering it would re-enable the leaderboard pattern the spec forbids.

### 6.7 Right rail

Sticky at desktop ≥ 1280px. Three cards top-to-bottom:

1. **Today** — next 5 events from `calendars.Event` filtered to `department=department`, with date · title · audience tag (Faculty / Students / Both). Past 24h items hidden.
2. **Outstanding ratings** — only when KPI #4 > 0. Inline list of pending `TeacherRating` objects with one-click "Review" link. Caps at 5 with "+N more" trailing link.
3. **Announcements** — last 3 dept-scoped `Announcement` objects, newest first.

Empty rail (no events, no ratings, no announcements) collapses via the `:has(.right-rail:empty)` rule from §4.3.

### 6.8 Quick actions in greeting (top-right)

- **Secondary**: `View department roster` (links to existing user list filtered by `Profile.department_fields=department`).
- **Primary**: `Approve ratings ({count})` if KPI #4 > 0; otherwise `New announcement` (existing dept-scoped announcement form).

### 6.9 Sidebar nav

| Section | Items |
|---|---|
| Top | Dashboard (active) · My Department |
| Department | Courses · Subjects · Faculty · Students |
| Operations | Calendar · Announcements · Syllabus plans |
| Bottom | Settings |

URLs map to existing Django URL names. If a link target doesn't exist yet (e.g., a dept-scoped roster filter), it falls back to the unfiltered page — consistent with how Wave A handled the same gap.

### 6.10 Principal sharing seam

Per parent spec §3, Principal will share this exact dashboard later. The view module exposes `_build_context(user, department)` as the public seam; a future Principal view will call the same builder, override only `glyph='☗'`, `role_tag='PRINCIPAL'`, and the scope-bar copy ("Grade 11 STEM" instead of "BS Computer Science"). No template changes will be needed for Principal — locked here so the template doesn't accidentally couple to Program Head copy.

## 7. Per-role hero widget + right rail content

Authored as part of PR #1 (Student/Teacher) and PR #3 (the four Wave A roles).

| Role | Hero widget (right of greeting) | Right rail (sticky desktop) |
|---|---|---|
| Student | "Today's mission" — next assignment due + countdown to deadline (most actionable single signal). Streak/freeze data stays in the existing hero chips. | Upcoming (next 3 deadlines · next class · next quest) + recent activity feed (3 items) |
| Teacher | "Your day at a glance" — next class, time, room, student count | Pending (papers to grade · ratings to write · messages) + recent student wins |
| Program Head | Department pulse (at-risk + Δ + sparkline + CTA) | Today + outstanding ratings + announcements (per §6.7) |
| Registrar | "Today's queue" — count of requests aging past SLA | Today's transactions + recent admin handoffs |
| Coil Admin | "Pipeline this week" — invites sent + responded | Upcoming joint sessions + partner news |
| Academic Director | "Coverage drift" — programs trending below intent + sparkline | Pending decisions shortcut + this-term content runway |
| IT Admin | "System status" — ring of green/yellow/red services | Failed-login alerts (last hour) + Celery queue snapshots |

## 8. PR breakdown

Three PRs targeting `main`, opened against `personal` remote, merge commits, branches deleted on merge — same conventions as Wave A.

### 8.1 PR #1 — `feat/shared-role-skeleton-and-right-rail` (~600 lines)

**Goal:** Architectural foundation. Extract shared chrome, introduce 3-column shell, fix right-side empty space across Student / Teacher / Operations.

| Action | File | Notes |
|---|---|---|
| **Add** | `templates/role_skeleton.html` | The new shared parent (~25 lines). |
| **Modify** | `templates/student_base.html` | Extends skeleton. Hero split, right-rail container added. Block names exposed: `greeting`, `hero_widget`, `content`, `right_rail`. ~80 lines net change (mostly removals from `<head>`). |
| **Modify** | `templates/teacher_base.html` | Same structural extraction. Translucent sidebar + Fraunces palette preserved. ~120 lines net (Teacher's was the largest at 629 lines). |
| **Modify** | `templates/operations_base.html` | Extends skeleton. Hero split, right-rail container. Scope bar still renders above hero; KPI strip and context strip in their existing slots. ~30 lines net. |
| **Modify** | `static/css/student_theme.css` | Hero grid + content-grid CSS, mobile breakpoints. |
| **Modify** | `static/css/operations_base.css` | Same shell grid rules. |
| **Modify** | `templates/teacher_base.html` inline `<style>` | Same shell grid rules. |
| **Add** | Hero widget + right rail content for Student `dashboard.html` | Server-rendered from existing data — no view changes. |
| **Add** | Hero widget + right rail content for Teacher `dashboard.html` | Same. |
| **Add** | `accounts/tests/test_shared_skeleton.py` | Verifies skip-link first focusable, OG meta tags present, `data-current-user-id` set, all three role-bases extend `role_skeleton.html`. |

**Verification:** Existing Student / Teacher / Operations dashboards render with their identities intact; right side of hero is no longer bare; right rail visible on desktop ≥ 1280px and collapses correctly below.

### 8.2 PR #2 — `feat/program-head-with-polished-shell` (~900 lines)

**Goal:** Ship Program Head dashboard *and* upgrade the shared Operations Mode shell to the new polish bar in one cohesive change.

| Action | File | Notes |
|---|---|---|
| **Add** | `accounts/views/program_head_dashboard.py` | View + `_build_context(user, department)` seam. Standalone function per KPI. |
| **Add** | `templates/operations/program_head_dashboard.html` | Extends `operations_base.html`. Overrides `primary_panel`, `secondary_panel`, `hero_widget`, `right_rail`. |
| **Add** | `accounts/tests/test_program_head_dashboard.py` | ~12–15 tests across Render / Permissions / KPIs (per §10.2). |
| **Modify** | `accounts/views/dashboard.py` | Add `is_program_head` branch + import. |
| **Modify** | `accounts/urls.py` | One new URL: `program_head_dashboard`. |
| **Modify** | `templates/operations_base.html` | Add `id="main"` on `<main>`, JetBrains Mono on `as_of` and `.mono`, panel transition wrappers. ~15 lines delta. |
| **Modify** | `templates/operations/kpi_strip.html` | Render `delta_direction`, `delta_intent`, `sparkline` (all optional). ~25 lines delta. |
| **Modify** | `templates/operations/scope_bar.html` | Pulse class on `.live-dot`; `.mono` on `as_of`. ~3 lines delta. |
| **Modify** | `templates/operations/worklist_panel.html` | Replace empty fallback with `.empty-state` block. ~10 lines delta. |
| **Modify** | `templates/operations/context_strip.html` | Same. ~6 lines delta. |
| **Modify** | `static/css/operations_base.css` | All polish bar deltas (per §5). Current 87 lines → ~440. ~350 lines delta. |

**Verification:** All four existing dashboards still render identically (existing partials are backward-compatible — new fields optional). Program Head returns 403 for non-PH users. Empty-department PH user sees graceful empty shell, not a 500.

### 8.3 PR #3 — `chore/operations-mode-polish-backport-and-rails` (~400 lines)

**Goal:** Wire the four Wave A dashboards into the polish affordances PR #2 made available, and add their hero widgets + right rails.

| Action | File | Notes |
|---|---|---|
| **Modify** | `accounts/views/registrar.py` | Add `delta_direction`, `delta_intent`, `sparkline` to KPI dicts. Add `hero_widget` + `right_rail` context. |
| **Modify** | `accounts/views/coil_admin.py` | Same enrichment. |
| **Modify** | `accounts/views/academic_director.py` | Same. Sparklines for at-risk + outcome attainment trend (data in `gamification`). |
| **Modify** | `accounts/views/it_admin.py` | Same. Sparklines for active-users-24h + Celery queue depth. |
| **Modify** | `templates/operations/registrar_dashboard.html` | Update empty-state copy: warmer phrasing. Add `hero_widget` + `right_rail` blocks. |
| **Modify** | `templates/operations/coil_admin_dashboard.html` | Same. Re-skin "Coming soon — model pending" as `.empty-state`. |
| **Modify** | `templates/operations/academic_director_dashboard.html` | Same. |
| **Modify** | `templates/operations/it_admin_dashboard.html` | Same. Re-skin service-health placeholder as `.empty-state`. |
| **Modify** | `accounts/tests/test_*_dashboard.py` (×4) | One assertion per file: KPI sparkline SVG present where data exists; updated empty-state copy renders. |
| **Modify** | `docs/superpowers/specs/2026-04-27-wave-a-finish-design.md` | Footer note: *"Polish backport applied in `chore/operations-mode-polish-backport-and-rails`."* |

**No file additions** in PR #3. No new CSS. No new partials. The polish is already in shared CSS from PR #2; the backport's job is to consume it.

**Verification:** Open all four dashboards in dev side-by-side with screenshots taken before PR #2 merge. Eyeball confirms motion/depth/empties look right and nothing regressed.

## 9. Routing changes

`accounts/views/dashboard.py` adds one new branch (PR #2):

```python
is_program_head = role_name == 'program head'
if is_program_head:
    return program_head_dashboard(request)
```

Routing for Teacher / Student / IT Admin / Registrar / Coil Admin / Academic Director is untouched.

## 10. Testing strategy

### 10.1 Conventions

- Pytest with `pytest-django`. No Playwright. Manual visual eyeballing for polish/regression.
- Reuse `accounts/tests/operations_dashboard_mixin.py` (added in PR #16). Provides authenticated request factory, role fixtures, current-term fixture, empty-department fixture.
- One test module per role: `accounts/tests/test_<role>_dashboard.py`.
- Each test module structured: `class TestXDashboardRender`, `class TestXDashboardPermissions`, `class TestXDashboardKPIs`.

### 10.2 PR #1 — Skeleton + right rail tests

`accounts/tests/test_shared_skeleton.py` (~6 tests):

- `test_skip_link_is_first_focusable` — skip-link is first interactive element on every role-base render.
- `test_csrf_meta_present_in_all_role_bases` — Student/Teacher/Operations all carry `<meta name="csrf-token">`.
- `test_og_meta_present` — Open Graph tags rendered in all three.
- `test_data_current_user_id_set` — `<body data-current-user-id="…">` present.
- `test_role_skeleton_extension` — assert each role-base contains `{% extends 'role_skeleton.html' %}`.
- `test_right_rail_collapses_when_empty` — render a dashboard that omits `{% block right_rail %}`; assert `.content-grid` has single column (CSS class assertion via inline style match — narrow but adequate).

### 10.3 PR #2 — Program Head + polish tests

`accounts/tests/test_program_head_dashboard.py` (~12–15 tests):

| Class | Test |
|---|---|
| `TestProgramHeadDashboardRender` | `test_renders_for_program_head_with_department` |
| | `test_empty_department_state_renders_without_500` |
| | `test_renders_all_5_kpis` |
| | `test_course_health_sort_floats_trouble_to_top` |
| | `test_teacher_pulse_never_renders_ip_as_number` *(asserts `total_ip` int literal absent in HTML — guards leaderboard regression)* |
| | `test_teacher_pulse_subheader_uses_support_copy` |
| | `test_hero_widget_at_risk_card_renders` |
| | `test_right_rail_today_announcements_outstanding_ratings_render` |
| `TestProgramHeadDashboardPermissions` | `test_403_for_non_program_head` |
| | `test_403_for_program_head_of_different_department` |
| | `test_redirects_anon_user` |
| `TestProgramHeadDashboardKPIs` | `test_kpi_dept_avg_score_returns_delta_vs_school` |
| | `test_kpi_at_risk_with_zero_students` |
| | `test_kpi_teacher_coverage_partial_staffing` |
| | `test_kpi_outstanding_ratings_pending_only` |
| | `test_kpi_schedule_integrity_uses_dept_calendar` |

Polish-foundation regression coverage added to the existing test mixin so all 5 dashboards inherit:

- `test_kpi_strip_handles_optional_fields_absent` — KPIs without `sparkline` / `delta_direction` / `delta_intent` render unchanged. **Regression guard for PR #3.**
- `test_empty_state_renders_for_empty_worklist` — uses new `.empty-state` block.

### 10.4 PR #3 — Polish backport tests

For each of the four existing test files:

- One assertion that any KPI carrying a sparkline now contains `<svg class="kpi-spark">` in the rendered HTML.
- One assertion that the upgraded empty-state copy renders.
- Total: ~6 lines × 4 files ≈ 25 lines.

### 10.5 What we are explicitly NOT testing

| Not tested | Why |
|---|---|
| Visual regression (pixel diffs) | No screenshot infra in repo; cost of adding > value for one polish pass. Manual eyeball before merge. |
| Animations literally animating | `prefers-reduced-motion` rule presence is the worthwhile assertion — covered implicitly by stylesheet check. |
| Mobile responsive at every breakpoint | One smoke test that the 900px / 1280px media queries are present. Manual check at 375 / 768 / 1280 / 1920. |
| Print stylesheet | Manual `Cmd+P` once before merge. |
| Full WCAG audit | Out of scope. Color-contrast token fix and focus rings address the highest-priority issues. Future a11y sub-project. |

### 10.6 Pre-merge manual checklist (per PR)

- Render the new/affected dashboards at desktop, confirm motion is smooth.
- Tab through each page; confirm focus rings visible and skip-link reachable.
- Toggle `prefers-reduced-motion` in devtools; confirm motion stops.
- Resize to 375px, 768px, 1280px, 1920px; confirm sidebar/hero/grids/right-rail behave per breakpoint rules.
- `Cmd+P`; confirm sidebar hidden, worklist prints clean.
- Inspect that `<svg class="kpi-spark">` only renders where `sparkline` data exists — never empty SVG.
- For PR #3 only: open all four Wave A dashboards, eyeball-confirm nothing visually regressed.

## 11. Out of scope

- Principal dashboard implementation (design seam reserved; build deferred).
- Adding gamification mechanics (XP / badges / streaks / leaderboards) to non-Teacher / non-Student roles. Reaffirmed.
- Re-platforming Operations Mode onto literal `teacher_base.html`.
- HTMX / async loading wired up. Skeleton CSS is added for future use; data is server-rendered as today.
- Dark mode for Operations Mode.
- Touching legacy `base.html`. Bootstrap-based legacy pages keep their current chrome.
- New Django apps, models, or migrations.
- Automated visual regression (Playwright pixel diffs).
- Wave B / C / D roles from the parent spec — Time Keeper, QA, Department Staff, Librarian, Guidance Counselor, Parent/Guardian. Each is its own future sub-project.

## 12. Open questions

- **Hero widget data ceiling.** If a role's hero widget data source is missing (e.g., Coil Admin "invites this week" requires a column not yet on `CoilPartnerSchool`), the widget falls back to the empty state pattern. Documented per role in PR #3 description.
- **Empty department recovery.** When a Program Head loses their `Department.head` assignment (e.g., reassigned by IT Admin), the dashboard renders an empty shell with a single CTA: *"Contact IT Admin to assign a department"*. This is not a 500 condition.

## 13. References

- Parent spec §4 (Operations Mode shell anatomy)
- Parent spec §5.1 (Program Head deep-dive data hierarchy)
- Wave A spec §3 (PR cadence pattern)
- Student dashboard redesign spec §3 (Bricolage theme tokens)
- Teacher dashboard SP1 design (Fraunces palette + translucent sidebar)
