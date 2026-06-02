# Teacher Dashboard & Design System — Sub-project 1 of 3

**Date:** 2026-04-18
**Status:** Approved
**Depends on:** Gamification Engine (shipped), At-Risk Dashboard (shipped), IDE Sub-B (shipped)

---

## Overview

Replace the existing generic teacher dashboard (`/dashboard/`) with a data-rich analytics dashboard that surfaces real student performance data in the new teacher design system. This is the foundation layer — Sub-project 2 (Teacher Gamification Engine) and Sub-project 3 (Per-Subject Analytics + Student Detail) build on it.

## Three Sub-project Roadmap

1. **SP1 (this spec):** Teacher base template + design system + dashboard with real student data
2. **SP2 (next):** TeacherGamification model (Impact Points, ranks), teacher badges, active challenges, recognition, student nominations
3. **SP3 (after):** Per-subject analytics drill-down (8 metrics: XP distribution, engagement heatmap, at-risk crossover, badge leaderboard, avg scores by activity type, streak health, completion rates, top/bottom performers) + per-student full detail page

---

## 1. Design System: `teacher_base.html`

### Source

Based on mockup at `~/classedge-hccci-repo/mockup-teacher-dashboard.html`. The design uses:

- **Fonts:** Fraunces (display/headings, serif, italic accents) + Inter Tight (body, sans-serif)
- **Palette:** Cream (`#faf7f2`), Forest (`#1b4332`), Gold (`#b7925a`), Rose (`#c08479`), Ink (`#2d3142`)
- **Layout:** Sidebar (260px) + main content area, card-based, 16px/10px border-radius
- **Animations:** fadeUp, fadeDown, fillProgress (CSS keyframes)
- **Texture:** Subtle SVG noise overlay, radial gradients on body

### Template: `templates/teacher_base.html`

A new base template for all teacher pages. Extends nothing — standalone like `student_base.html`.

**Includes:**
- Full CSS variables block (`:root` with all color, shadow, radius, font vars)
- Google Fonts link (Fraunces + Inter Tight)
- Body background (radial gradients + noise texture)
- `.app` grid layout (sidebar + main)
- Sidebar component (logo, nav sections, footer with user info)
- `{% block content %}` for page-specific content
- All CSS classes from the mockup (`.card`, `.metric`, `.growth`, `.spotlight`, etc.)

**Sidebar navigation:**
Dynamic based on existing URL names. Teacher sees:
- **Teaching:** Dashboard (student_dashboard → now teacher), My Subjects, Gradebook, Attendance
- **Insight:** Analytics (SP3), Badge Management, Coding Overview
- **Footer:** Teacher name, role/department, avatar initial

**Active nav detection:** Compare `request.resolver_match.url_name` to highlight current page.

**Context processor:** New `gamification.context_processors.teacher_context` (or extend existing `student_context`) to provide:
- `is_teacher_role` (bool)
- `teacher_name` (first name)
- `teacher_department` (from subject or profile)

### Template Selection

Teacher pages use:
```python
{% extends is_teacher_role|yesno:"teacher_base.html,base.html" %}
```

Similar to the student pattern with `student_base.html`. Non-teacher/non-student users fall back to `base.html`.

---

## 2. Teacher Dashboard View

### URL

Replaces existing teacher dashboard at `/dashboard/`. The existing `accounts/views/dashboard.py` has a `teacher_dashboard` path that renders for teachers. We replace its content.

### View: `teacher_dashboard(request)`

**File:** `gamification/views.py` (add new view, keep existing student_dashboard)

Queries real data from existing models. No new models needed for SP1.

### Sections

#### 2a. Top Bar

- Greeting: "Good morning/afternoon/evening, *{first_name}*"
- Subtitle: "Your classes at a glance" (or date-based: "Friday, April 18")
- Notification icons (placeholder for SP2)

#### 2b. Summary Growth Card

A large card at the top showing the teacher's aggregate stats across all subjects:

| Field | Source | Computation |
|-------|--------|-------------|
| Total Students | `SubjectEnrollment` | Count distinct students enrolled in teacher's subjects this semester |
| Active Subjects | `Subject` | Count subjects assigned to teacher this semester |
| Overall Class Average | `StudentActivity` | Avg of (total_score / max_score * 100) across all graded activities in teacher's subjects |
| At-Risk Students | `at_risk.calculator` | Count students with risk_score < AT_RISK_MEDIUM_THRESHOLD (65) across teacher's subjects |

Layout follows the mockup's `.growth` section: large card with forest/gold accents, two stat columns, a progress-style bar showing overall class average (0-100%).

#### 2c. Four Metric Cards

Row of 4 cards following the mockup's `.metric` pattern. Each shows a value + caption:

| Card | Label | Value | Caption | Source |
|------|-------|-------|---------|--------|
| 1 | Class Average | `{avg}%` | `{delta}% vs last term` | `StudentActivity` avg scores this term vs previous term |
| 2 | At-Risk | `{count}` | `{high} high · {medium} medium` | `at_risk.calculator.calculate_risk_scores()` per subject, aggregate |
| 3 | Completion Rate | `{pct}%` | `{submitted}/{total} activities` | Count StudentActivity / (enrolled students * graded activities) |
| 4 | Active Streaks | `{count}` | `{pct}% of students` | `StudentGamification` where login_streak > 0, count / total enrolled |

