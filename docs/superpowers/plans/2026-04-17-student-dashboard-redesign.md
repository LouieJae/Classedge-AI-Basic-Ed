# Student Dashboard UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Bootstrap 5 student experience with a custom dark/light themed UI featuring gamification widgets, quest map, calendar, leaderboard, and badge collection — all student-facing pages get the new theme.

**Architecture:** New `student_base.html` with CSS custom property theming (dark/light toggle). Context processor detects student role and provides `is_student_role` + `theme_preference` to all templates. Student-facing templates use conditional extends (`is_student_role|yesno`). New views for dashboard, leaderboard, badges, calendar, quest map in `gamification/` app. No new data models — reads from existing + gamification engine.

**Tech Stack:** Django 5, CSS custom properties, Bricolage Grotesque + Inter Tight fonts, existing Bootstrap 5 / jQuery / DataTables dependencies, SVG for quest map

---

## File Structure

### New files

| File | Responsibility |
|------|---------------|
| `static/css/student_theme.css` | Dark/light CSS variable palettes + all student UI component styles |
| `static/js/student_theme.js` | Theme toggle logic (localStorage + cookie + body attribute) |
| `templates/student_base.html` | Base template for student-facing pages (sidebar, topbar, theme) |
| `gamification/context_processors.py` | `student_context()` — provides `is_student_role` + `theme_preference` |
| `gamification/templates/gamification/student_dashboard.html` | Redesigned student dashboard |
| `gamification/templates/gamification/leaderboard.html` | Full leaderboard page |
| `gamification/templates/gamification/badge_collection.html` | Badge grid page |
| `gamification/templates/gamification/student_calendar.html` | Monthly calendar page |
| `gamification/templates/gamification/quest_map_picker.html` | Subject picker for quest map |
| `gamification/templates/gamification/quest_map.html` | Quest map for a subject |
| `gamification/tests/test_dashboard_views.py` | View + template tests |

### Modified files

| File | Change |
|------|--------|
| `lms/settings.py` | Add `gamification.context_processors.student_context` to context processors |
| `gamification/urls.py` | Add dashboard, leaderboard, badges, calendar, quest map URL patterns |
| `gamification/views.py` | Add student_dashboard, leaderboard, badge_collection, student_calendar, quest_map views |
| `accounts/views/dashboard.py` | Add student redirect at top of `dashboard()` view |
| ~25 student-facing templates | Change `{% extends 'base.html' %}` to conditional extends |

---

## Task 1: Theme CSS + JS + Student Base Template

**Files:**
- Create: `static/css/student_theme.css`
- Create: `static/js/student_theme.js`
- Create: `templates/student_base.html`
- Create: `gamification/context_processors.py`
- Modify: `lms/settings.py`

- [ ] **Step 1: Create the context processor**

Create `gamification/context_processors.py`:
```python
def student_context(request):
    """Provide is_student_role and theme_preference to all templates."""
    if not request.user.is_authenticated:
        return {"is_student_role": False, "theme_preference": "dark"}

    is_student = False
    if hasattr(request.user, "profile") and request.user.profile.role:
        is_student = request.user.profile.role.name.lower() == "student"

    theme = request.COOKIES.get("theme", "dark")
    return {
        "is_student_role": is_student,
        "theme_preference": theme,
    }
```

- [ ] **Step 2: Register context processor in settings**

In `lms/settings.py`, add to the `context_processors` list (after `accounts.context_processors.logo_update_time`):
```python
                'gamification.context_processors.student_context',
```

- [ ] **Step 3: Create the theme JS**

Create `static/js/student_theme.js`:
```javascript
(function() {
    // Read theme: localStorage > cookie > default
    var theme = localStorage.getItem('theme');
    if (!theme) {
        var match = document.cookie.match(/(?:^|; )theme=([^;]*)/);
        theme = match ? match[1] : 'dark';
    }
    document.body.setAttribute('data-theme', theme);

    // Toggle function — called by the sidebar toggle button
    window.toggleStudentTheme = function() {
        var current = document.body.getAttribute('data-theme');
        var next = current === 'dark' ? 'light' : 'dark';
        document.body.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        document.cookie = 'theme=' + next + ';path=/;max-age=31536000;SameSite=Lax';

        // Update toggle icon
        var icon = document.getElementById('theme-toggle-icon');
        if (icon) {
            icon.className = next === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }
        var label = document.getElementById('theme-toggle-label');
        if (label) {
            label.textContent = next === 'dark' ? 'Light Mode' : 'Dark Mode';
        }
    };
})();
```

- [ ] **Step 4: Create the theme CSS**

Create `static/css/student_theme.css`. This is a large file — use the `frontend-design` skill or write it directly. The CSS must contain:

1. **CSS variable definitions** for both `[data-theme="dark"]` and `[data-theme="light"]` selectors. Dark palette:
   - `--bg: #0a0f1f`, `--bg-2: #111930`, `--surface: rgba(22,30,54,0.72)`, `--surface-2: rgba(30,40,70,0.55)`
   - `--border: rgba(255,255,255,0.08)`, `--border-strong: rgba(255,255,255,0.14)`
   - `--text: #eef2ff`, `--text-dim: #9aa3c0`, `--text-muted: #6b7394`
   - `--gold: #f4b740`, `--gold-glow: rgba(244,183,64,0.35)`
   - `--coral: #ff6b6b`, `--coral-glow: rgba(255,107,107,0.35)`
   - `--mint: #4ecdc4`, `--mint-glow: rgba(78,205,196,0.3)`
   - `--violet: #9d8dff`
   Light palette: `--bg: #f8f9fc`, `--surface: #ffffff`, `--text: #1a1a2e`, etc.

