# Student Dashboard UI Redesign — Design Spec

## Overview

Replace the existing Bootstrap 5 student experience with a custom dark-navy
themed UI featuring gamification widgets, a quest map, and a student calendar.
All student-facing pages get the new theme via `student_base.html`. Teachers
and admins stay on the existing `base.html`. Includes a dark/light mode toggle.

This is **Sub-project B** of the gamification feature. Sub-project A (the
gamification engine) is already shipped and provides the data this UI consumes.

## Scope

**In scope:**
- New `student_base.html` template with custom sidebar, dark/light CSS variables
- Theme toggle (dark/light) persisted in localStorage + cookie
- Redesigned student dashboard at `/dashboard/` with XP, streaks, badges, leaderboard, quests, upcoming
- Full leaderboard page at `/gamification/leaderboard/`
- Badge collection page at `/gamification/badges/`
- Student calendar page at `/gamification/calendar/` using existing Holiday/Event/Announcement models
- Quest map page at `/gamification/quest-map/<subject_id>/` using existing Module + StudentProgress models
- Context processor for role-based template switching
- Migration of all student-facing templates to `student_base.html`
- ~12-15 view/template tests

**Out of scope:**
- Teacher/admin UI redesign (stays on `base.html`)
- New data models (everything reads from existing models + gamification engine)
- Side activities / mini-games (future sub-project)
- Push notification changes
- Mobile app changes

## Theme System

### `static/css/student_theme.css`

Single CSS file with two palettes via custom properties on `[data-theme]`:

**Dark palette (default):**
```css
[data-theme="dark"] {
    --bg: #0a0f1f;
    --bg-2: #111930;
    --surface: rgba(22, 30, 54, 0.72);
    --surface-2: rgba(30, 40, 70, 0.55);
    --border: rgba(255, 255, 255, 0.08);
    --border-strong: rgba(255, 255, 255, 0.14);
    --text: #eef2ff;
    --text-dim: #9aa3c0;
    --text-muted: #6b7394;
    --gold: #f4b740;
    --gold-glow: rgba(244, 183, 64, 0.35);
    --coral: #ff6b6b;
    --coral-glow: rgba(255, 107, 107, 0.35);
    --mint: #4ecdc4;
    --mint-glow: rgba(78, 205, 196, 0.3);
    --violet: #9d8dff;
}
```

**Light palette:**
```css
[data-theme="light"] {
    --bg: #f8f9fc;
    --bg-2: #eef0f6;
    --surface: #ffffff;
    --surface-2: #f3f4f8;
    --border: rgba(0, 0, 0, 0.08);
    --border-strong: rgba(0, 0, 0, 0.14);
    --text: #1a1a2e;
    --text-dim: #5a5f7a;
    --text-muted: #8b90a8;
    --gold: #d4960a;
    --gold-glow: rgba(212, 150, 10, 0.25);
    --coral: #e04545;
    --coral-glow: rgba(224, 69, 69, 0.25);
    --mint: #2ba69e;
    --mint-glow: rgba(43, 166, 158, 0.2);
    --violet: #7b6de0;
}
```

All component styles reference these variables. Typography: Bricolage Grotesque
(display) + Inter Tight (body) loaded from Google Fonts.

### Theme persistence

JavaScript on page load:
1. Read `localStorage.getItem("theme")` — if set, apply it
2. Otherwise read `theme` cookie — if set, apply it
3. Otherwise default to `"dark"`
4. Set `data-theme` on `<body>`
5. On toggle: flip attribute, write to localStorage, set cookie (so Django can read it)

Cookie is used so Django context processor can read the user's preference for
any server-side rendering decisions. Attribute name: `theme`, value: `"dark"` or
`"light"`, path: `/`, max-age: 1 year.

## Template Architecture

### `student_base.html`

```
<body data-theme="{{ theme_preference }}">
  <div class="app">
    <aside class="sidebar">
      Logo
      Nav links (8 items, active state from URL)
      User avatar + name + section
      Theme toggle button
    </aside>
    <main>
      <div class="topbar">
        Date / Search / Notifications
      </div>
      {% block content %}{% endblock %}
    </main>
  </div>

  <!-- Same JS/CSS dependencies as base.html -->
  jQuery, Bootstrap 5 JS, DataTables, Select2, Summernote, OneSignal
  <!-- Plus new -->
  student_theme.css, student_theme.js
</body>
```

### Context processor: `gamification/context_processors.py`

```python
def student_context(request):
    if not request.user.is_authenticated:
        return {}
    is_student = request.user.profile.role.name.lower() == "student"
    theme = request.COOKIES.get("theme", "dark")
    return {
        "is_student_role": is_student,
        "theme_preference": theme,
    }
```

Registered in `settings.py` `TEMPLATES[0]["OPTIONS"]["context_processors"]`.

### Template migration pattern

Each student-facing template changes its extends line:

```django
{% extends is_student_role|yesno:"student_base.html,base.html" %}
```

This uses Django's `yesno` filter — students get `student_base.html`, everyone
else gets `base.html`. The context processor ensures `is_student_role` is
always available.

## Sidebar Navigation

