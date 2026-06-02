# Teacher My Courses sidebar widgets — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a right-hand sidebar with three glanceable widgets (upcoming news, unread messages, top students) to the teacher's My Courses page.

**Architecture:** All changes scoped to two files — `subject/views/subject_view.py` (build three context vars on the teacher branch only) and `templates/teacher/subject_list.html` (wrap existing grid in a 2-column layout, add the sidebar markup and styles). No models, migrations, or new URLs.

**Tech Stack:** Django templates, Django ORM, vanilla CSS (uses existing teacher tokens), Django humanize template tags (`naturaltime`, `intcomma`).

**Spec:** `docs/superpowers/specs/2026-04-30-teacher-courses-sidebar-widgets-design.md`

---

### Task 1: Add view context for the three widgets (teacher branch only)

**Files:**
- Modify: `subject/views/subject_view.py` — `subject(request)` function (the teacher branch is around lines 102–114; the post-pagination block is around line 142+).

- [ ] **Step 1: Add new imports near the top of the file**

Add these imports after the existing `from django.db.models import Q, Count` line and after the existing `from course.models import Semester, SubjectEnrollment` line:

```python
from datetime import date, datetime, timedelta
from calendars.models import Holiday, Event, Announcement
from message.models import Message
from gamification.models import StudentGamification
```

Note: `from datetime import date` already exists; replace it with `from datetime import date, datetime, timedelta` (do not add a duplicate line). The other imports are new.

- [ ] **Step 2: Build the three context variables, only on the teacher branch**

Find the existing post-pagination block:

```python
    if user_role == 'teacher':
        page_subject_ids = [s.id for s in page_obj]
        enrollment_filter = Q(student__isnull=False, status='enrolled', subject_id__in=page_subject_ids)
        if selected_semester:
            enrollment_filter &= Q(semester=selected_semester)
        enrollment_counts = dict(
            SubjectEnrollment.objects
            .filter(enrollment_filter)
            .values('subject_id')
            .annotate(c=Count('id'))
            .values_list('subject_id', 'c')
        )
        for subject in page_obj:
            subject.enrolled_count = enrollment_counts.get(subject.id, 0)
```

Append the following inside the same `if user_role == 'teacher':` block (right after the `for subject in page_obj` loop):

```python
        # ---- Upcoming feed (announcements + holidays + events, today..+14 days) ----
        today_date = date.today()
        window_end = today_date + timedelta(days=14)
        ICON_MAP = {
            'holiday': 'umbrella-beach',
            'event': 'calendar-day',
            'announcement': 'bullhorn',
        }
        upcoming_raw = []
        for h in Holiday.objects.filter(date__gte=today_date, date__lte=window_end):
            upcoming_raw.append({'type': 'holiday', 'title': h.title, 'date': h.date})
        for e in Event.objects.filter(start_date__gte=today_date, start_date__lte=window_end):
            upcoming_raw.append({'type': 'event', 'title': e.title, 'date': e.start_date})
        for a in Announcement.objects.filter(date__gte=today_date, date__lte=window_end):
            upcoming_raw.append({'type': 'announcement', 'title': a.title, 'date': a.date})
        upcoming_raw.sort(key=lambda x: x['date'])
        upcoming_items = [
            {**item, 'icon': ICON_MAP[item['type']]}
            for item in upcoming_raw[:6]
        ]

        # ---- Unread messages (top 4) ----
        unread_qs = (
            Message.objects
            .filter(messageunreadstatus__user=request.user)
            .select_related('sender')
            .order_by('-timestamp')
        )
        unread_messages_total = unread_qs.count()
        unread_messages = list(unread_qs[:4])

        # ---- Class leaderboard (top 5 students across teacher's subjects) ----
        teacher_subject_ids = list(subjects.values_list('id', flat=True))
        class_leaderboard = []
        if selected_semester and teacher_subject_ids:
            enrolled_student_ids = (
                SubjectEnrollment.objects
                .filter(
                    subject_id__in=teacher_subject_ids,
                    semester=selected_semester,
                    status='enrolled',
                    student__isnull=False,
                )
                .values_list('student_id', flat=True)
                .distinct()
            )
            for rank, sg in enumerate(
                StudentGamification.objects
                .filter(student_id__in=enrolled_student_ids)
                .select_related('student')
                .order_by('-total_xp')[:5],
                start=1,
            ):
                full_name = sg.student.get_full_name() or sg.student.username
                initial = (sg.student.first_name or sg.student.username or '?')[:1].upper()
                class_leaderboard.append({
                    'rank': rank,
                    'name': full_name,
                    'initial': initial,
                    'xp': sg.total_xp,
                })

        context['upcoming_items'] = upcoming_items
        context['unread_messages'] = unread_messages
        context['unread_messages_total'] = unread_messages_total
        context['class_leaderboard'] = class_leaderboard
```