2. **Layout**: `.app` grid (240px sidebar + 1fr main), `.sidebar` (sticky, glassmorphic, flex column), `main` (padded content area)

3. **Sidebar styles**: `.logo`, `.nav`, `.nav a`, `.nav a.active` (gold left border), `.nav a.coming-soon` (dimmed + "SOON" badge), `.sidebar-footer`, `.theme-toggle`

4. **Topbar**: `.topbar`, `.greeting-meta`, `.icon-btn`

5. **Hero section**: `.hero` (gradient background, border-radius 28px), `.level-row`, `.level-badge`, `.xp-bar`, `.xp-fill`, `.xp-meta`, `.streaks`, `.streak-chip`

6. **Cards**: `.card`, `.card h2`, `.count` badge

7. **Quest list**: `.quest`, `.quest.done`, `.quest-check`, `.quest-title`, `.quest-xp`

8. **Badge grid**: `.badge-grid`, `.badge`, `.badge.locked`, `.badge-footer`

9. **Leaderboard**: `.lb-row`, `.lb-row.you`, `.lb-rank`, `.lb-avatar`, `.lb-name`, `.lb-xp`, `.lb-delta`

10. **Upcoming**: `.upcoming-item`, `.upcoming-date`, `.upcoming-title`, `.upcoming-time`

11. **Calendar**: `.cal-grid`, `.cal-day`, `.cal-day.today`, `.cal-dot` (color variants)

12. **Quest map**: `.quest-map`, `.map-svg`, `.node-done`, `.node-active`, `.node-locked`

13. **Responsive**: below 980px — sidebar hidden, single-column grids

14. **Animations**: `fadeUp`, `fadeDown`, `fillXP`, `shimmer`, `pulse` keyframes

Reference the mockup HTML at `~/classedge-hccci-repo/mockup-student-dashboard.html` for exact CSS values.

- [ ] **Step 5: Create student_base.html**

Create `templates/student_base.html`:
```html
{% load static %}
<!DOCTYPE html>
<html lang="en-US" dir="ltr">
<head>
    <meta charset="utf-8" />
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="csrf-token" content="{{ csrf_token }}" />

    <title>{% block title %}{{ SCHOOL_NAME }} | Dashboard{% endblock %}</title>

    <link rel="icon" type="image/png" href="{{ MEDIA_URL }}logos/HCCCI-logo.png?{{ logo_update_time }}" />

    <!-- Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,700;12..96,800&family=Inter+Tight:wght@400;500;600;700&display=swap" rel="stylesheet">

    <!-- Existing dependencies (same as base.html) -->
    <link href="{% static 'assets/css/theme.css' %}" rel="stylesheet" id="style-default" />
    <link href="{% static 'assets/css/user.css' %}" rel="stylesheet" id="user-style-default" />
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/sweetalert2@11/dist/sweetalert2.min.css" />
    <link rel="stylesheet" href="{% static 'vendors/select2/select2.min.css' %}" />
    <link rel="stylesheet" href="{% static 'vendors/select2-bootstrap-5-theme/select2-bootstrap-5-theme.min.css' %}" />
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.7/css/dataTables.bootstrap5.min.css" />
    <link rel="stylesheet" href="https://cdn.datatables.net/responsive/3.0.0/css/responsive.bootstrap5.min.css" />
    <link href="{% static 'vendors/glightbox/glightbox.min.css' %}" rel="stylesheet" />
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />

    <!-- Student theme (overrides) -->
    <link href="{% static 'css/student_theme.css' %}" rel="stylesheet" />

    {% block extra_css %}{% endblock %}
</head>

<body data-theme="{{ theme_preference }}" data-current-user-id="{{ request.user.id }}">
<script src="{% static 'js/student_theme.js' %}"></script>

<div class="app">
    <!-- Sidebar -->
    <aside class="sidebar" id="student-sidebar">
        <div class="logo">
            <div class="logo-mark">C</div>
            ClassEdge
        </div>

        <nav class="nav">
            <a href="{% url 'dashboard' %}" class="{% if request.path == '/dashboard/' or request.path == '/gamification/dashboard/' %}active{% endif %}">
                <span class="nav-icon"><i class="fas fa-home"></i></span> Dashboard
            </a>
            <a href="{% url 'subject_list' %}" class="{% if '/subject_list/' in request.path %}active{% endif %}">
                <span class="nav-icon"><i class="fas fa-book"></i></span> My Courses
            </a>
            <a href="{% url 'activityList' %}" class="{% if '/activityList/' in request.path or '/activity' in request.path %}active{% endif %}">
                <span class="nav-icon"><i class="fas fa-tasks"></i></span> Assignments
            </a>
            <a href="{% url 'student_calendar' %}" class="{% if '/gamification/calendar/' in request.path %}active{% endif %}">
                <span class="nav-icon"><i class="fas fa-calendar-alt"></i></span> Calendar
            </a>
            <a href="{% url 'quest_map_picker' %}" class="{% if '/gamification/quest-map/' in request.path %}active{% endif %}">
                <span class="nav-icon"><i class="fas fa-map"></i></span> Quest Map
            </a>
            <a href="{% url 'gamification_leaderboard' %}" class="{% if '/gamification/leaderboard/' in request.path %}active{% endif %}">
                <span class="nav-icon"><i class="fas fa-trophy"></i></span> Leaderboard
            </a>
            <a href="{% url 'inbox' %}" class="{% if '/messages/' in request.path or '/inbox/' in request.path %}active{% endif %}">
                <span class="nav-icon"><i class="fas fa-envelope"></i></span> Messages
                {% if unread_messages_count %}<span class="nav-badge">{{ unread_messages_count }}</span>{% endif %}
            </a>
            <a href="{% url 'viewProfile' request.user.id %}" class="{% if '/view_profile/' in request.path %}active{% endif %}">
                <span class="nav-icon"><i class="fas fa-cog"></i></span> Settings
            </a>
        </nav>

        <div class="sidebar-footer">
            <div class="avatar">{{ request.user.first_name|first|default:"?" }}</div>
            <div>
                <div style="font-weight: 600;">{{ request.user.get_full_name|default:request.user.username }}</div>
                <div class="user-role">{{ request.user.profile.section|default:"Student" }}</div>
            </div>
        </div>

        <div class="theme-toggle" onclick="toggleStudentTheme()">
            <i id="theme-toggle-icon" class="fas {% if theme_preference == 'dark' %}fa-sun{% else %}fa-moon{% endif %}"></i>
            <span id="theme-toggle-label">{% if theme_preference == 'dark' %}Light Mode{% else %}Dark Mode{% endif %}</span>
        </div>
    </aside>

    <!-- Mobile hamburger -->
    <button class="sidebar-toggle" id="sidebar-toggle" onclick="document.getElementById('student-sidebar').classList.toggle('open')">
        <i class="fas fa-bars"></i>
    </button>

    <!-- Main content -->
    <main>
        <div class="topbar">
            <div class="greeting-meta">{% now "l · F j" %}</div>
            <div class="topbar-actions">
                <div class="icon-btn"><i class="fas fa-search"></i></div>
                <div class="icon-btn">
                    <i class="fas fa-envelope"></i>
                    {% if unread_messages_count %}<span class="dot"></span>{% endif %}
                </div>
                <div class="icon-btn">
                    <i class="fas fa-bell"></i>
                    {% if unread_notifications_count %}<span class="dot"></span>{% endif %}
                </div>
            </div>
        </div>

        {% if messages %}
        <div class="mb-3">
            {% for message in messages %}
            <div class="alert alert-{{ message.tags }} alert-dismissible fade show" role="alert">
                {{ message }}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
            {% endfor %}
        </div>
        {% endif %}

        {% block content %}{% endblock %}
    </main>
</div>

<!-- JS dependencies (same as base.html) -->
<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://cdn.datatables.net/1.13.7/js/jquery.dataTables.min.js"></script>
<script src="https://cdn.datatables.net/1.13.7/js/dataTables.bootstrap5.min.js"></script>
<script src="https://cdn.datatables.net/responsive/3.0.0/js/dataTables.responsive.min.js"></script>
<script src="{% static 'vendors/select2/select2.min.js' %}"></script>
<script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
<script src="{% static 'vendors/glightbox/glightbox.min.js' %}"></script>

{% block extra_js %}{% endblock %}
</body>
</html>
```

