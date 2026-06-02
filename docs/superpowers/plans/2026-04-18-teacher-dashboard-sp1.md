# Teacher Dashboard SP1: Design System + Analytics Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the generic teacher dashboard with a data-rich analytics dashboard using a new Fraunces/cream/forest/gold design system, surfacing real student performance metrics from existing models.

**Architecture:** New `teacher_base.html` base template with full CSS from the mockup. New `teacher_dashboard` view in `gamification/views.py` queries StudentActivity, SubjectEnrollment, StudentGamification, StudentProgress, and the at_risk calculator. The existing `accounts/views/dashboard.py` routes teachers to the new view. Context processor extended with `is_teacher_role`.

**Tech Stack:** Django 5.0.7, PostgreSQL. Design: Fraunces + Inter Tight fonts, CSS variables, card-based layout. No JS frameworks.

**Test command:** `~/classedge/env/bin/python manage.py test <app.tests.module> --keepdb -v2`

---

## File Structure

### New Files
| File | Responsibility |
|------|---------------|
| `templates/teacher_base.html` | Teacher design system: CSS variables, fonts, sidebar, layout grid |
| `gamification/teacher_dashboard.py` | `teacher_dashboard` view function + helper queries |
| `gamification/tests/test_teacher_dashboard.py` | All tests for this feature |

### Modified Files
| File | Changes |
|------|---------|
| `gamification/context_processors.py` | Add `is_teacher_role` flag |
| `accounts/views/dashboard.py:26-53` | Route teacher to new view |
| `gamification/urls.py` | No URL changes needed — dashboard URL is in accounts |

---

### Task 1: Context Processor — Add `is_teacher_role`

**Files:**
- Modify: `gamification/context_processors.py`
- Test: `gamification/tests/test_teacher_dashboard.py`

- [ ] **Step 1: Write the failing test**

Create `gamification/tests/test_teacher_dashboard.py`:

