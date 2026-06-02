# Teacher My Courses sidebar widgets — design

## Context

The teacher's "My Courses" page (`templates/teacher/subject_list.html`, served by
`subject.views.subject_view.subject` when `user_role == 'teacher'`) currently shows only
a search bar and a grid of course cards. We want to mirror three feature areas the
student already has access to (via the student base nav: News, Messages, Leaderboard)
by surfacing them as glanceable widgets next to the courses grid.

This change is teacher-only. The student template and other teacher pages are unchanged
in this iteration.

## Goals

- Give teachers an at-a-glance view of upcoming announcements/holidays/events,
  unread messages, and the top students across their classes — without leaving the
  My Courses page.
- Keep the courses grid as the primary content; the widgets sit in a right-hand sidebar.
- Reuse existing teacher tokens (`--paper`, `--forest`, `--gold`, `--ink-dim`,
  `--shadow`, `--radius`) so the sidebar feels native.

## Non-goals

- Changing the student `subject_list.html`.
- Adding the sidebar to other teacher pages (dashboard, gradebook, etc.).
- New nav items in `teacher_base.html` (News / Messages / Leaderboard nav links).
- Notifications, websocket updates, or real-time refresh — widgets render at page load only.

## Layout

A two-column layout on screens ≥1024px:

```
┌─────────────────────────────────┬──────────────────┐
│ courses header + search         │                  │
│                                 │   Upcoming       │
│ courses grid                    │                  │
│ (auto-fill, minmax(280px, 1fr)) │   Messages       │
│                                 │                  │
│                                 │   Top students   │
│ pagination                      │                  │
└─────────────────────────────────┴──────────────────┘
```

- Outer container: `.courses-layout` — CSS grid `grid-template-columns: minmax(0, 1fr) 340px`,
  `gap: 24px`, items aligned to the top.
- Below 1024px: `.courses-layout` collapses to one column (`grid-template-columns: 1fr`),
  sidebar drops below the courses block.
- Each widget is a card: `var(--paper)` background, `1px solid var(--border)`,
  `border-radius: var(--radius-sm)`, `box-shadow: var(--shadow)`, padding `18px 20px`,
  with a heading row (title + optional badge/link) and body content.

## Widget content

### 1. Upcoming (News)

Combined chronological feed of `calendars.Holiday`, `calendars.Event`, and
`calendars.Announcement` records dated today through today + 14 days, sorted ascending,
capped at 6 items.

Each row:
- Type icon: holiday → `fa-umbrella-beach`, event → `fa-calendar-day`,
  announcement → `fa-bullhorn`. Color: `var(--gold)`.