Important: `context` is built later in the function (around line 145). The new code references `context`, so it must be inserted **after** the `context = { … }` dict literal and **after** `context.update(pagination_context)`. If the existing teacher post-pagination block sits before `context = …`, move the new block to live just after `context.update(pagination_context)` and gate it with `if user_role == 'teacher':`. (Verify before editing.)

- [ ] **Step 3: Run the dev server and check `/subject/` as a teacher**

```
python manage.py runserver
```

Expected: page loads without errors. Sidebar context vars are present but not yet rendered (no template changes yet). No 500.

- [ ] **Step 4: Commit**

```bash
git add subject/views/subject_view.py
git commit -m "feat(teacher-courses): add sidebar widget context (news/messages/leaderboard)"
```

---

### Task 2: Render the sidebar widgets in the template

**Files:**
- Modify: `templates/teacher/subject_list.html` — add `{% load humanize %}`, wrap existing content in a 2-column layout, add the `<aside>` block, append CSS.

- [ ] **Step 1: Add `humanize` load**

At the top of the file, after `{% load static %}`, add:

```django
{% load humanize %}
```

- [ ] **Step 2: Append sidebar styles to the existing `<style>` block in `extra_css`**

Find the closing `</style>` tag inside the `{% block extra_css %}` block (just before `{% endblock %}`). Insert the following CSS right before that `</style>`:

```css
  /* ---- 2-column layout with right sidebar ---- */
  .courses-layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 340px;
    gap: 24px;
    align-items: start;
  }
  @media (max-width: 1023px) {
    .courses-layout { grid-template-columns: 1fr; }
  }
  .courses-main { min-width: 0; }

  .courses-sidebar {
    display: flex;
    flex-direction: column;
    gap: 16px;
    position: sticky;
    top: 16px;
  }
  @media (max-width: 1023px) {
    .courses-sidebar { position: static; }
  }

  .sidebar-card {
    background: var(--paper);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    box-shadow: var(--shadow);
    padding: 16px 18px 14px;
  }
  .sidebar-card-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
  }
  .sidebar-card-head h3 {
    font-family: var(--display);
    font-size: 15px;
    font-weight: 600;
    color: var(--forest);
    margin: 0;
    letter-spacing: -0.01em;
  }
  .sidebar-badge {
    background: var(--gold);
    color: var(--cream);
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 100px;
    line-height: 1.4;
  }
  .sidebar-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 0;
    border-bottom: 1px solid var(--border);
    text-decoration: none;
    color: var(--ink);
    font-size: 12.5px;
    line-height: 1.35;
  }
  .sidebar-row:last-child { border-bottom: none; }
  .sidebar-row:hover { color: var(--forest); }
  .sidebar-row > i { color: var(--gold); width: 16px; text-align: center; flex-shrink: 0; }
  .sidebar-row-title {
    flex: 1 1 auto;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-weight: 500;
    color: var(--forest);
  }
  .sidebar-row-meta {
    color: var(--ink-muted);
    font-size: 11px;
    flex-shrink: 0;
    white-space: nowrap;
  }
  .sidebar-row-body {
    flex: 1 1 auto;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 1px;
  }
  .sidebar-row-snippet {
    color: var(--ink-dim);
    font-size: 11.5px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .sidebar-avatar {
    width: 26px; height: 26px;
    border-radius: 50%;
    background: var(--gold-bg);
    color: var(--gold);
    font-size: 12px;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .sidebar-rank {
    width: 22px; height: 22px;
    border-radius: 50%;
    background: var(--cream-2);
    color: var(--forest);
    font-size: 11px;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .sidebar-empty {
    color: var(--ink-muted);
    font-size: 12px;
    font-style: italic;
    padding: 6px 0 2px;
  }
  .sidebar-card-foot {
    margin-top: 10px;
    padding-top: 8px;
    border-top: 1px dashed var(--border);
    text-align: right;
  }
  .sidebar-card-foot a {
    color: var(--forest);
    font-size: 11.5px;
    font-weight: 600;
    text-decoration: none;
  }
  .sidebar-card-foot a:hover { color: var(--gold); }
```