```python
from django.test import TestCase, Client, RequestFactory
from ai_content.tests.test_models import _create_test_user
from gamification.context_processors import student_context


class ContextProcessorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.teacher = _create_test_user(username="cp_teach", role_name="teacher")
        self.student = _create_test_user(username="cp_stu", role_name="student")

    def test_teacher_gets_is_teacher_role(self):
        request = self.factory.get("/")
        request.user = self.teacher
        request.COOKIES = {}
        ctx = student_context(request)
        self.assertTrue(ctx["is_teacher_role"])
        self.assertFalse(ctx["is_student_role"])

    def test_student_does_not_get_is_teacher_role(self):
        request = self.factory.get("/")
        request.user = self.student
        request.COOKIES = {}
        ctx = student_context(request)
        self.assertFalse(ctx["is_teacher_role"])
        self.assertTrue(ctx["is_student_role"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `~/classedge/env/bin/python manage.py test gamification.tests.test_teacher_dashboard.ContextProcessorTests --keepdb -v2`
Expected: FAIL — `is_teacher_role` not in returned dict

- [ ] **Step 3: Update context processor**

Replace `gamification/context_processors.py` entirely:

```python
def student_context(request):
    """Provide is_student_role, is_teacher_role, and theme_preference to all templates."""
    if not request.user.is_authenticated:
        return {"is_student_role": False, "is_teacher_role": False, "theme_preference": "dark"}

    role_name = ""
    if hasattr(request.user, "profile") and request.user.profile.role:
        role_name = request.user.profile.role.name.lower()

    theme = request.COOKIES.get("theme", "dark")
    return {
        "is_student_role": role_name == "student",
        "is_teacher_role": role_name in ("teacher", "admin"),
        "theme_preference": theme,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `~/classedge/env/bin/python manage.py test gamification.tests.test_teacher_dashboard.ContextProcessorTests --keepdb -v2`
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add gamification/context_processors.py gamification/tests/test_teacher_dashboard.py
git commit -m "feat(gamification): add is_teacher_role to context processor"
```

---

### Task 2: `teacher_base.html` Template

**Files:**
- Create: `templates/teacher_base.html`

- [ ] **Step 1: Create the template**

Create `templates/teacher_base.html`. This is the full design system from the mockup — CSS variables, fonts, sidebar, layout. The template must include `{% load static %}` and standard Django blocks.

```html
{% load static %}
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<meta name="csrf-token" content="{{ csrf_token }}" />
<title>{% block title %}ClassEdge · Faculty{% endblock %}</title>

<link rel="icon" type="image/png" href="{{ MEDIA_URL }}logos/HCCCI-logo.png?{{ logo_update_time }}" />
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,400;9..144,500;9..144,600;9..144,700&family=Inter+Tight:wght@400;500;600;700&display=swap" rel="stylesheet">

<style>
  :root {
    --cream: #faf7f2;
    --cream-2: #f3ede2;
    --paper: #ffffff;
    --forest: #1b4332;
    --forest-2: #2d5a47;
    --forest-light: #d9e4dd;
    --gold: #b7925a;
    --gold-soft: #e8d5b0;
    --gold-bg: rgba(183, 146, 90, 0.08);
    --rose: #c08479;
    --rose-soft: #f4e0dc;
    --ink: #2d3142;
    --ink-dim: #6c7080;
    --ink-muted: #a0a4b8;
    --border: rgba(45, 49, 66, 0.08);
    --border-strong: rgba(45, 49, 66, 0.14);
    --shadow: 0 1px 2px rgba(45,49,66,0.03), 0 12px 32px -12px rgba(45,49,66,0.08);
    --shadow-hover: 0 2px 4px rgba(45,49,66,0.04), 0 20px 48px -16px rgba(45,49,66,0.12);
    --display: 'Fraunces', serif;
    --body: 'Inter Tight', sans-serif;
    --radius: 16px;
    --radius-sm: 10px;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  html, body {
    background: var(--cream);
    color: var(--ink);
    font-family: var(--body);
    -webkit-font-smoothing: antialiased;
    min-height: 100vh;
    font-feature-settings: "ss01";
  }

  body {
    background:
      radial-gradient(ellipse at 10% 0%, rgba(183, 146, 90, 0.08) 0%, transparent 40%),
      radial-gradient(ellipse at 90% 100%, rgba(27, 67, 50, 0.05) 0%, transparent 50%),
      var(--cream);
    background-attachment: fixed;
    position: relative;
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

  .app {
    display: grid;
    grid-template-columns: 260px 1fr;
    min-height: 100vh;
    position: relative;
    z-index: 1;
  }

  /* ─── Sidebar ─────────────────────────────────── */
  .sidebar {
    padding: 32px 24px;
    border-right: 1px solid var(--border);
    background: rgba(255, 255, 255, 0.4);
    backdrop-filter: blur(10px);
    position: sticky;
    top: 0;
    height: 100vh;
  }

  .logo {
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin-bottom: 8px;
    font-family: var(--display);
    font-size: 26px;
    font-weight: 500;
    letter-spacing: -0.02em;
    color: var(--forest);
    text-decoration: none;
  }
  .logo-mark {
    display: inline-block;
    width: 38px; height: 38px;
    border-radius: 50%;
    background: var(--forest);
    color: var(--cream);
    display: grid; place-items: center;
    font-size: 18px; font-weight: 600;
    font-family: var(--display);
    font-style: italic;
    position: relative;
    transform: translateY(4px);
  }
  .logo-mark::after {
    content: '';
    position: absolute;
    inset: 3px;
    border-radius: 50%;
    border: 1px solid rgba(250, 247, 242, 0.3);
  }
  .institution {
    font-size: 11px;
    font-family: var(--body);
    color: var(--ink-dim);
    text-transform: uppercase;
    letter-spacing: 0.14em;
    margin-bottom: 40px;
    padding-left: 54px;
    font-weight: 500;
  }

  .nav-section {
    font-size: 10px;
    color: var(--ink-muted);
    text-transform: uppercase;
    letter-spacing: 0.14em;
    margin: 24px 14px 10px;
    font-weight: 600;
  }
  .nav { display: flex; flex-direction: column; gap: 2px; }
  .nav a {
    text-decoration: none;
    color: var(--ink-dim);
    padding: 11px 16px;
    border-radius: var(--radius-sm);
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.2s;
    position: relative;
  }
  .nav a:hover { color: var(--forest); background: rgba(27, 67, 50, 0.04); }
  .nav a.active {
    color: var(--forest);
    background: var(--forest-light);
    font-weight: 600;
  }
  .nav a.active::after {
    content: '';
    position: absolute;
    right: 14px;
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--gold);
  }
  .nav-icon { width: 18px; text-align: center; font-size: 15px; }

  .sidebar-footer {
    position: absolute; bottom: 24px; left: 24px; right: 24px;
    padding-top: 18px;
    border-top: 1px solid var(--border);
    display: flex; align-items: center; gap: 12px;
  }
  .avatar {
    width: 42px; height: 42px;
    border-radius: 50%;
    background: var(--forest);
    color: var(--cream);
    display: grid; place-items: center;
    font-family: var(--display);
    font-weight: 500;
    font-size: 17px;
    font-style: italic;
  }
  .user-meta-name { font-weight: 600; font-size: 13.5px; }
  .user-meta-role {
    font-family: var(--display);
    font-style: italic;
    color: var(--gold);
    font-size: 12px;
    font-weight: 500;
  }

  /* ─── Main ──────────────────────────────────── */
  main { padding: 40px 48px 80px; max-width: 1300px; }

  .topbar {
    display: flex; justify-content: space-between; align-items: flex-start;
    margin-bottom: 32px;
    animation: fadeDown 0.6s ease;
  }

  .page-title {
    font-family: var(--display);
    font-size: 34px;
    font-weight: 400;
    letter-spacing: -0.025em;
    color: var(--forest);
    line-height: 1.1;
    margin-bottom: 6px;
  }
  .page-title em {
    font-style: italic;
    color: var(--gold);
    font-weight: 300;
  }
  .page-sub {
    color: var(--ink-dim);
    font-size: 14px;
    font-family: var(--display);
    font-style: italic;
  }

  /* ─── Growth overview ──────────────────────── */
  .growth {
    background: var(--paper);
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 40px 44px;
    margin-bottom: 24px;
    box-shadow: var(--shadow);
    position: relative;
    overflow: hidden;
    animation: fadeUp 0.7s 0.05s both ease;
  }
  .growth::before {
    content: '';
    position: absolute;
    top: 0; right: 0;
    width: 360px; height: 360px;
    background: radial-gradient(circle at top right, rgba(183, 146, 90, 0.12), transparent 65%);
    pointer-events: none;
  }
  .growth-header {
    display: flex; align-items: flex-start; justify-content: space-between;
    margin-bottom: 32px; position: relative;
  }
  .growth-stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 40px;
    padding: 24px 0;
    border-top: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    margin-bottom: 28px;
    position: relative;
  }
  .growth-stat-label {
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.14em;
    color: var(--ink-muted); font-weight: 600; margin-bottom: 6px;
  }
  .growth-stat-value {
    font-family: var(--display); font-size: 28px; font-weight: 500;
    color: var(--forest); letter-spacing: -0.01em; font-variant-numeric: tabular-nums;
  }
  .growth-stat-sub {
    font-family: var(--display); font-style: italic;
    color: var(--ink-dim); font-size: 13px; margin-top: 4px;
  }

  .progress-section { position: relative; }
  .progress-labels {
    display: flex; justify-content: space-between;
    font-size: 12px; color: var(--ink-dim);
    margin-bottom: 10px; font-family: var(--display); font-style: italic;
  }
  .progress-labels .target { color: var(--gold); font-weight: 500; }
  .progress-track {
    height: 6px; background: var(--cream-2); border-radius: 100px;
    overflow: hidden; position: relative;
  }
  .progress-fill {
    height: 100%; background: linear-gradient(90deg, var(--forest) 0%, var(--forest-2) 80%, var(--gold) 100%);
    border-radius: 100px;
    animation: fillProgress 1.8s 0.4s cubic-bezier(0.22, 1, 0.36, 1) both;
    position: relative;
  }
  .progress-fill::after {
    content: '';
    position: absolute; right: -3px; top: 50%;
    width: 10px; height: 10px; border-radius: 50%;
    background: var(--gold); transform: translateY(-50%);
    box-shadow: 0 0 0 3px rgba(183, 146, 90, 0.2);
  }
  .progress-footer {
    font-family: var(--display); font-style: italic;
    color: var(--ink-dim); font-size: 13px; margin-top: 12px;
  }
  .progress-footer strong { color: var(--forest); font-weight: 600; }

  /* ─── Metric cards row ─────────────────────── */
  .metrics {
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 16px; margin-bottom: 24px;
  }
  .metric {
    background: var(--paper); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 22px 24px;
    box-shadow: var(--shadow); transition: all 0.3s;
    position: relative; overflow: hidden;
    animation: fadeUp 0.7s both ease;
  }
  .metric:nth-child(1) { animation-delay: 0.15s; }
  .metric:nth-child(2) { animation-delay: 0.22s; }
  .metric:nth-child(3) { animation-delay: 0.29s; }
  .metric:nth-child(4) { animation-delay: 0.36s; }
  .metric:hover { transform: translateY(-2px); box-shadow: var(--shadow-hover); }
  .metric-label {
    display: flex; align-items: center; gap: 8px;
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.12em;
    color: var(--ink-dim); font-weight: 600; margin-bottom: 16px;
  }
  .metric-icon {
    width: 24px; height: 24px; border-radius: 50%;
    background: var(--forest-light); color: var(--forest);
    display: grid; place-items: center; font-size: 12px;
  }
  .metric-value {
    font-family: var(--display); font-size: 32px; font-weight: 500;
    color: var(--forest); letter-spacing: -0.015em; line-height: 1;
    font-variant-numeric: tabular-nums;
  }
  .metric-value .unit {
    font-size: 16px; color: var(--ink-dim); font-weight: 400; font-style: italic;
  }
  .metric-caption {
    font-family: var(--display); font-style: italic;
    color: var(--forest-2); font-size: 12.5px; margin-top: 8px; font-weight: 500;
  }
  .metric-caption.positive::before { content: '▲ '; color: var(--forest-2); }
  .metric-caption.warn { color: var(--gold); }
  .metric-caption.warn::before { content: '◆ '; }

  /* ─── Classes ──────────────────────────────── */
  .classes {
    background: var(--paper); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 30px 34px;
    margin-bottom: 24px; box-shadow: var(--shadow);
    animation: fadeUp 0.7s 0.5s both ease;
  }
  .classes-header {
    display: flex; justify-content: space-between; align-items: baseline;
    margin-bottom: 24px;
  }
  .classes-list {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 18px;
  }
  .class-card {
    padding: 22px; background: var(--cream);
    border: 1px solid var(--border); border-radius: var(--radius-sm);
    transition: all 0.25s; cursor: pointer; position: relative;
    border-left: 3px solid var(--forest-2);
    text-decoration: none; color: inherit; display: block;
  }
  .class-card.warn { border-left-color: var(--gold); }
  .class-card.excellent { border-left-color: var(--forest); background: var(--forest-light); }
  .class-card:hover { transform: translateY(-2px); box-shadow: var(--shadow); }
  .class-name {
    font-family: var(--display); font-size: 17px; font-weight: 500;
    color: var(--forest); margin-bottom: 2px; letter-spacing: -0.01em;
  }
  .class-section {
    font-family: var(--display); font-style: italic;
    color: var(--ink-dim); font-size: 12px; margin-bottom: 18px;
  }
  .class-metrics {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 14px; margin-bottom: 16px;
  }
  .class-metric-label {
    font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em;
    color: var(--ink-muted); font-weight: 600; margin-bottom: 2px;
  }
  .class-metric-value {
    font-family: var(--display); font-size: 19px; font-weight: 500;
    color: var(--forest); font-variant-numeric: tabular-nums;
  }
  .class-metric-value.warn { color: var(--gold); }
  .class-metric-value.done { color: var(--forest-2); }
  .class-progress-label {
    font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.1em;
    color: var(--ink-muted); font-weight: 600; margin-bottom: 6px;
    display: flex; justify-content: space-between;
  }
  .class-progress-label span:last-child {
    color: var(--forest); font-variant-numeric: tabular-nums; font-size: 12px;
  }
  .class-progress-track {
    height: 5px; background: var(--cream-2); border-radius: 100px; overflow: hidden;
  }
  .class-progress-fill { height: 100%; background: var(--forest); border-radius: 100px; }
  .class-card.excellent .class-progress-fill { background: var(--forest); }
  .class-card.warn .class-progress-fill { background: var(--gold); }

  /* ─── Spotlight ────────────────────────────── */
  .spotlight {
    background: linear-gradient(135deg, var(--forest) 0%, var(--forest-2) 100%);
    color: var(--cream); border-radius: var(--radius);
    padding: 36px 40px;
    box-shadow: 0 24px 60px -20px rgba(27, 67, 50, 0.4);
    position: relative; overflow: hidden;
    animation: fadeUp 0.7s 0.55s both ease;
  }
  .spotlight::before {
    content: ''; position: absolute; top: -80px; right: -80px;
    width: 300px; height: 300px;
    background: radial-gradient(circle, var(--gold-soft), transparent 60%);
    opacity: 0.15; pointer-events: none;
  }
  .spotlight-label {
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.16em;
    color: var(--gold); font-weight: 600; margin-bottom: 10px;
  }
  .spotlight-title {
    font-family: var(--display); font-size: 26px; font-weight: 400;
    letter-spacing: -0.02em; line-height: 1.2; max-width: 640px; margin-bottom: 24px;
  }
  .spotlight-title em { font-style: italic; color: var(--gold); }
  .spotlight-list { list-style: none; border-top: 1px solid rgba(250, 247, 242, 0.15); }
  .spotlight-item {
    padding: 16px 0; border-bottom: 1px solid rgba(250, 247, 242, 0.1);
    display: flex; align-items: center; gap: 18px;
    font-size: 15px; font-family: var(--display); font-weight: 400;
  }
  .spotlight-item:last-child { border-bottom: none; padding-bottom: 0; }
  .spotlight-item strong { font-weight: 500; color: #fff; }
  .spotlight-item em { font-style: italic; color: var(--gold); font-weight: 500; }
  .spotlight-avatar {
    width: 44px; height: 44px; border-radius: 50%;
    background: var(--gold); color: var(--forest);
    display: grid; place-items: center;
    font-family: var(--display); font-weight: 600;
    font-style: italic; font-size: 17px; flex-shrink: 0;
  }
  .spotlight-cta {
    margin-top: 28px; display: inline-flex; align-items: center; gap: 10px;
    background: var(--cream); color: var(--forest);
    padding: 12px 24px; border: none; border-radius: 100px;
    font-family: var(--body); font-weight: 600; font-size: 13.5px;
    cursor: pointer; transition: all 0.25s; text-decoration: none;
  }
  .spotlight-cta:hover { transform: translateY(-1px); box-shadow: 0 12px 30px -10px rgba(0,0,0,0.3); }

  /* ─── Animations ─────────────────────────── */
  @keyframes fadeDown { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
  @keyframes fadeUp { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }
  @keyframes fillProgress { from { width: 0; } }

  @media (max-width: 1100px) {
    .metrics { grid-template-columns: 1fr 1fr; }
    .classes-list { grid-template-columns: 1fr; }
  }
  @media (max-width: 840px) {
    .app { grid-template-columns: 1fr; }
    .sidebar { display: none; }
    main { padding: 24px; }
    .metrics { grid-template-columns: 1fr; }
    .growth-stats { grid-template-columns: 1fr; gap: 24px; }
  }
</style>
{% block extra_css %}{% endblock %}
</head>
<body>

<div class="app">

  <!-- Sidebar -->
  <aside class="sidebar">
    <a href="{% url 'dashboard' %}" class="logo">
      <div class="logo-mark">C</div>
      ClassEdge
    </a>
    <div class="institution">Faculty · {{ SCHOOL_NAME|default:"ClassEdge" }}</div>

    <div class="nav-section">Teaching</div>
    <nav class="nav">
      <a href="{% url 'dashboard' %}"{% if request.resolver_match.url_name == 'dashboard' %} class="active"{% endif %}><span class="nav-icon">&#x25C9;</span> Dashboard</a>
      <a href="{% url 'viewGradeBookComponents' %}"{% if request.resolver_match.url_name == 'viewGradeBookComponents' %} class="active"{% endif %}><span class="nav-icon">&#x270E;</span> Gradebook</a>
      <a href="{% url 'attendance_report' %}"{% if request.resolver_match.url_name == 'attendance_report' %} class="active"{% endif %}><span class="nav-icon">&#x25A4;</span> Attendance</a>
    </nav>

    <div class="nav-section">Insight</div>
    <nav class="nav">
      <a href="{% url 'badge_management' %}"{% if request.resolver_match.url_name == 'badge_management' %} class="active"{% endif %}><span class="nav-icon">&#x2606;</span> Badges</a>
      <a href="{% url 'coding_overview' %}"{% if request.resolver_match.url_name == 'coding_overview' %} class="active"{% endif %}><span class="nav-icon">&#x25C8;</span> Coding</a>
    </nav>

    <div class="sidebar-footer">
      <div class="avatar">{{ request.user.first_name|default:request.user.username|make_list|first|upper }}</div>
      <div>
        <div class="user-meta-name">{{ request.user.get_full_name|default:request.user.username }}</div>
        <div class="user-meta-role">Faculty</div>
      </div>
    </div>
  </aside>

  <!-- Main content -->
  <main>
    {% block content %}{% endblock %}
  </main>
</div>

</body>
</html>
```

- [ ] **Step 2: Verify template has no syntax errors**

```bash
cd ~/classedge && ./env/bin/python -c "
from django.template.loader import get_template
import django; import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'lms.settings'
django.setup()
t = get_template('teacher_base.html')
print('Template loaded OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add templates/teacher_base.html
git commit -m "feat: add teacher_base.html design system template (Fraunces/cream/forest/gold)"
```

---

### Task 3: Teacher Dashboard View

**Files:**
- Create: `gamification/teacher_dashboard.py`
- Append tests to: `gamification/tests/test_teacher_dashboard.py`

- [ ] **Step 1: Write failing tests**

Append to `gamification/tests/test_teacher_dashboard.py`:

```python
from datetime import date
from django.test import override_settings
from activity.models.activity_model import Activity, ActivityType
from activity.models.student_activity_model import StudentActivity
from course.models.semester_model import Semester
from course.models.term_model import Term
from course.models.subject_enrollment_model import SubjectEnrollment
from subject.models.subject_model import Subject
from gamification.models import StudentGamification
from module.models.module import Module
from module.models.student_progress import StudentProgress

_GAM_SETTINGS = {
    "GAMIFICATION_XP_RATES": {
        "submission": 50, "early_submission": 75, "score_90": 30,
        "score_75": 15, "daily_login": 5, "perfect_attendance_week": 50,
    },
    "GAMIFICATION_STREAK_FREEZE_MONTHLY": 1,
    "AT_RISK_WEIGHTS": {"grade": 0.5, "completion": 0.3, "attendance": 0.2},
    "AT_RISK_HIGH_THRESHOLD": 40,
    "AT_RISK_MEDIUM_THRESHOLD": 65,
}


@override_settings(**_GAM_SETTINGS)
class TeacherDashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = _create_test_user(username="td_teach", role_name="teacher")
        self.student1 = _create_test_user(username="td_stu1", role_name="student")
        self.student2 = _create_test_user(username="td_stu2", role_name="student")
        from ai_content.tests.test_models import _create_subject
        self.subject = _create_subject()
        Subject.objects.filter(pk=self.subject.pk).update(assign_teacher=self.teacher)
        self.semester = Semester.objects.create(
            semester_name="Sem", start_date=date(2026, 1, 1), end_date=date(2027, 12, 31),
        )
        self.term = Term.objects.create(
            term_name="Prelim", semester=self.semester,
            start_date=date(2026, 8, 15), end_date=date(2026, 10, 15),
        )
        SubjectEnrollment.objects.create(
            student=self.student1, subject=self.subject,
            semester=self.semester, status="enrolled",
        )
        SubjectEnrollment.objects.create(
            student=self.student2, subject=self.subject,
            semester=self.semester, status="enrolled",
        )

    def test_teacher_sees_new_dashboard(self):
        self.client.login(username="td_teach", password="testpass")
        resp = self.client.get("/dashboard/")
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "gamification/teacher_dashboard.html")

    def test_student_does_not_see_teacher_dashboard(self):
        self.client.login(username="td_stu1", password="testpass")
        resp = self.client.get("/dashboard/")
        # Students get redirected to student_dashboard
        self.assertEqual(resp.status_code, 302)

    def test_dashboard_shows_subject_cards(self):
        self.client.login(username="td_teach", password="testpass")
        resp = self.client.get("/dashboard/")
        self.assertIn("subjects", resp.context)
        self.assertEqual(len(resp.context["subjects"]), 1)

    def test_dashboard_metric_cards_present(self):
        self.client.login(username="td_teach", password="testpass")
        resp = self.client.get("/dashboard/")
        self.assertIn("metrics", resp.context)
        self.assertEqual(len(resp.context["metrics"]), 4)

    def test_dashboard_spotlight_with_data(self):
        quiz_type, _ = ActivityType.objects.get_or_create(name="Quiz")
        # Student1: two activities, scores improving
        for i, score in enumerate([60, 90]):
            act = Activity.objects.create(
                activity_name=f"Quiz {i}", activity_type=quiz_type,
                subject=self.subject, term=self.term, max_score=100, is_graded=True,
            )
            StudentActivity.objects.create(
                student=self.student1, activity=act,
                subject=self.subject, term=self.term, total_score=score,
            )
        self.client.login(username="td_teach", password="testpass")
        resp = self.client.get("/dashboard/")
        self.assertIn("spotlight", resp.context)

    def test_empty_semester_no_crash(self):
        # Delete the semester so teacher has no current semester
        Semester.objects.all().delete()
        self.client.login(username="td_teach", password="testpass")
        resp = self.client.get("/dashboard/")
        self.assertEqual(resp.status_code, 200)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `~/classedge/env/bin/python manage.py test gamification.tests.test_teacher_dashboard.TeacherDashboardViewTests --keepdb -v2`
Expected: FAIL — template not found or view not wired

- [ ] **Step 3: Create the teacher dashboard view**

Create `gamification/teacher_dashboard.py`:

```python
from datetime import datetime

from django.conf import settings
from django.db.models import Avg, Count, Q
from django.shortcuts import render
from django.utils import timezone

from activity.models.activity_model import Activity
from activity.models.student_activity_model import StudentActivity
from course.models.semester_model import Semester
from course.models.subject_enrollment_model import SubjectEnrollment
from course.models.term_model import Term
from gamification.models import StudentGamification
from module.models.module import Module
from module.models.student_progress import StudentProgress
from subject.models.subject_model import Subject


def teacher_dashboard(request):
    user = request.user
    now = timezone.localtime(timezone.now())

    hour = now.hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    semester = Semester.objects.filter(
        start_date__lte=now.date(), end_date__gte=now.date(),
    ).first()

    # Teacher's subjects this semester
    teacher_subjects = Subject.objects.filter(
        Q(assign_teacher=user) | Q(substitute_teacher=user) | Q(collaborators=user),
    ).distinct()

    terms = Term.objects.filter(semester=semester) if semester else Term.objects.none()

    # ── Aggregate stats ────────────────────────────────────────
    total_students = 0
    if semester:
        total_students = SubjectEnrollment.objects.filter(
            semester=semester, status="enrolled", subject__in=teacher_subjects,
        ).values("student").distinct().count()

    active_subjects = teacher_subjects.count()

    # Overall class average
    overall_avg = _calc_overall_avg(teacher_subjects, terms)

    # At-risk counts
    at_risk_high, at_risk_medium = _calc_at_risk_counts(teacher_subjects, semester)

    # Completion rate
    completion_pct, submitted_count, total_possible = _calc_completion_rate(
        teacher_subjects, terms, semester,
    )

    # Active streaks
    streak_count, streak_pct = _calc_streak_stats(teacher_subjects, semester)

    # ── Metrics ────────────────────────────────────────────────
    metrics = [
        {
            "label": "Class Average",
            "icon": "&#x1F4CA;",
            "value": f"{overall_avg:.0f}",
            "unit": "%",
            "caption": f"across {active_subjects} subject{'s' if active_subjects != 1 else ''}",
            "caption_class": "positive" if overall_avg >= 75 else "warn",
        },
        {
            "label": "At-Risk",
            "icon": "&#x26A0;",
            "value": str(at_risk_high + at_risk_medium),
            "unit": "",
            "caption": f"{at_risk_high} high \u00b7 {at_risk_medium} medium",
            "caption_class": "warn" if at_risk_high > 0 else "positive",
        },
        {
            "label": "Completion",
            "icon": "&#x2714;",
            "value": f"{completion_pct:.0f}",
            "unit": "%",
            "caption": f"{submitted_count}/{total_possible} submissions",
            "caption_class": "positive" if completion_pct >= 80 else "warn",
        },
        {
            "label": "Active Streaks",
            "icon": "&#x1F525;",
            "value": str(streak_count),
            "unit": "",
            "caption": f"{streak_pct:.0f}% of students",
            "caption_class": "positive" if streak_pct >= 50 else "warn",
        },
    ]

    # ── Subject cards ──────────────────────────────────────────
    subjects = []
    for subj in teacher_subjects:
        avg = _calc_subject_avg(subj, terms)
        ungraded = _calc_ungraded(subj, terms, semester)
        module_pct = _calc_module_progress(subj, semester)

        if avg >= 85 and ungraded == 0:
            card_class = "excellent"
        elif ungraded > 5 or avg < 70:
            card_class = "warn"
        else:
            card_class = ""

        subjects.append({
            "subject": subj,
            "avg": round(avg, 1),
            "ungraded": ungraded,
            "module_pct": round(module_pct),
            "card_class": card_class,
        })

    # ── Spotlight (top improvers) ──────────────────────────────
    spotlight = _calc_spotlight(teacher_subjects, terms, semester)

    return render(request, "gamification/teacher_dashboard.html", {
        "greeting": greeting,
        "user_name": user.first_name or user.username,
        "total_students": total_students,
        "active_subjects": active_subjects,
        "overall_avg": round(overall_avg, 1),
        "metrics": metrics,
        "subjects": subjects,
        "spotlight": spotlight,
        "semester": semester,
    })


# ── Helper functions ───────────────────────────────────────────


def _calc_overall_avg(teacher_subjects, terms):
    if not terms.exists():
        return 0.0
    scores = StudentActivity.objects.filter(
        subject__in=teacher_subjects, term__in=terms,
        activity__is_graded=True, activity__max_score__gt=0,
    ).select_related("activity")
    if not scores.exists():
        return 0.0
    total_earned = sum(sa.total_score for sa in scores)
    total_possible = sum(sa.activity.max_score for sa in scores)
    return (total_earned / total_possible * 100) if total_possible > 0 else 0.0


def _calc_at_risk_counts(teacher_subjects, semester):
    if not semester:
        return 0, 0
    high_threshold = getattr(settings, "AT_RISK_HIGH_THRESHOLD", 40)
    medium_threshold = getattr(settings, "AT_RISK_MEDIUM_THRESHOLD", 65)
    high = 0
    medium = 0
    try:
        from at_risk.calculator import calculate_risk_scores
        for subj in teacher_subjects:
            results = calculate_risk_scores(subj, semester)
            for r in results:
                if r["risk_level"] == "high":
                    high += 1
                elif r["risk_level"] == "medium":
                    medium += 1
    except Exception:
        pass
    return high, medium


def _calc_completion_rate(teacher_subjects, terms, semester):
    if not semester or not terms.exists():
        return 0.0, 0, 0
    graded_activities = Activity.objects.filter(
        subject__in=teacher_subjects, term__in=terms, is_graded=True,
    )
    total_activities = graded_activities.count()
    if total_activities == 0:
        return 0.0, 0, 0

    enrolled_count = SubjectEnrollment.objects.filter(
        semester=semester, status="enrolled", subject__in=teacher_subjects,
    ).values("student").distinct().count()

    total_possible = total_activities * enrolled_count
    if total_possible == 0:
        return 0.0, 0, 0

    submitted = StudentActivity.objects.filter(
        activity__in=graded_activities,
    ).count()

    return (submitted / total_possible * 100), submitted, total_possible


def _calc_streak_stats(teacher_subjects, semester):
    if not semester:
        return 0, 0.0
    enrolled_ids = SubjectEnrollment.objects.filter(
        semester=semester, status="enrolled", subject__in=teacher_subjects,
    ).values_list("student_id", flat=True).distinct()

    total = len(set(enrolled_ids))
    if total == 0:
        return 0, 0.0

    with_streak = StudentGamification.objects.filter(
        student_id__in=enrolled_ids, login_streak__gt=0,
    ).count()

    return with_streak, (with_streak / total * 100)


def _calc_subject_avg(subject, terms):
    if not terms.exists():
        return 0.0
    scores = StudentActivity.objects.filter(
        subject=subject, term__in=terms,
        activity__is_graded=True, activity__max_score__gt=0,
    ).select_related("activity")
    if not scores.exists():
        return 0.0
    total_earned = sum(sa.total_score for sa in scores)
    total_possible = sum(sa.activity.max_score for sa in scores)
    return (total_earned / total_possible * 100) if total_possible > 0 else 0.0


def _calc_ungraded(subject, terms, semester):
    if not semester or not terms.exists():
        return 0
    graded_activities = Activity.objects.filter(
        subject=subject, term__in=terms, is_graded=True,
    )
    enrolled_count = SubjectEnrollment.objects.filter(
        semester=semester, status="enrolled", subject=subject,
    ).count()

    ungraded = 0
    for act in graded_activities:
        submitted = StudentActivity.objects.filter(activity=act).count()
        if submitted < enrolled_count:
            ungraded += 1
    return ungraded


def _calc_module_progress(subject, semester):
    if not semester:
        return 0.0
    modules = Module.objects.filter(subject=subject)
    total_modules = modules.count()
    if total_modules == 0:
        return 0.0

    enrolled_ids = SubjectEnrollment.objects.filter(
        semester=semester, status="enrolled", subject=subject,
    ).values_list("student_id", flat=True)

    if not enrolled_ids:
        return 0.0

    completed = StudentProgress.objects.filter(
        student_id__in=enrolled_ids, module__in=modules, completed=True,
    ).count()

    total_possible = total_modules * len(set(enrolled_ids))
    return (completed / total_possible * 100) if total_possible > 0 else 0.0


def _calc_spotlight(teacher_subjects, terms, semester):
    if not semester or not terms.exists():
        return []

    enrolled_ids = SubjectEnrollment.objects.filter(
        semester=semester, status="enrolled", subject__in=teacher_subjects,
    ).values_list("student_id", flat=True).distinct()

    improvers = []
    for student_id in set(enrolled_ids):
        scores = list(
            StudentActivity.objects.filter(
                student_id=student_id,
                subject__in=teacher_subjects,
                term__in=terms,
                activity__is_graded=True,
                activity__max_score__gt=0,
            ).select_related("activity").order_by("-activity__end_time", "-pk")[:10]
        )
        if len(scores) < 4:
            continue

        mid = len(scores) // 2
        recent = scores[:mid]
        older = scores[mid:]

        def avg_pct(sa_list):
            earned = sum(s.total_score for s in sa_list)
            possible = sum(s.activity.max_score for s in sa_list)
            return (earned / possible * 100) if possible > 0 else 0

        recent_avg = avg_pct(recent)
        older_avg = avg_pct(older)
        delta = recent_avg - older_avg

        if delta > 0:
            from accounts.models import CustomUser
            student = CustomUser.objects.filter(pk=student_id).first()
            if student:
                name = student.get_full_name() or student.username
                initial = (student.first_name or student.username)[0].upper()
                improvers.append({
                    "name": name,
                    "initial": initial,
                    "old_avg": round(older_avg),
                    "new_avg": round(recent_avg),
                    "delta": round(delta),
                })

    improvers.sort(key=lambda x: -x["delta"])
    return improvers[:3]
```

- [ ] **Step 4: Run tests to verify they still fail (template missing)**

Run: `~/classedge/env/bin/python manage.py test gamification.tests.test_teacher_dashboard.TeacherDashboardViewTests --keepdb -v2`
Expected: FAIL — template `gamification/teacher_dashboard.html` not found

- [ ] **Step 5: Commit (view only, template in next task)**

```bash
git add gamification/teacher_dashboard.py gamification/tests/test_teacher_dashboard.py
git commit -m "feat(gamification): add teacher dashboard view with analytics queries"
```

---

### Task 4: Teacher Dashboard Template

**Files:**
- Create: `gamification/templates/gamification/teacher_dashboard.html`

- [ ] **Step 1: Create the dashboard template**

Create `gamification/templates/gamification/teacher_dashboard.html`:

```html
{% extends "teacher_base.html" %}
{% block title %}ClassEdge · Faculty Dashboard{% endblock %}
{% block content %}

<!-- Top bar -->
<div class="topbar">
  <div>
    <h1 class="page-title">{{ greeting }}, <em>{{ user_name }}</em></h1>
    <div class="page-sub">Your classes at a glance &mdash; {% now "l, F j" %}</div>
  </div>
</div>

<!-- Growth overview -->
<section class="growth">
  <div class="growth-header">
    <div>
      <div class="growth-stat-label">Overview</div>
      <div class="growth-stat-value" style="font-size:32px;">{{ total_students }} <span style="font-size:16px;color:var(--ink-dim);font-style:italic;">students</span></div>
      <div class="growth-stat-sub">across {{ active_subjects }} subject{{ active_subjects|pluralize }}</div>
    </div>
    {% if semester %}
    <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.16em;color:var(--gold);font-weight:600;padding:10px 18px;border:1px solid var(--gold);border-radius:100px;background:var(--gold-bg);">
      {{ semester.semester_name }}
    </div>
    {% endif %}
  </div>

  <div class="growth-stats">
    <div>
      <div class="growth-stat-label">Overall Class Average</div>
      <div class="growth-stat-value">{{ overall_avg }}%</div>
      <div class="growth-stat-sub">Across all graded activities</div>
    </div>
    <div>
      <div class="growth-stat-label">Total Students</div>
      <div class="growth-stat-value">{{ total_students }}</div>
      <div class="growth-stat-sub">Currently enrolled</div>
    </div>
  </div>

  <div class="progress-section">
    <div class="progress-labels">
      <span>Overall class average</span>
      <span class="target">{{ overall_avg }}%</span>
    </div>
    <div class="progress-track"><div class="progress-fill" style="width: {{ overall_avg }}%;"></div></div>
  </div>
</section>

<!-- Metric cards -->
<section class="metrics">
  {% for m in metrics %}
  <div class="metric">
    <div class="metric-label"><span class="metric-icon">{{ m.icon }}</span> {{ m.label }}</div>
    <div class="metric-value">{{ m.value }}{% if m.unit %}<span class="unit"> {{ m.unit }}</span>{% endif %}</div>
    <div class="metric-caption {{ m.caption_class }}">{{ m.caption }}</div>
  </div>
  {% endfor %}
</section>

<!-- My Classes -->
<section class="classes">
  <div class="classes-header">
    <h2 style="font-family:var(--display);font-size:22px;font-weight:500;color:var(--forest);letter-spacing:-0.015em;">My <em style="font-style:italic;color:var(--gold);font-weight:400;">Classes</em></h2>
    {% if semester %}
    <div class="page-sub">{{ semester.semester_name }} &middot; {{ subjects|length }} active section{{ subjects|length|pluralize }}</div>
    {% endif %}
  </div>

  <div class="classes-list">
    {% for s in subjects %}
    <div class="class-card {{ s.card_class }}">
      <div class="class-name">{{ s.subject.subject_name }}</div>
      <div class="class-section">{{ s.subject.subject_code }}</div>
      <div class="class-metrics">
        <div>
          <div class="class-metric-label">Class Average</div>
          <div class="class-metric-value">{{ s.avg }}%</div>
        </div>
        <div>
          <div class="class-metric-label">Ungraded</div>
          <div class="class-metric-value{% if s.ungraded > 5 %} warn{% elif s.ungraded == 0 %} done{% endif %}">{{ s.ungraded }}{% if s.ungraded == 0 %} &#x2713;{% endif %}</div>
        </div>
      </div>
      <div class="class-progress-label"><span>Module progress</span><span>{{ s.module_pct }}%</span></div>
      <div class="class-progress-track"><div class="class-progress-fill" style="width: {{ s.module_pct }}%;"></div></div>
    </div>
    {% empty %}
    <div style="padding:40px;text-align:center;color:var(--ink-dim);font-family:var(--display);font-style:italic;">
      No subjects assigned this semester.
    </div>
    {% endfor %}
  </div>
</section>

<!-- Student Spotlight -->
{% if spotlight %}
<section class="spotlight">
  <div class="spotlight-label">Student Spotlight</div>
  <h2 class="spotlight-title">
    {% if spotlight|length == 1 %}A student improved this period{% else %}{{ spotlight|length }} students improved this period{% endif %} &mdash; <em>here's who</em>.
  </h2>

  <ul class="spotlight-list">
    {% for s in spotlight %}
    <li class="spotlight-item">
      <div class="spotlight-avatar">{{ s.initial }}</div>
      <div>
        <strong>{{ s.name }}</strong> jumped from <em>{{ s.old_avg }}% to {{ s.new_avg }}%</em> on recent activities.
      </div>
    </li>
    {% endfor %}
  </ul>

  <a href="{% url 'badge_manual_award' 1 %}" class="spotlight-cta">Send recognition &rarr;</a>
</section>
{% endif %}

{% endblock %}
```

Note: The `badge_manual_award` URL requires a badge_id. For the "Send recognition" CTA, we use badge ID 1 as a placeholder — in SP2 this will link to a proper recognition flow. If badge ID 1 doesn't work in all test scenarios, use `{% url 'badge_management' %}` instead.

Actually, to be safe, use `{% url 'badge_management' %}` which always resolves:

Replace the CTA line with:
```html
  <a href="{% url 'badge_management' %}" class="spotlight-cta">Send recognition &rarr;</a>
```

- [ ] **Step 2: Run tests — should still fail (routing not wired)**

Run: `~/classedge/env/bin/python manage.py test gamification.tests.test_teacher_dashboard.TeacherDashboardViewTests --keepdb -v2`
Expected: FAIL — dashboard still renders old template

- [ ] **Step 3: Commit template**

```bash
git add gamification/templates/gamification/teacher_dashboard.html
git commit -m "feat(gamification): add teacher dashboard template with mockup design"
```

---

### Task 5: Wire Dashboard Routing

**Files:**
- Modify: `accounts/views/dashboard.py:26-53`

- [ ] **Step 1: Update the dashboard view to route teachers**

In `accounts/views/dashboard.py`, add this import near the top (after line 18):

```python
from gamification.teacher_dashboard import teacher_dashboard as gamification_teacher_dashboard
```

In the `dashboard` function, find line 48 (`is_teacher = role_name == 'teacher'`) and the student redirect at line 52-53. After the student redirect, add a teacher redirect BEFORE the rest of the function continues. The block around lines 47-54 should become:

```python
    role_name = user.profile.role.name.lower() if hasattr(user, 'profile') and user.profile.role else ''
    is_teacher = role_name == 'teacher'
    is_student = role_name == 'student'
    is_registrar = role_name == 'registrar'

    if is_student:
        return redirect("student_dashboard")

    if is_teacher:
        return gamification_teacher_dashboard(request)
```

This replaces the teacher's dashboard rendering. The rest of the function (admin/registrar path) continues as before.

- [ ] **Step 2: Run tests to verify they pass**

Run: `~/classedge/env/bin/python manage.py test gamification.tests.test_teacher_dashboard --keepdb -v2`
Expected: All 8 tests PASS

- [ ] **Step 3: Run full test suite to check for regressions**

Run: `~/classedge/env/bin/python manage.py test gamification.tests ide.tests --keepdb`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add accounts/views/dashboard.py
git commit -m "feat: route teacher dashboard to new analytics view"
```

---

### Task 6: Full Integration Test + Push

**Files:** All modified files

- [ ] **Step 1: Run the full test suite**

```bash
cd ~/classedge && ./env/bin/python manage.py test gamification.tests ide.tests --keepdb -v2
```

Expected: All tests PASS (135 existing + 8 new = ~143)

- [ ] **Step 2: Check for migration issues**

```bash
cd ~/classedge && ./env/bin/python manage.py makemigrations --check --dry-run
```

Expected: No new migrations needed (no model changes in SP1)

- [ ] **Step 3: Push to personal remote**

```bash
cd ~/classedge && git push personal main
```