- Title (truncate to one line via `text-overflow: ellipsis`).
- Short date: e.g. "May 02" (`{{ item.date|date:"M d" }}`).
- Whole row is a link to a sensible detail destination:
  - announcement → `{% url 'announcement_list' %}` (jump to the list, list URL is
    fine since per-announcement detail isn't required for this iteration)
  - event/holiday → `{% url 'announcement_list' %}` as well (calendars share the
    announcements page — confirmed from `templates/calendars/announcement.html`)

Empty state: small icon + "Nothing coming up." footer link omitted when empty.

Footer (when items exist): right-aligned "View all →" link to `announcement_list`.

### 2. Messages

Top 4 unread messages for `request.user` (the teacher), via `MessageUnreadStatus`.

Heading row:
- Title: "Messages"
- If `unread_messages_total > 0`, badge pill on the right: `{{ unread_messages_total }}`
  in gold; otherwise no badge.

Each row:
- Sender initial avatar (small circle with first letter, gold background).
- Sender full name (one line, ellipsis).
- Subject if non-empty, else first 60 chars of body (one line, ellipsis).
- Relative timestamp: `{{ msg.timestamp|naturaltime }}` (uses `humanize` template tag).
- Each row links to `{% url 'view_message' msg.id %}` (per-message detail).

Empty state: "All caught up." (no items)

Footer: "Open inbox →" link to `{% url 'inbox' %}`.

### 3. Leaderboard

Top 5 students by `gamification.StudentGamification.total_xp`, scoped to students
enrolled (active, this semester) in any subject the teacher teaches.

Each row:
- Rank number (1–5) in a small circle.
- Initial avatar (first letter of first name).
- Full name (ellipsis).
- XP value, right-aligned, e.g. `1,240 XP` (`{{ row.xp|intcomma }} XP`).

Empty state: trophy icon + "No data yet." (no items)

Footer: omitted (no per-class leaderboard URL exists yet for teachers; opening one
is out of scope for this iteration).

## Data flow (view changes)

File: `subject/views/subject_view.py`, function `subject(request)`.

After pagination, when `user_role == 'teacher'`, build three context variables:

### `upcoming_items`

```python
from calendars.models import Holiday, Event, Announcement
from datetime import date, timedelta

today = date.today()
window = today + timedelta(days=14)

items = []
for h in Holiday.objects.filter(date__gte=today, date__lte=window):
    items.append({"type": "holiday", "title": h.title, "date": h.date})
for e in Event.objects.filter(start_date__gte=today, start_date__lte=window):
    items.append({"type": "event", "title": e.title, "date": e.start_date})
for a in Announcement.objects.filter(date__gte=today, date__lte=window):
    items.append({"type": "announcement", "title": a.title, "date": a.date})
items.sort(key=lambda x: x["date"])
upcoming_items = items[:6]
```

Note: department-scoped filtering is intentionally left as "all departments" for
this iteration (matches what the student calendar widget does in `student_dashboard.html`).

### `unread_messages` and `unread_messages_total`

```python
from message.models import Message

unread_qs = (
    Message.objects
    .filter(messageunreadstatus__user=request.user)
    .select_related('sender')
    .order_by('-timestamp')
)
unread_messages_total = unread_qs.count()
unread_messages = list(unread_qs[:4])
```

### `class_leaderboard`

```python
from gamification.models import StudentGamification

# subjects already filtered to "this teacher, this semester" — reuse subject_ids
teacher_subject_ids = list(subjects.values_list('id', flat=True))

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
    leaderboard_rows = (
        StudentGamification.objects
        .filter(student_id__in=enrolled_student_ids)
        .select_related('student')
        .order_by('-total_xp')[:5]
    )
    class_leaderboard = []
    for rank, sg in enumerate(leaderboard_rows, 1):
        full_name = sg.student.get_full_name() or sg.student.username
        initial = (sg.student.first_name or sg.student.username)[:1].upper()
        class_leaderboard.append({
            "rank": rank,
            "name": full_name,
            "initial": initial,
            "xp": sg.total_xp,
        })
else:
    class_leaderboard = []
```

All three vars are only added to the context dict on the teacher branch. Student and
registrar branches do not add them; their templates ignore the keys.

## Template changes

File: `templates/teacher/subject_list.html`.

1. Add `{% load humanize %}` at the top (required for `naturaltime` and `intcomma`).
2. Wrap the existing `.course-grid` (and pagination) in a left column inside a new
   `.courses-layout` outer container; add a sibling `<aside class="courses-sidebar">`.
3. In the `<aside>`, render three `<section class="sidebar-card">` blocks, one per widget.
4. Append a CSS block to `extra_css` with:
   - `.courses-layout { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 24px; align-items: start; }`
   - `@media (max-width: 1023px) { .courses-layout { grid-template-columns: 1fr; } }`
   - Per-widget styles (heading typography, row layout, empty states).

Markup sketch:

```html
<div class="courses-layout">
  <div class="courses-main">
    <form class="courses-search">…</form>
    <div class="course-grid">…</div>
    {# pagination #}
  </div>
  <aside class="courses-sidebar">
    <section class="sidebar-card">
      <header class="sidebar-card-head">
        <h3>Upcoming</h3>
      </header>
      {% for item in upcoming_items %}
        <a class="sidebar-row sidebar-row--news" href="{% url 'announcement_list' %}">
          <i class="fas fa-{{ item.icon }}"></i>
          <span class="sidebar-row-title">{{ item.title }}</span>
          <span class="sidebar-row-meta">{{ item.date|date:"M d" }}</span>
        </a>
      {% empty %}
        <div class="sidebar-empty">Nothing coming up.</div>
      {% endfor %}
    </section>
    <section class="sidebar-card">
      <header class="sidebar-card-head">
        <h3>Messages</h3>
        {% if unread_messages_total %}<span class="sidebar-badge">{{ unread_messages_total }}</span>{% endif %}
      </header>
      {% for msg in unread_messages %}
        <a class="sidebar-row sidebar-row--msg" href="{% url 'view_message' msg.id %}">
          <span class="sidebar-avatar">{{ msg.sender.first_name|slice:":1"|upper }}</span>
          <span class="sidebar-row-body">
            <span class="sidebar-row-title">{{ msg.sender.get_full_name|default:msg.sender.username }}</span>
            <span class="sidebar-row-snippet">{{ msg.subject|default:msg.body|truncatechars:60 }}</span>
          </span>
          <span class="sidebar-row-meta">{{ msg.timestamp|naturaltime }}</span>
        </a>
      {% empty %}
        <div class="sidebar-empty">All caught up.</div>
      {% endfor %}
    </section>
    <section class="sidebar-card">
      <header class="sidebar-card-head">
        <h3>Top students</h3>
      </header>
      {% for row in class_leaderboard %}
        <div class="sidebar-row sidebar-row--lb">
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
```

The icon mapping (`fa-umbrella-beach` / `fa-calendar-day` / `fa-bullhorn`) is computed
in the view to keep the template simple — each `upcoming_items` entry includes an
`icon` key alongside `type`, `title`, `date`.

## Testing / verification

- Manual: log in as a teacher, open `/subject/`, verify the three widgets render with
  realistic data; verify empty states for fresh accounts; resize the viewport below
  1024px and confirm the sidebar drops under the grid.
- Automated tests are out of scope for this UI iteration (no test infrastructure for
  templates is currently used in this app; manual verification is the existing pattern).

## Out of scope

- Per-subject leaderboard selector (option (b) from brainstorming).
- Real-time updates / polling.
- Departmental filtering of the upcoming feed.
- Notification mark-as-read interaction inside the sidebar.
- Adding the sidebar to other teacher pages.