- [ ] **Step 6: Verify student_base.html renders**

Start the dev server and log in as a student. Manually visit a URL that uses `student_base.html` (we'll wire this up in Task 2). For now, verify no Django template errors:

Run: `cd ~/classedge && env/bin/python manage.py check 2>&1`
Expected: No issues.

- [ ] **Step 7: Commit**

```bash
cd ~/classedge && git add static/css/student_theme.css static/js/student_theme.js templates/student_base.html gamification/context_processors.py && git add -f lms/settings.py
git commit -m "feat(ui): add student theme CSS/JS, student_base.html, and context processor"
```

---

## Task 2: Student Dashboard View + Template

**Files:**
- Modify: `gamification/views.py`
- Modify: `gamification/urls.py`
- Modify: `accounts/views/dashboard.py`
- Create: `gamification/templates/gamification/student_dashboard.html`

- [ ] **Step 1: Add the student dashboard view**

In `gamification/views.py`, add these imports and the view function:

```python
import math
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from activity.models.activity_model import Activity
from activity.models.student_activity_model import StudentActivity
from calendars.models import Event
from course.models.semester_model import Semester
from course.models.subject_enrollment_model import SubjectEnrollment
from gamification.models import BadgeDefinition, StudentBadge, StudentGamification


@login_required
def student_dashboard(request):
    user = request.user
    now = timezone.localtime(timezone.now())

    # Greeting
    hour = now.hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    # Gamification data
    gam = StudentGamification.objects.filter(student=user).first()
    total_xp = gam.total_xp if gam else 0
    current_level = gam.current_level if gam else 1
    next_level = current_level + 1
    xp_for_next = (next_level ** 2) * 100
    xp_progress_pct = min(100, int((total_xp / xp_for_next) * 100)) if xp_for_next > 0 else 0
    xp_to_next = max(0, xp_for_next - total_xp)

    login_streak = gam.login_streak if gam else 0
    submission_streak = gam.submission_streak if gam else 0
    accuracy_streak = gam.accuracy_streak if gam else 0
    freezes = gam.streak_freezes_available if gam else 1

    # Current semester
    semester = Semester.objects.filter(
        start_date__lte=now, end_date__gte=now,
    ).first()

    # Today's quests — upcoming activities for enrolled subjects
    quests = []
    if semester:
        enrolled_subject_ids = SubjectEnrollment.objects.filter(
            student=user, semester=semester, status="enrolled",
        ).values_list("subject_id", flat=True)

        upcoming_activities = Activity.objects.filter(
            subject_id__in=enrolled_subject_ids,
            end_time__gte=now,
            status=True,
        ).exclude(
            activity_type__name__iexact="Participation",
        ).select_related("subject").order_by("end_time")[:5]

        completed_ids = set(
            StudentActivity.objects.filter(
                student=user,
                activity__in=upcoming_activities,
            ).values_list("activity_id", flat=True)
        )

        for act in upcoming_activities:
            quests.append({
                "name": act.activity_name,
                "subject": act.subject.subject_name if act.subject else "",
                "done": act.pk in completed_ids,
                "xp": 50,
            })

    completed_count = sum(1 for q in quests if q["done"])

    # Recent badges
    recent_badges = StudentBadge.objects.filter(
        student=user,
    ).select_related("badge").order_by("-earned_at")[:6]

    total_badges = BadgeDefinition.objects.filter(is_active=True).count()
    earned_count = StudentBadge.objects.filter(student=user).count()

    # Leaderboard snippet — top 5 in same class
    leaderboard = []
    if semester:
        student_subject_ids = SubjectEnrollment.objects.filter(
            student=user, semester=semester, status="enrolled",
        ).values_list("subject_id", flat=True)[:1]

        if student_subject_ids:
            classmate_ids = SubjectEnrollment.objects.filter(
                subject_id__in=student_subject_ids, semester=semester, status="enrolled",
            ).values_list("student_id", flat=True)

            leaderboard_qs = StudentGamification.objects.filter(
                student_id__in=classmate_ids,
            ).select_related("student").order_by("-total_xp")[:5]

            for rank, sg in enumerate(leaderboard_qs, 1):
                leaderboard.append({
                    "rank": rank,
                    "name": sg.student.get_full_name() or sg.student.username,
                    "initial": (sg.student.first_name or sg.student.username)[0].upper(),
                    "xp": sg.total_xp,
                    "is_you": sg.student_id == user.pk,
                })

    # Upcoming deadlines + events
    upcoming = []
    if semester:
        upcoming_acts = Activity.objects.filter(
            subject_id__in=enrolled_subject_ids,
            end_time__gt=now,
            status=True,
        ).order_by("end_time")[:5]
        for act in upcoming_acts:
            upcoming.append({
                "date": act.end_time,
                "title": act.activity_name,
            })

    upcoming_events = Event.objects.filter(
        start_date__gte=now.date(),
    ).order_by("start_date")[:3]
    for ev in upcoming_events:
        upcoming.append({
            "date": ev.start_date,
            "title": ev.title,
        })
    upcoming.sort(key=lambda x: x["date"])
    upcoming = upcoming[:5]

    return render(request, "gamification/student_dashboard.html", {
        "greeting": greeting,
        "user_name": user.first_name or user.username,
        "total_xp": total_xp,
        "current_level": current_level,
        "next_level": next_level,
        "xp_progress_pct": xp_progress_pct,
        "xp_to_next": xp_to_next,
        "login_streak": login_streak,
        "submission_streak": submission_streak,
        "accuracy_streak": accuracy_streak,
        "freezes": freezes,
        "quests": quests,
        "completed_count": completed_count,
        "quest_total": len(quests),
        "recent_badges": recent_badges,
        "total_badges": total_badges,
        "earned_count": earned_count,
        "leaderboard": leaderboard,
        "upcoming": upcoming,
    })
```

- [ ] **Step 2: Add URL pattern**

In `gamification/urls.py`, add to `urlpatterns`:
```python
    path("gamification/dashboard/", views.student_dashboard, name="student_dashboard"),
```

Also add the import if not already present:
```python
from gamification import views
```

- [ ] **Step 3: Redirect students from existing dashboard**

In `accounts/views/dashboard.py`, add after line 50 (`is_registrar = ...`):
```python
    if is_student:
        return redirect("student_dashboard")
```

Add `redirect` to the imports at the top:
```python
from django.shortcuts import render, redirect
```

- [ ] **Step 4: Create the student dashboard template**

Create `gamification/templates/gamification/student_dashboard.html`. This is a large template — use the `frontend-design` skill to generate high-quality HTML that extends `student_base.html`. The template must include:

1. **Hero section**: greeting with wave emoji, XP bar (level badge → progress bar → next level badge), XP meta line, 4 streak chips (login/submission/accuracy/freezes)

2. **Grid row 1** (class `grid`, 1.4fr + 1fr):
   - **Today's Quests card**: h2 with count badge, quest list with done/pending states, XP rewards
   - **Recent Badges card**: h2 with count badge, 3x2 badge grid (icon + name), locked placeholders, footer with "View all →"

3. **Grid row 2** (class `grid`, 1fr + 1fr):
   - **Class Leaderboard card**: lb-row items with rank/avatar/name/xp, `.you` class on current user
   - **Upcoming card**: upcoming-item list with date/title/time

All data comes from the context variables defined in the view. Use Django template tags (`{% for %}`, `{% if %}`, `{{ variable }}`).

Reference the visual preview at `~/.superpowers/brainstorm/*/content/dashboard-layout.html` for exact markup structure.

- [ ] **Step 5: Verify the dashboard renders**

Run: `cd ~/classedge && env/bin/python manage.py runserver`
Log in as a student. Visit `/dashboard/` — should redirect to `/gamification/dashboard/` showing the new dark-themed dashboard.

- [ ] **Step 6: Commit**

```bash
cd ~/classedge && git add gamification/views.py gamification/urls.py gamification/templates/gamification/student_dashboard.html accounts/views/dashboard.py
git commit -m "feat(ui): add student dashboard view with gamification widgets"
```

---

## Task 3: Leaderboard + Badge Collection Views

**Files:**
- Modify: `gamification/views.py`
- Modify: `gamification/urls.py`
- Create: `gamification/templates/gamification/leaderboard.html`
- Create: `gamification/templates/gamification/badge_collection.html`

- [ ] **Step 1: Add leaderboard view**

In `gamification/views.py`, add:
```python
@login_required
def leaderboard(request):
    user = request.user
    now = timezone.localtime(timezone.now())
    semester = Semester.objects.filter(
        start_date__lte=now, end_date__gte=now,
    ).first()

    rows = []
    if semester:
        my_subject_ids = SubjectEnrollment.objects.filter(
            student=user, semester=semester, status="enrolled",
        ).values_list("subject_id", flat=True)[:1]

        classmate_ids = SubjectEnrollment.objects.filter(
            subject_id__in=my_subject_ids, semester=semester, status="enrolled",
        ).values_list("student_id", flat=True) if my_subject_ids else []

        gam_qs = StudentGamification.objects.filter(
            student_id__in=classmate_ids,
        ).select_related("student").order_by("-total_xp")

        for rank, sg in enumerate(gam_qs, 1):
            badge_count = StudentBadge.objects.filter(student=sg.student).count()
            rows.append({
                "rank": rank,
                "name": sg.student.get_full_name() or sg.student.username,
                "initial": (sg.student.first_name or sg.student.username)[0].upper(),
                "level": sg.current_level,
                "xp": sg.total_xp,
                "badges": badge_count,
                "is_you": sg.student_id == user.pk,
            })

    return render(request, "gamification/leaderboard.html", {"rows": rows})
```

- [ ] **Step 2: Add badge collection view**

In `gamification/views.py`, add:
```python
@login_required
def badge_collection(request):
    user = request.user
    all_badges = BadgeDefinition.objects.filter(is_active=True).order_by(
        models.Case(
            models.When(tier="platinum", then=0),
            models.When(tier="gold", then=1),
            models.When(tier="silver", then=2),
            models.When(tier="bronze", then=3),
            models.When(tier="hidden", then=4),
            models.When(tier="seasonal", then=5),
            default=6,
            output_field=models.IntegerField(),
        ),
        "name",
    )

    earned_map = {}
    for sb in StudentBadge.objects.filter(student=user).select_related("badge"):
        earned_map[sb.badge_id] = sb

    badges = []
    for bd in all_badges:
        sb = earned_map.get(bd.pk)
        badges.append({
            "definition": bd,
            "earned": sb is not None,
            "earned_at": sb.earned_at if sb else None,
        })

    earned_count = len(earned_map)
    total_count = all_badges.count()

    return render(request, "gamification/badge_collection.html", {
        "badges": badges,
        "earned_count": earned_count,
        "total_count": total_count,
    })
```

Add `from django.db import models` to imports if not present.

- [ ] **Step 3: Add URL patterns**

In `gamification/urls.py`, add:
```python
    path("gamification/leaderboard/", views.leaderboard, name="gamification_leaderboard"),
    path("gamification/badges/", views.badge_collection, name="gamification_badges"),
```

- [ ] **Step 4: Create leaderboard template**

Create `gamification/templates/gamification/leaderboard.html` extending `student_base.html`:
- Page title "Leaderboard"
- Full-width card with table: rank, avatar (initials), name, level, XP, badges count
- Current user row highlighted with `.lb-row.you`
- Back to dashboard link

- [ ] **Step 5: Create badge collection template**

Create `gamification/templates/gamification/badge_collection.html` extending `student_base.html`:
- Page title "Badge Collection" with "{earned} of {total} unlocked"
- Badge grid (4 columns): each badge card shows icon, name, tier label, description (if earned), earned date
- Locked badges: greyed out, icon only, "???" for description
- Grouped visually by tier with section dividers

- [ ] **Step 6: Verify both pages render**

Start dev server, log in as student, visit:
- `/gamification/leaderboard/`
- `/gamification/badges/`

Both should render with the dark theme.

- [ ] **Step 7: Commit**

```bash
cd ~/classedge && git add gamification/views.py gamification/urls.py gamification/templates/gamification/leaderboard.html gamification/templates/gamification/badge_collection.html
git commit -m "feat(ui): add leaderboard and badge collection pages"
```

---

## Task 4: Student Calendar View

**Files:**
- Modify: `gamification/views.py`
- Modify: `gamification/urls.py`
- Create: `gamification/templates/gamification/student_calendar.html`

- [ ] **Step 1: Add calendar view**

In `gamification/views.py`, add:
```python
import calendar as cal_module
from datetime import date, timedelta

from calendars.models import Holiday, Event as CalendarEvent, Announcement
from course.models.attendance_model import Attendance


@login_required
def student_calendar(request):
    user = request.user
    today = date.today()

    # Parse month/year from query params or default to current
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
    except (ValueError, TypeError):
        year, month = today.year, today.month

    # Build calendar grid
    cal = cal_module.Calendar(firstweekday=6)  # Sunday first
    month_days = cal.monthdayscalendar(year, month)

    first_of_month = date(year, month, 1)
    if month == 12:
        last_of_month = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_of_month = date(year, month + 1, 1) - timedelta(days=1)

    # Events for this month
    holidays = Holiday.objects.filter(
        date__gte=first_of_month, date__lte=last_of_month,
    )
    events = CalendarEvent.objects.filter(
        start_date__gte=first_of_month, start_date__lte=last_of_month,
    )
    announcements = Announcement.objects.filter(
        date__gte=first_of_month, date__lte=last_of_month,
    )

    # Student's enrolled subjects — activity deadlines
    now = timezone.localtime(timezone.now())
    semester = Semester.objects.filter(
        start_date__lte=now, end_date__gte=now,
    ).first()
    deadlines = []
    if semester:
        enrolled_ids = SubjectEnrollment.objects.filter(
            student=user, semester=semester, status="enrolled",
        ).values_list("subject_id", flat=True)
        deadlines = Activity.objects.filter(
            subject_id__in=enrolled_ids,
            end_time__date__gte=first_of_month,
            end_time__date__lte=last_of_month,
            status=True,
        )

    # Build day data map
    day_data = {}
    for h in holidays:
        day_data.setdefault(h.date.day, []).append({"type": "holiday", "title": h.title})
    for e in events:
        day_data.setdefault(e.start_date.day, []).append({"type": "event", "title": e.title})
    for a in announcements:
        day_data.setdefault(a.date.day, []).append({"type": "announcement", "title": a.title})
    for d in deadlines:
        day_data.setdefault(d.end_time.day, []).append({"type": "deadline", "title": d.activity_name})

    # Prev/next month
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    month_name = date(year, month, 1).strftime("%B %Y")

    return render(request, "gamification/student_calendar.html", {
        "month_days": month_days,
        "day_data": day_data,
        "today": today,
        "year": year,
        "month": month,
        "month_name": month_name,
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
    })
```

- [ ] **Step 2: Add URL pattern**

In `gamification/urls.py`, add:
```python
    path("gamification/calendar/", views.student_calendar, name="student_calendar"),
```

- [ ] **Step 3: Create calendar template**

Create `gamification/templates/gamification/student_calendar.html` extending `student_base.html`:
- Header: month name, prev/next arrows (link to `?year=X&month=Y`)
- Day-of-week headers: Sun, Mon, Tue, Wed, Thu, Fri, Sat
- Calendar grid: 7 columns, each cell shows day number + colored dots for events
  - Gold dot: deadline
  - Coral dot: holiday
  - Mint dot: event
  - Violet dot: announcement
- Today's cell highlighted with border
- Below calendar: detail panel showing events for today (or clicked day via JS)
- Empty cells (day=0) rendered blank

- [ ] **Step 4: Verify calendar renders**

Start dev server, log in as student, visit `/gamification/calendar/`.
Navigate to previous/next months.

- [ ] **Step 5: Commit**

```bash
cd ~/classedge && git add gamification/views.py gamification/urls.py gamification/templates/gamification/student_calendar.html
git commit -m "feat(ui): add student calendar view with monthly grid"
```

---

## Task 5: Quest Map View

**Files:**
- Modify: `gamification/views.py`
- Modify: `gamification/urls.py`
- Create: `gamification/templates/gamification/quest_map_picker.html`
- Create: `gamification/templates/gamification/quest_map.html`

- [ ] **Step 1: Add quest map views**

In `gamification/views.py`, add:
```python
from module.models.module import Module
from module.models.student_progress import StudentProgress


@login_required
def quest_map_picker(request):
    user = request.user
    now = timezone.localtime(timezone.now())
    semester = Semester.objects.filter(
        start_date__lte=now, end_date__gte=now,
    ).first()

    subjects = []
    if semester:
        enrollments = SubjectEnrollment.objects.filter(
            student=user, semester=semester, status="enrolled",
        ).select_related("subject")

        for enrollment in enrollments:
            subj = enrollment.subject
            total_modules = Module.objects.filter(subject=subj).count()
            completed = StudentProgress.objects.filter(
                student=user, module__subject=subj, completed=True,
            ).count()
            pct = int((completed / total_modules) * 100) if total_modules > 0 else 0
            subjects.append({
                "id": subj.pk,
                "name": subj.subject_name,
                "total": total_modules,
                "completed": completed,
                "pct": pct,
            })

    return render(request, "gamification/quest_map_picker.html", {
        "subjects": subjects,
    })


@login_required
def quest_map(request, subject_id):
    user = request.user
    subject = get_object_or_404(
        SubjectEnrollment.objects.filter(student=user).values_list("subject", flat=True),
        subject_id,
    )
    from subject.models.subject_model import Subject
    subject = get_object_or_404(Subject, pk=subject_id)

    modules = Module.objects.filter(subject=subject).order_by("order", "pk")

    completed_module_ids = set(
        StudentProgress.objects.filter(
            student=user, module__in=modules, completed=True,
        ).values_list("module_id", flat=True)
    )

    nodes = []
    current_found = False
    for mod in modules:
        is_completed = mod.pk in completed_module_ids
        if is_completed:
            state = "done"
        elif not current_found:
            state = "active"
            current_found = True
            current_module = mod
        else:
            state = "locked"

        nodes.append({
            "id": mod.pk,
            "name": mod.file_name,
            "state": state,
        })

    completed_count = len(completed_module_ids)
    total_count = len(nodes)

    # Current module URL for "Continue Learning" button
    continue_url = None
    if not current_found and nodes:
        # All done — link to last module
        continue_url = f"/viewModule/{nodes[-1]['id']}/"
    elif current_found:
        continue_url = f"/viewModule/{current_module.pk}/"

    # SVG node positions — distribute along a wavy path
    svg_nodes = []
    total = len(nodes)
    for i, node in enumerate(nodes):
        x = 40 + (i / max(1, total - 1)) * 720 if total > 1 else 400
        y = 90 + (30 * ((-1) ** i))  # wavy
        svg_nodes.append({**node, "x": round(x), "y": round(y)})

    return render(request, "gamification/quest_map.html", {
        "subject": subject,
        "nodes": svg_nodes,
        "completed_count": completed_count,
        "total_count": total_count,
        "continue_url": continue_url,
    })
```

- [ ] **Step 2: Add URL patterns**

In `gamification/urls.py`, add:
```python
    path("gamification/quest-map/", views.quest_map_picker, name="quest_map_picker"),
    path("gamification/quest-map/<int:subject_id>/", views.quest_map, name="quest_map"),
```

- [ ] **Step 3: Create quest map picker template**

Create `gamification/templates/gamification/quest_map_picker.html` extending `student_base.html`:
- Title "Quest Map — Choose a Subject"
- Grid of subject cards (3 columns), each showing:
  - Subject name
  - Progress bar (percentage)
  - "X of Y modules completed"
  - Link to `/gamification/quest-map/<id>/`
- Empty state if no enrolled subjects

- [ ] **Step 4: Create quest map template**

Create `gamification/templates/gamification/quest_map.html` extending `student_base.html`:
- Title: subject name
- SVG element (viewBox="0 0 800 180"):
  - Path line connecting all nodes (dashed for locked, solid gold for done)
  - Circle nodes: gold for done, coral (pulsing) for active, grey for locked
  - Text labels below each node
- Below SVG: "X of Y quests completed" + "Continue Learning →" button
- Back to subject picker link

The SVG is rendered server-side using the `svg_nodes` context variable:
```html
<svg class="map-svg" viewBox="0 0 800 180">
    {% for node in nodes %}
    <g class="node node-{{ node.state }}" transform="translate({{ node.x }},{{ node.y }})">
        <circle r="14"/>
        <text class="node-label" y="38">{{ node.name|truncatechars:12 }}</text>
    </g>
    {% endfor %}
</svg>
```

- [ ] **Step 5: Verify quest map renders**

Start dev server, log in as student, visit:
- `/gamification/quest-map/` — should show enrolled subjects
- `/gamification/quest-map/<subject_id>/` — should show module nodes

- [ ] **Step 6: Commit**

```bash
cd ~/classedge && git add gamification/views.py gamification/urls.py gamification/templates/gamification/quest_map_picker.html gamification/templates/gamification/quest_map.html
git commit -m "feat(ui): add quest map with subject picker and SVG progress path"
```

---

## Task 6: Template Migration

**Files:**
- Modify: ~25 student-facing templates

- [ ] **Step 1: Migrate priority templates**

Change the first line of each of these templates from:
```django
{% extends 'base.html' %}
```
to:
```django
{% extends is_student_role|yesno:"student_base.html,base.html" %}
```

**Templates to change:**

```
accounts/templates/accounts/interface/dashboard.html
accounts/templates/accounts/user_level/view_profile.html
accounts/templates/accounts/user_level/view_student_profile.html
course/templates/course/subject_list.html
course/templates/course/view_subject_dashboard.html
course/templates/course/view_subject_dashboard_archived.html
course/templates/course/attendance/attendance_list.html
course/templates/course/attendance/student_subject_attendance.html
course/templates/course/subjectFinishedActivity.html
activity/templates/activity/activities/activity_list.html
activity/templates/activity/activities/activity_detail.html
activity/templates/activity/activities/activity_completed.html
activity/templates/activity/question/display_question.html
activity/templates/activity/question/list_question.html
activity/templates/activity/grade/grade_essay.html
module/templates/module/lesson_list.html
module/templates/module/view_lesson.html
module/templates/module/view_student_progress.html
module/templates/module/progress/progressList.html
module/templates/module/progress/detailProgress.html
module/templates/module/progress/detailsActivityProgress.html
calendars/templates/calendar/calendar.html
calendars/templates/calendar/announcement.html
calendars/templates/calendar/announcement_details.html
calendars/templates/calendar/event.html
calendars/templates/calendar/event_details.html
message/templates/message/inbox.html
message/templates/message/sent.html
message/templates/message/trash.html
gradebookcomponent/templates/gradebookcomponent/activityGrade/student_grades.html
gradebookcomponent/templates/gradebookcomponent/activityGrade/studentGrade.html
gradebookcomponent/templates/gradebookcomponent/activityGrade/studentGradedActivity.html
at_risk/templates/at_risk/dashboard.html
rms/templates/rms/student_SOA.html
```

- [ ] **Step 2: Verify no template errors**

Run: `cd ~/classedge && env/bin/python manage.py check 2>&1`
Expected: No issues.

Start the dev server and log in as both a student AND a teacher to verify:
- Student sees new dark theme on all migrated pages
- Teacher sees original Bootstrap base.html on all pages

- [ ] **Step 3: Commit**

```bash
cd ~/classedge && git add -A
git commit -m "feat(ui): migrate student-facing templates to conditional student_base.html"
```

---

## Task 7: View Tests

**Files:**
- Create: `gamification/tests/test_dashboard_views.py`

- [ ] **Step 1: Write tests**

Create `gamification/tests/test_dashboard_views.py`:
```python
from datetime import date

from django.test import TestCase, Client, override_settings

from ai_content.tests.test_models import _create_test_user, _create_subject
from course.models.semester_model import Semester
from course.models.subject_enrollment_model import SubjectEnrollment
from gamification.models import BadgeDefinition, StudentBadge, StudentGamification
from module.models.module import Module
from subject.models.subject_model import Subject

_GAM_SETTINGS = {
    "GAMIFICATION_XP_RATES": {
        "submission": 50, "early_submission": 75,
        "score_90": 30, "score_75": 15,
        "daily_login": 5, "perfect_attendance_week": 50,
    },
    "GAMIFICATION_STREAK_FREEZE_MONTHLY": 1,
}


@override_settings(**_GAM_SETTINGS)
class StudentDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = _create_test_user(username="dash_stu", role_name="student")
        self.teacher = _create_test_user(username="dash_teach", role_name="teacher")
        self.subject = _create_subject()
        self.semester = Semester.objects.create(
            semester_name="Sem",
            start_date=date(2026, 1, 1),
            end_date=date(2027, 12, 31),
        )
        SubjectEnrollment.objects.create(
            student=self.student, subject=self.subject,
            semester=self.semester, status="enrolled",
        )
        StudentGamification.objects.create(
            student=self.student, total_xp=500, current_level=2,
            login_streak=5, submission_streak=3, accuracy_streak=2,
        )

    def test_student_sees_new_dashboard(self):
        self.client.login(username="dash_stu", password="testpass")
        resp = self.client.get("/dashboard/")
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get("/gamification/dashboard/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "data-theme")

    def test_dashboard_shows_xp(self):
        self.client.login(username="dash_stu", password="testpass")
        resp = self.client.get("/gamification/dashboard/")
        self.assertContains(resp, "500")

    def test_teacher_sees_old_dashboard(self):
        self.client.login(username="dash_teach", password="testpass")
        resp = self.client.get("/dashboard/")
        self.assertEqual(resp.status_code, 200)
        # Teacher should NOT be redirected
        self.assertNotContains(resp, "data-theme")

    def test_unauthenticated_redirects(self):
        resp = self.client.get("/gamification/dashboard/")
        self.assertEqual(resp.status_code, 302)


@override_settings(**_GAM_SETTINGS)
class LeaderboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = _create_test_user(username="lb_stu", role_name="student")

    def test_leaderboard_renders(self):
        self.client.login(username="lb_stu", password="testpass")
        resp = self.client.get("/gamification/leaderboard/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Leaderboard")


@override_settings(**_GAM_SETTINGS)
class BadgeCollectionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = _create_test_user(username="bc_stu", role_name="student")

    def test_badge_collection_renders(self):
        self.client.login(username="bc_stu", password="testpass")
        resp = self.client.get("/gamification/badges/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Badge")

    def test_shows_earned_vs_total(self):
        self.client.login(username="bc_stu", password="testpass")
        badge = BadgeDefinition.objects.first()
        if badge:
            StudentBadge.objects.create(student=self.student, badge=badge)
        resp = self.client.get("/gamification/badges/")
        self.assertEqual(resp.status_code, 200)


@override_settings(**_GAM_SETTINGS)
class CalendarTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = _create_test_user(username="cal_stu", role_name="student")

    def test_calendar_renders(self):
        self.client.login(username="cal_stu", password="testpass")
        resp = self.client.get("/gamification/calendar/")
        self.assertEqual(resp.status_code, 200)

    def test_calendar_prev_next(self):
        self.client.login(username="cal_stu", password="testpass")
        resp = self.client.get("/gamification/calendar/?year=2026&month=3")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "March 2026")


@override_settings(**_GAM_SETTINGS)
class QuestMapTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = _create_test_user(username="qm_stu", role_name="student")
        self.subject = _create_subject()
        self.semester = Semester.objects.create(
            semester_name="Sem",
            start_date=date(2026, 1, 1),
            end_date=date(2027, 12, 31),
        )
        SubjectEnrollment.objects.create(
            student=self.student, subject=self.subject,
            semester=self.semester, status="enrolled",
        )

    def test_picker_shows_subjects(self):
        self.client.login(username="qm_stu", password="testpass")
        resp = self.client.get("/gamification/quest-map/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.subject.subject_name)

    def test_map_renders_for_subject(self):
        self.client.login(username="qm_stu", password="testpass")
        resp = self.client.get(f"/gamification/quest-map/{self.subject.pk}/")
        self.assertEqual(resp.status_code, 200)


@override_settings(**_GAM_SETTINGS)
class TemplateSwitchingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = _create_test_user(username="tmpl_stu", role_name="student")
        self.teacher = _create_test_user(username="tmpl_teach", role_name="teacher")

    def test_student_gets_student_base(self):
        self.client.login(username="tmpl_stu", password="testpass")
        resp = self.client.get("/gamification/leaderboard/")
        self.assertContains(resp, "student_theme")

    def test_theme_cookie_respected(self):
        self.client.login(username="tmpl_stu", password="testpass")
        self.client.cookies["theme"] = "light"
        resp = self.client.get("/gamification/dashboard/")
        self.assertContains(resp, 'data-theme="light"')
```

- [ ] **Step 2: Run tests**

Run: `cd ~/classedge && env/bin/python manage.py test gamification.tests.test_dashboard_views --keepdb -v2`
Expected: All ~13 tests PASS

- [ ] **Step 3: Run full gamification test suite**

Run: `cd ~/classedge && env/bin/python manage.py test gamification --keepdb 2>&1 | tail -5`
Expected: All tests PASS (40 engine + ~13 UI = ~53 total)

- [ ] **Step 4: Commit**

```bash
cd ~/classedge && git add gamification/tests/test_dashboard_views.py
git commit -m "test(ui): add dashboard, leaderboard, badges, calendar, quest map view tests"
```

---

## Summary

| Task | What it builds | Tests |
|------|---------------|-------|
| 1 | Theme CSS/JS + student_base.html + context processor | — |
| 2 | Student dashboard view + template | — |
| 3 | Leaderboard + badge collection views + templates | — |
| 4 | Student calendar view + template | — |
| 5 | Quest map view + templates | — |
| 6 | Template migration (~25 templates) | — |
| 7 | View + template tests | ~13 |

**Total new tests: ~13**

**Note on template-heavy tasks:** Tasks 1-5 create large HTML templates. Use the `frontend-design` skill when implementing these to ensure high design quality matching the mockup. The CSS file (Task 1, Step 4) and dashboard template (Task 2, Step 4) are the two largest files — reference the mockup at `~/classedge-hccci-repo/mockup-student-dashboard.html` for exact styling.