- [ ] **Step 3: Wrap the existing courses block + add the sidebar**

Find this section in the template (inside `{% block content %}`):

```django
<div class="courses-page">
  <div class="courses-header">
    …
  </div>

  <form method="get" class="courses-search">
    …
  </form>

  <div class="course-grid">
    …
  </div>

  {% if page_obj.paginator.num_pages > 1 %}
    <nav class="pagination-row" aria-label="Pagination">
      …
    </nav>
  {% endif %}
</div>
```

Restructure it so the search/grid/pagination live inside `<div class="courses-main">`, and add `<aside class="courses-sidebar">` next to it inside a wrapping `<div class="courses-layout">`. The header stays above the layout.

The new structure (replace the content of `{% block content %}` with this exact markup, preserving the existing header and inner blocks where indicated):

```django
<div class="courses-page">
  <div class="courses-header">
    <div class="courses-title-block">
      <h1 class="page-title">My <em>Courses</em></h1>
      <div class="page-sub">
        {% if selected_semester %}
          {{ selected_semester.semester_name }} &middot; {{ selected_semester.get_academic_year }}
        {% else %}
          {% now 'Y' as current_year %}
          {{ current_year }}&ndash;{{ current_year|add:'1' }} academic year
        {% endif %}
      </div>
    </div>
  </div>

  <div class="courses-layout">
    <div class="courses-main">
      <form method="get" class="courses-search">
        <input type="text" name="search" placeholder="Search by course name, code, or room..." value="{{ search_query }}" />
        {% if selected_semester %}<input type="hidden" name="semester" value="{{ selected_semester.id }}" />{% endif %}
        <button type="submit"><i class="fas fa-search"></i> Search</button>
        {% if search_query %}
          <a class="clear-btn" href="{% url 'subject' %}{% if selected_semester %}?semester={{ selected_semester.id }}{% endif %}">Clear</a>
        {% endif %}
      </form>

      <div class="course-grid">
        {% for subject in page_obj %}
          <a class="course-card" href="{% url 'moduleList' subject.id %}">
            <div class="course-image">
              {% if subject.subject_photo and subject.subject_photo.url %}
                <img src="{{ subject.subject_photo.url }}" alt="{{ subject.subject_name }}" />
              {% else %}
                <div class="course-image-placeholder"><i class="fas fa-book"></i></div>
              {% endif %}
              {% if subject.subject_type %}
                <span class="course-image-pill course-type-pill type-{{ subject.subject_type|lower }}">{{ subject.subject_type }}</span>
              {% endif %}
            </div>
            <div class="course-body">
              <div class="course-name">{{ subject.subject_name }}</div>
              {% if subject.subject_code %}
                <div class="course-code">{{ subject.subject_code }}</div>
              {% endif %}

              <div class="course-meta">
                <div class="course-meta-item">
                  <i class="fas fa-users"></i>
                  <span>{{ subject.enrolled_count|default:0 }} enrolled</span>
                </div>
                {% if subject.room_number %}
                  <div class="course-meta-item">
                    <i class="fas fa-door-open"></i>
                    <span>Room {{ subject.room_number }}</span>
                  </div>
                {% endif %}
                {% if subject.substitute_teacher %}
                  <div class="course-meta-item">
                    <i class="fas fa-user-friends"></i>
                    <span>Sub: {{ subject.substitute_teacher.first_name }} {{ subject.substitute_teacher.last_name }}</span>
                  </div>
                {% endif %}
              </div>

              <div class="course-schedule">
                {% for schedule in subject.schedules.all %}
                  {% if not selected_semester or not schedule.semester_id or schedule.semester_id == selected_semester.id %}
                    <div class="course-schedule-row">
                      <i class="far fa-clock"></i>
                      <span class="course-schedule-days">{{ schedule.days_of_week|join:", " }}</span>
                      <span>&middot; {{ schedule.schedule_start_time|time:"g:i A" }}&ndash;{{ schedule.schedule_end_time|time:"g:i A" }}</span>
                    </div>
                  {% endif %}
                {% empty %}
                  <div class="course-schedule-empty"><i class="far fa-clock"></i> No schedule yet</div>
                {% endfor %}
              </div>
            </div>
          </a>
        {% empty %}
          <div class="empty-courses">
            <i class="fas fa-book-open"></i>
            <div class="lead">No courses assigned</div>
            <div style="font-size: 13px;">You aren't assigned to any courses for this semester.</div>
          </div>
        {% endfor %}
      </div>

      {% if page_obj.paginator.num_pages > 1 %}
        <nav class="pagination-row" aria-label="Pagination">
          {% if page_obj.has_previous %}
            <a href="?page={{ page_obj.previous_page_number }}{% if query_string %}&{{ query_string }}{% endif %}"><i class="fas fa-chevron-left"></i></a>
          {% else %}
            <span class="disabled"><i class="fas fa-chevron-left"></i></span>
          {% endif %}
          {% for page_num in page_range %}
            {% if page_num == page_obj.number %}
              <span class="active">{{ page_num }}</span>
            {% else %}
              <a href="?page={{ page_num }}{% if query_string %}&{{ query_string }}{% endif %}">{{ page_num }}</a>
            {% endif %}
          {% endfor %}
          {% if page_obj.has_next %}
            <a href="?page={{ page_obj.next_page_number }}{% if query_string %}&{{ query_string }}{% endif %}"><i class="fas fa-chevron-right"></i></a>
          {% else %}
            <span class="disabled"><i class="fas fa-chevron-right"></i></span>
          {% endif %}
        </nav>
      {% endif %}
    </div>

    <aside class="courses-sidebar">
      <section class="sidebar-card">
        <header class="sidebar-card-head">
          <h3>Upcoming</h3>
        </header>
        {% for item in upcoming_items %}
          <a class="sidebar-row" href="{% url 'announcement_list' %}">
            <i class="fas fa-{{ item.icon }}"></i>
            <span class="sidebar-row-title">{{ item.title }}</span>
            <span class="sidebar-row-meta">{{ item.date|date:"M d" }}</span>
          </a>
        {% empty %}
          <div class="sidebar-empty">Nothing coming up.</div>
        {% endfor %}
        {% if upcoming_items %}
          <div class="sidebar-card-foot">
            <a href="{% url 'announcement_list' %}">View all &rarr;</a>
          </div>
        {% endif %}
      </section>

      <section class="sidebar-card">
        <header class="sidebar-card-head">
          <h3>Messages</h3>
          {% if unread_messages_total %}<span class="sidebar-badge">{{ unread_messages_total }}</span>{% endif %}
        </header>
        {% for msg in unread_messages %}
          <a class="sidebar-row" href="{% url 'view_message' msg.id %}">
            <span class="sidebar-avatar">{% firstof msg.sender.first_name|slice:':1'|upper msg.sender.username|slice:':1'|upper '?' %}</span>
            <span class="sidebar-row-body">
              <span class="sidebar-row-title">{{ msg.sender.get_full_name|default:msg.sender.username }}</span>
              <span class="sidebar-row-snippet">{{ msg.subject|default:msg.body|truncatechars:60 }}</span>
            </span>
            <span class="sidebar-row-meta">{{ msg.timestamp|naturaltime }}</span>
          </a>
        {% empty %}
          <div class="sidebar-empty">All caught up.</div>
        {% endfor %}
        {% if unread_messages %}
          <div class="sidebar-card-foot">
            <a href="{% url 'inbox' %}">Open inbox &rarr;</a>
          </div>
        {% endif %}
      </section>

      <section class="sidebar-card">
        <header class="sidebar-card-head">
          <h3>Top students</h3>
        </header>
        {% for row in class_leaderboard %}
          <div class="sidebar-row">
            <span class="sidebar-rank">{{ row.rank }}</span>
            <span class="sidebar-avatar">{{ row.initial }}</span>
            <span class="sidebar-row-title">{{ row.name }}</span>
            <span class="sidebar-row-meta">{{ row.xp|intcomma }} XP</span>
          </div>
        {% empty %}
          <div class="sidebar-empty">No data yet.</div>
        {% endfor %}
      </section>
    </aside>
  </div>
</div>
```