| Item | Icon | URL | View exists |
|------|------|-----|-------------|
| Dashboard | `fas fa-home` | `/dashboard/` | Redesigned |
| My Courses | `fas fa-book` | `/subject_list/` | Existing |
| Assignments | `fas fa-tasks` | `/student_activities/` | Existing |
| Calendar | `fas fa-calendar-alt` | `/gamification/calendar/` | New |
| Quest Map | `fas fa-map` | `/gamification/quest-map/` | New (subject picker) |
| Leaderboard | `fas fa-trophy` | `/gamification/leaderboard/` | New |
| Messages | `fas fa-envelope` | `/messages/` | Existing |
| Settings | `fas fa-cog` | `/profile/` | Existing |

Active state: gold left-border accent, matched by comparing `request.path`
against each item's URL prefix.

Sidebar footer: user initials avatar (gradient background), full name, section
label (e.g., "Grade 10-A" from profile data).

Mobile (below 980px): sidebar hidden, hamburger toggle reveals it as an overlay.

## Student Dashboard Page

### View: `gamification/views.py :: student_dashboard`

Replaces the existing dashboard view for students. The existing `dashboard()`
in `accounts/views/dashboard.py` is kept for teacher/admin — we add a role
check at the top that redirects students to the new view.

### Template: `gamification/templates/gamification/student_dashboard.html`

**Hero section:**
- Time-based greeting: "Good morning/afternoon/evening, {first_name}"
- XP bar: Level N badge → progress bar (percentage to next level) → Level N+1 badge
- XP meta: "{total_xp} XP earned" / "{xp_to_next} XP to next level"
- XP to next level: `((current_level + 1)^2 * 100) - total_xp`
- Streak chips: login_streak, submission_streak, accuracy_streak, streak_freezes_available

**Grid row 1 (1.4fr + 1fr):**

Left card — **Today's Quests:**
- Query: `Activity` objects for student's enrolled subjects in current semester
  where `end_time` is today or upcoming, limit 5
- For each: activity name, completion status (has `StudentActivity`?), XP reward
  (from `GAMIFICATION_XP_RATES["submission"]`)
- Completed quests shown with mint checkmark and strikethrough

Right card — **Recent Badges:**
- Query: `StudentBadge.objects.filter(student=user).select_related("badge").order_by("-earned_at")[:6]`
- 3x2 grid: icon + name for each badge. If fewer than 6, fill remaining with locked placeholder
- Footer: "N of M unlocked" + "View all →" link to badge collection

**Grid row 2 (1fr + 1fr):**

Left card — **Class Leaderboard:**
- Query: `StudentGamification` for students in same section/class as current
  user, ordered by `-total_xp`, limit 5
- Each row: rank, avatar (initials), name, XP total
- Current user row highlighted with gold accent
- "View full leaderboard →" link

Right card — **Upcoming:**
- Query: `Activity` objects across enrolled subjects where `end_time > now`,
  ordered by `end_time`, limit 5
- Plus `Event` objects from calendar where `start_date > today`, limit 3
- Merged and sorted by date, total limit 5
- Each row: date label, title, time

### Data assembly: `_build_dashboard_context(student, semester)`

Helper function that assembles all dashboard data in one place with efficient
queries (select_related, prefetch_related). Returns a dict ready for template
context.

## Leaderboard Page

### View: `gamification/views.py :: leaderboard`

URL: `/gamification/leaderboard/`

Full leaderboard for students in the same section/class. Shows all students
(not just top 5).

**Query:** `StudentGamification` joined with Profile to get section info.
Filter to students in same section as `request.user`. Order by `-total_xp`.

**Template:** `gamification/templates/gamification/leaderboard.html`
- Table: rank, avatar, name, level, XP, badges earned count
- Current user row highlighted
- Optional subject filter dropdown (leaderboard scoped to a specific subject's
  enrollment list)

## Badge Collection Page

### View: `gamification/views.py :: badge_collection`

URL: `/gamification/badges/`

All badge definitions displayed in a grid, grouped by tier (platinum first,
then gold, silver, bronze, hidden, seasonal).

**Query:**
- All active `BadgeDefinition` objects
- Student's `StudentBadge` set (to mark earned vs locked)

**Template:** `gamification/templates/gamification/badge_collection.html`
- Tier section headers
- Badge cards: icon, name, description, tier label
- Earned badges: full color, earned date shown
- Locked badges: greyed out, no description (mystery)
- Teacher-awarded badges: no "awarded by" label visible to students

## Calendar Page

### View: `gamification/views.py :: student_calendar`

URL: `/gamification/calendar/`

Monthly calendar showing the student's academic schedule.

**Data sources (existing models, no changes):**
- `calendars.Holiday` — school holidays
- `calendars.Event` — school events
- `calendars.Announcement` — school announcements
- `activity.Activity` — assignment deadlines for enrolled subjects
- `course.Attendance` — past attendance records

**Template:** `gamification/templates/gamification/calendar.html`
- Month grid view (standard calendar layout)
- Color-coded dots: gold for deadlines, coral for holidays, mint for events,
  violet for attendance