Each card has a sparkline SVG. For SP1, sparklines are static decorative (same as mockup). SP2 can make them data-driven.

#### 2d. My Classes (Subject Cards)

Grid of subject cards following the mockup's `.classes-list` pattern. One card per subject the teacher teaches this semester.

Per card:
| Field | Source |
|-------|--------|
| Subject name | `Subject.subject_name` |
| Section/details | Grade level or section info if available |
| Class Average | Avg of StudentActivity scores for this subject |
| Ungraded | Count of Activities in this subject where not all enrolled students have a StudentActivity |
| Module Progress | Avg of StudentProgress.progress across enrolled students and modules in this subject |

**Card border-left color logic:**
- `excellent` (forest green): class avg >= 85% AND ungraded == 0
- `warn` (gold): ungraded > 5 OR class avg < 70%
- Default (forest-2): everything else

**Click action:** Links to per-subject analytics page (SP3). For SP1, links to existing activity list or `#`.

#### 2e. Student Spotlight

Dark forest-green card (`.spotlight` from mockup) showing top 3 students who showed the most improvement recently.

**Computation:** For each student enrolled in teacher's subjects this semester:
1. Get their last 5 graded StudentActivity scores (by date)
2. Get their 5 graded StudentActivity scores before that
3. Calculate delta = avg(recent 5) - avg(previous 5)
4. Sort by delta descending, take top 3

Display: Avatar initial, full name, improvement description (e.g. "jumped from 68% to 82% on recent activities")

**"Send recognition" button:** For SP1, links to badge manual award page. SP2 will add inline recognition.

---

## 3. Context Processor Update

**File:** `gamification/context_processors.py`

Update existing `student_context` to also detect teacher role:

```python
def student_context(request):
    if not request.user.is_authenticated:
        return {}
    role_name = ""
    if hasattr(request.user, "profile") and request.user.profile.role:
        role_name = request.user.profile.role.name.lower()
    return {
        "is_student_role": role_name == "student",
        "is_teacher_role": role_name in ("teacher", "admin"),
        "theme_preference": ...,
    }
```

---

## 4. Dashboard Routing

**File:** `accounts/views/dashboard.py`

The existing `dashboard` view routes by role. Update the teacher path to use the new view:

```python
if role_name == "teacher":
    return teacher_dashboard(request)  # from gamification.views
```

Import `teacher_dashboard` from `gamification.views`.

---

## 5. Sidebar Link Updates

The teacher_base.html sidebar needs to link to existing URL names:

| Nav Item | URL Name | Exists? |
|----------|----------|---------|
| Dashboard | `dashboard` | Yes |
| Gradebook | `viewGradeBookComponents` | Yes |
| Attendance | `attendance_report` | Yes |
| Badge Management | `badge_management` | Yes (SP-B) |
| Coding Overview | `coding_overview` | Yes (SP-B) |
| Analytics | `teacher_analytics` | SP3 |

For SP1, "Analytics" nav item links to `#` (greyed out, "Coming soon" tooltip).

---

## 6. Tests

### View Tests (~6) — `gamification/tests/test_teacher_dashboard.py`

1. `test_teacher_sees_new_dashboard` — teacher login, GET `/dashboard/`, status 200, uses `teacher_base.html`
2. `test_student_does_not_see_teacher_dashboard` — student login, GET `/dashboard/`, does NOT use `teacher_base.html`
3. `test_dashboard_shows_subject_cards` — teacher with 2 subjects sees 2 cards in context
4. `test_dashboard_metric_cards_present` — context has `metrics` with 4 entries
5. `test_dashboard_spotlight_students` — with graded activities, spotlight returns top improvers
6. `test_empty_semester_no_crash` — teacher with no current semester gets empty but no 500

### Template Tests (~2) — `gamification/tests/test_teacher_dashboard.py`

7. `test_teacher_base_template_renders` — teacher sees Fraunces font link and sidebar nav
8. `test_context_processor_teacher_flag` — `is_teacher_role` is True for teacher users

**Total: ~8 tests**

---

## 7. File Changes Summary

### New Files
| File | Purpose |
|------|---------|
| `templates/teacher_base.html` | Teacher design system base template |
| `gamification/tests/test_teacher_dashboard.py` | Dashboard view tests |

### Modified Files
| File | Changes |
|------|---------|
| `gamification/views.py` | Add `teacher_dashboard` view |
| `gamification/urls.py` | Add dashboard URL if needed (or modify accounts routing) |
| `gamification/context_processors.py` | Add `is_teacher_role` flag |
| `accounts/views/dashboard.py` | Route teacher to new dashboard view |

### Unchanged
- All existing teacher pages (gradebook, attendance, etc.) stay on `base.html` for now
- Student dashboard (`student_base.html`) unchanged
- SP2 will add TeacherGamification model, SP3 will add analytics pages

---

## 8. Design Tokens Reference

Extracted from mockup for `teacher_base.html`:

```css
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
```

Fonts: `https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,400;9..144,500;9..144,600;9..144,700&family=Inter+Tight:wght@400;500;600;700&display=swap`