- [ ] **Step 4: Reload the dev server page as a teacher and verify**

```
python manage.py runserver
```

Open `/subject/` while logged in as a teacher. Verify:
- Three sidebar widgets render to the right of the courses grid on a wide screen.
- Resizing the window below ~1024px wide stacks the sidebar below the grid.
- Empty states ("Nothing coming up." / "All caught up." / "No data yet.") render when there's no data.
- No template-syntax errors and no 500.

- [ ] **Step 5: Commit**

```bash
git add templates/teacher/subject_list.html
git commit -m "feat(teacher-courses): add right-sidebar widgets (news/messages/leaderboard)"
```

---

## Self-review

**Spec coverage:**
- Layout (2-col, ≥1024px → stacked): Task 2 step 2 + step 3.
- Three widget cards using teacher tokens: Task 2 step 2.
- Upcoming feed (Holiday + Event + Announcement, today..+14 days, sorted, capped 6): Task 1 step 2.
- Icon mapping in view: Task 1 step 2.
- Unread messages (top 4 + total): Task 1 step 2.
- Per-message link to `view_message`: Task 2 step 3.
- Inbox footer link: Task 2 step 3.
- Leaderboard top 5 across teacher's subjects, semester-scoped: Task 1 step 2.
- Empty states: Task 2 step 3.
- Teacher-only context: gated by `if user_role == 'teacher':` in Task 1 step 2.
- Manual verification: Task 2 step 4 (matches spec testing/verification section).

**Placeholder scan:** None. All code is concrete. The only conditional note is in Task 1 step 2 about whether the existing teacher block sits before or after `context = …`; this is unavoidable since I haven't seen the post-modification line numbers, but the instruction is explicit ("verify before editing").

**Type consistency:** `upcoming_items` keys (`type`, `title`, `date`, `icon`) match between Task 1 (build) and Task 2 (template). `unread_messages` items are `Message` instances; template accesses `msg.sender`, `msg.id`, `msg.subject`, `msg.body`, `msg.timestamp` — all real fields. `class_leaderboard` keys (`rank`, `name`, `initial`, `xp`) match between view and template.

---

## Execution handoff

Plan complete. Two execution options:

1. **Subagent-Driven** (recommended) — fresh subagent per task with review between tasks.
2. **Inline Execution** — execute tasks in this session with checkpoints.

Which approach?