- Click on a day to see detail list below the calendar
- Previous/next month navigation
- Today highlighted

**Implementation:** Pure server-rendered HTML calendar grid. No JavaScript
calendar library needed — a simple Python function generates the month's days
and the template renders them in a CSS grid. Each day cell contains colored
dots for its events.

## Quest Map Page

### View: `gamification/views.py :: quest_map`

URL: `/gamification/quest-map/` (subject picker)
URL: `/gamification/quest-map/<int:subject_id>/` (map for specific subject)

Visual progress map showing the student's journey through a subject's modules.

**Data sources (existing models, no changes):**
- `module.Module` — ordered list of modules for the subject (uses `order` field)
- `module.StudentProgress` — completion status per module
- `activity.Activity` — activities linked to modules (via `additional_modules` M2M)
- `activity.StudentActivity` — activity completion

**Subject picker page:** If no subject_id, show a grid of the student's
enrolled subjects with progress percentage. Click to view the quest map.

**Quest map page:**
- SVG path with nodes for each module, rendered server-side
- Node states: completed (gold), current (coral, pulsing), locked (grey)
- Current node = first incomplete module in order
- Each node shows module name below
- Progress bar: "X of Y modules completed"
- "Continue Learning →" button linking to the current module's lesson view
- Below the map: list of upcoming activities for the current module

**SVG generation:** Python function that calculates node positions based on
module count, creates a wavy path, and outputs SVG markup. The template
includes the SVG inline. No JavaScript needed for the basic map.

## Template Migration

### Templates to update

All student-facing templates that currently extend `base.html` need the
conditional extends pattern:

```django
{% extends is_student_role|yesno:"student_base.html,base.html" %}
```

**Priority templates (student visits daily):**
- `accounts/templates/accounts/interface/dashboard.html`
- `course/templates/course/view_subject_dashboard.html`
- `course/templates/course/subject_list.html`
- `module/templates/module/lesson_list.html`
- `module/templates/module/view_lesson.html`
- `activity/templates/activity/` (activity list, detail, quiz display)
- `calendars/templates/calendar/calendar.html`
- `message/templates/message/` (inbox, compose, detail)

**Secondary templates (less frequent):**
- `course/templates/course/attendance/` student views
- `module/templates/module/progress/` progress views
- `accounts/templates/accounts/` profile/settings

**Not migrated (teacher/admin only):**
- Grade management, roster, content creation, admin dashboards
- Any template with `_CM.html` suffix (Classroom Mode — teacher tool)

### Migration approach

The conditional extends pattern (`is_student_role|yesno`) means each template
works for both roles without duplication. The context processor provides
`is_student_role` on every request.

**CSS compatibility:** `student_base.html` includes all the same CSS/JS
dependencies as `base.html` (Bootstrap 5, DataTables, Select2, etc.) so
existing template content renders correctly inside the new wrapper. The new
theme CSS is additive — it styles the wrapper (sidebar, topbar, cards) but
doesn't override Bootstrap component styles used in page content.

## URL Configuration

### `gamification/urls.py` (additions to existing)

```
gamification/leaderboard/                    → leaderboard
gamification/badges/                         → badge_collection
gamification/calendar/                       → student_calendar
gamification/quest-map/                      → quest_map_picker
gamification/quest-map/<int:subject_id>/     → quest_map
```

### Modification to `accounts/views/dashboard.py`

Add at the top of the existing `dashboard()` view:

```python
if user_role == "student":
    return redirect("student_dashboard")
```

New `student_dashboard` URL registered in `gamification/urls.py`:
```
gamification/dashboard/   → student_dashboard
```

The existing `/dashboard/` URL stays — it just redirects students to the new
view. Teachers/admins continue to see the existing dashboard.

## Testing

### `gamification/tests/test_dashboard_views.py`

**Dashboard tests:**
- Student sees new dashboard (check for `data-theme` in response)
- Dashboard shows XP, level, streak data from gamification engine
- Dashboard shows recent badges
- Dashboard shows leaderboard snippet
- Teacher accessing `/dashboard/` sees old dashboard (no redirect loop)
- Unauthenticated → login redirect

**Leaderboard tests:**
- Renders with ranked students
- Current user highlighted
- Student-only access

**Badge collection tests:**
- Shows earned vs locked badges
- Grouped by tier
- Student-only access

**Calendar tests:**
- Renders current month
- Shows holidays and upcoming deadlines

**Quest map tests:**
- Subject picker shows enrolled subjects
- Map renders modules in order
- Completed/current/locked states correct

**Template tests:**
- Student gets `student_base.html` (check sidebar markup)
- Teacher gets `base.html` (no sidebar)
- Theme cookie respected

**~15-18 tests total.**

## Static Files

### New files

| File | Purpose |
|------|---------|
| `static/css/student_theme.css` | Dark/light palettes + all component styles |
| `static/js/student_theme.js` | Theme toggle logic (localStorage + cookie) |

### Font loading

Google Fonts loaded in `student_base.html` `<head>`:
```html
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,700&family=Inter+Tight:wght@400;500;600;700&display=swap" rel="stylesheet">
```
