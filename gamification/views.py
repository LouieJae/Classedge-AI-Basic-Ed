import calendar as cal_module
import json as _json
import math
from datetime import date, datetime, timedelta

from django.contrib.auth.decorators import login_required, permission_required
from django.db import models, transaction
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from activity.models.activity_model import Activity
from activity.models.student_activity_model import StudentActivity
from calendars.models import Announcement, Event, Holiday
from course.models.semester_model import Semester
from course.models.subject_enrollment_model import SubjectEnrollment
from gamification.badges import compute_badge_progress
from gamification.models import BadgeDefinition, StudentBadge, StudentGamification
from gamification.quest_grading import get_student_quest_score
from gamification.quest_models import Quest, QuestAttempt
from gamification.teacher_models import TeacherRecognition, TeacherRating
from module.models.module import Module
from module.models.student_progress import StudentProgress
from subject.models.subject_model import Subject
from subject.models.schedule_model import Schedule


def _module_done_by_quests(student, module):
    """Return True if all published quests for this module are correctly attempted.
    Falls back to legacy StudentProgress.completed when no quests exist."""
    published = Quest.objects.filter(module=module, status="published")
    if not published.exists():
        sp = StudentProgress.objects.filter(student=student, module=module).first()
        return bool(sp and sp.completed)
    correct = QuestAttempt.objects.filter(
        quest__in=published, student=student, is_correct=True
    ).values_list("quest_id", flat=True)
    return set(published.values_list("id", flat=True)) == set(correct)


@login_required
def student_dashboard(request):
    user = request.user
    now = timezone.localtime(timezone.now())

    hour = now.hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

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

    semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    quests = []
    enrolled_subject_ids = []
    schedule_today = []
    due_this_week_count = 0
    if semester:
        enrolled_subject_ids = list(SubjectEnrollment.objects.filter(
            student=user, semester=semester, status="enrolled",
        ).values_list("subject_id", flat=True))

        # ── Today's classes (HIGHLIGHT) ─────────────────────────
        today_short = now.strftime("%a")  # "Mon", "Tue", ...
        sched_qs = (
            Schedule.objects
            .filter(
                subject_id__in=enrolled_subject_ids,
                days_of_week__icontains=today_short,
            )
            .select_related("subject")
            .filter(models.Q(semester=semester) | models.Q(semester__isnull=True))
        )
        now_t = now.time()
        for sch in sched_qs:
            start_t = sch.schedule_start_time
            end_t = sch.schedule_end_time
            if start_t and end_t and start_t <= now_t <= end_t:
                status = "now"
            elif start_t and start_t > now_t:
                status = "upcoming"
            else:
                status = "done"
            schedule_today.append({
                "subject": sch.subject,
                "start_time": start_t,
                "end_time": end_t,
                "room": sch.subject.room_number or "",
                "status": status,
            })
        status_order = {"now": 0, "upcoming": 1, "done": 2}
        schedule_today.sort(key=lambda s: (status_order[s["status"]], s["start_time"] or datetime.min.time()))

        # ── "Due this week" headline number ─────────────────────
        week_ahead = now + timedelta(days=7)
        due_this_week_count = (
            Activity.objects
            .filter(
                subject_id__in=enrolled_subject_ids,
                status=True,
                end_time__gte=now,
                end_time__lte=week_ahead,
            )
            .exclude(activity_type__name__iexact="Participation")
            .exclude(classroom_mode=True)
            .count()
        )

        upcoming_activities = Activity.objects.filter(
            subject_id__in=enrolled_subject_ids, end_time__gte=now, status=True,
        ).exclude(activity_type__name__iexact="Participation").exclude(
            studentquestion__is_participation=True
        ).exclude(classroom_mode=True).select_related("subject").order_by("end_time")[:5]

        completed_ids = set(StudentActivity.objects.filter(
            student=user, activity__in=upcoming_activities,
        ).values_list("activity_id", flat=True))

        for act in upcoming_activities:
            quests.append({
                "name": act.activity_name,
                "subject": act.subject.subject_name if act.subject else "",
                "done": act.pk in completed_ids,
                "xp": 50,
                "url": reverse("assessment-details", args=[act.id]),
            })

    completed_count = sum(1 for q in quests if q["done"])

    recent_badges = StudentBadge.objects.filter(student=user).select_related("badge").order_by("-earned_at")[:6]
    total_badges = BadgeDefinition.objects.filter(is_active=True).count()
    earned_count = StudentBadge.objects.filter(student=user).count()

    earned_badge_ids = set(
        StudentBadge.objects.filter(student=user).values_list("badge_id", flat=True)
    )
    almost_there = []
    for bd in BadgeDefinition.objects.filter(is_active=True).exclude(pk__in=earned_badge_ids):
        prog = compute_badge_progress(user, bd)
        if 0 < prog < 100:
            almost_there.append({"badge": bd, "progress": prog})
    almost_there.sort(key=lambda x: -x["progress"])
    almost_there = almost_there[:3]

    leaderboard = []
    if semester and enrolled_subject_ids:
        classmate_ids = SubjectEnrollment.objects.filter(
            subject_id=enrolled_subject_ids[0], semester=semester, status="enrolled",
        ).values_list("student_id", flat=True)

        for rank, sg in enumerate(StudentGamification.objects.filter(
            student_id__in=classmate_ids,
        ).select_related("student").order_by("-total_xp")[:5], 1):
            leaderboard.append({
                "rank": rank,
                "name": sg.student.get_full_name() or sg.student.username,
                "initial": (sg.student.first_name or sg.student.username)[0].upper(),
                "xp": sg.total_xp,
                "is_you": sg.student_id == user.pk,
            })

    upcoming = []
    if semester and enrolled_subject_ids:
        for act in Activity.objects.filter(
            subject_id__in=enrolled_subject_ids, end_time__gt=now, status=True,
        ).order_by("end_time")[:5]:
            # act.end_time is a DateTimeField — surface the time separately for the template.
            upcoming.append({
                "date": act.end_time.date(),
                "time": act.end_time,
                "title": act.activity_name,
            })

    for ev in Event.objects.filter(start_date__gte=now.date()).order_by("start_date")[:3]:
        # ev.start_date is a DateField — no time component to display.
        upcoming.append({"date": ev.start_date, "time": None, "title": ev.title})
    upcoming.sort(key=lambda x: x["date"])
    upcoming = upcoming[:5]

    # Recent recognitions from teachers
    recent_recognitions = TeacherRecognition.objects.filter(
        student=user,
    ).select_related("teacher").order_by("-created_at")[:3]

    # Teachers to rate this semester
    teachers_to_rate = []
    if semester and enrolled_subject_ids:
        teacher_ids_seen = set()
        for subj in Subject.objects.filter(pk__in=enrolled_subject_ids):
            if subj.assign_teacher_id and subj.assign_teacher_id not in teacher_ids_seen:
                teacher_ids_seen.add(subj.assign_teacher_id)
                existing_rating = TeacherRating.objects.filter(
                    teacher_id=subj.assign_teacher_id, student=user, semester=semester,
                ).first()
                teacher_user = subj.assign_teacher
                if teacher_user:
                    teachers_to_rate.append({
                        "id": teacher_user.pk,
                        "name": teacher_user.get_full_name() or teacher_user.username,
                        "current_stars": existing_rating.stars if existing_rating else 0,
                    })

    return render(request, "student/gamification/student_dashboard.html", {
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
        "almost_there": almost_there,
        "leaderboard": leaderboard,
        "upcoming": upcoming,
        "recent_recognitions": recent_recognitions,
        "teachers_to_rate": teachers_to_rate,
        "schedule_today": schedule_today,
        "due_this_week_count": due_this_week_count,
        "now_dt": now,
    })


@login_required
def leaderboard(request):
    user = request.user
    now = timezone.localtime(timezone.now())
    semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    role_name = ""
    try:
        if hasattr(user, "profile") and user.profile.role:
            role_name = user.role_name
    except Exception:
        pass
    is_teacher = role_name in ("teacher", "admin")

    rows = []
    if semester:
        if is_teacher:
            # Teacher view: rank all students enrolled in any subject this teacher teaches
            from subject.models.subject_model import Subject
            from django.db.models import Q
            teacher_subjects = Subject.objects.filter(
                Q(assign_teacher=user) | Q(substitute_teacher=user) | Q(collaborators=user),
            ).distinct()
            classmate_ids = list(
                SubjectEnrollment.objects.filter(
                    subject__in=teacher_subjects, semester=semester, status="enrolled",
                ).values_list("student_id", flat=True).distinct()
            )
        else:
            my_subject_ids = SubjectEnrollment.objects.filter(
                student=user, semester=semester, status="enrolled",
            ).values_list("subject_id", flat=True)[:1]

            classmate_ids = list(
                SubjectEnrollment.objects.filter(
                    subject_id__in=my_subject_ids, semester=semester, status="enrolled",
                ).values_list("student_id", flat=True)
            ) if my_subject_ids else []

        for rank, sg in enumerate(StudentGamification.objects.filter(
            student_id__in=classmate_ids,
        ).select_related("student").order_by("-total_xp"), 1):
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

    return render(request, "student/gamification/leaderboard.html", {"rows": rows})


@login_required
def badge_collection(request):
    user = request.user
    tier_order = {"platinum": 0, "gold": 1, "silver": 2, "bronze": 3, "hidden": 4, "seasonal": 5}

    all_badges = list(BadgeDefinition.objects.filter(is_active=True))

    earned_map = {}
    for sb in StudentBadge.objects.filter(student=user).select_related("badge"):
        earned_map[sb.badge_id] = sb

    # Group tiered (family) badges: show only the highest earned tier plus the
    # next-tier target so a family appears as a single upgrading slot.
    visible_defs = []
    families = {}
    for bd in all_badges:
        if not bd.family:
            visible_defs.append(bd)
            continue
        families.setdefault(bd.family, []).append(bd)

    for family_rows in families.values():
        family_rows.sort(key=lambda b: b.family_rank)
        earned_tiers = [bd for bd in family_rows if bd.pk in earned_map]
        unearned_tiers = [bd for bd in family_rows if bd.pk not in earned_map]
        if unearned_tiers:
            visible_defs.append(unearned_tiers[0])
        elif earned_tiers:
            visible_defs.append(earned_tiers[-1])

    visible_defs.sort(key=lambda b: (tier_order.get(b.tier, 6), b.name))

    badges = []
    for bd in visible_defs:
        sb = earned_map.get(bd.pk)
        progress = 0
        if not sb:
            progress = compute_badge_progress(user, bd)
        badges.append({
            "definition": bd,
            "earned": sb is not None,
            "earned_at": sb.earned_at if sb else None,
            "share_token": sb.share_token if sb else None,
            "progress": progress,
        })

    return render(request, "student/gamification/badge_collection.html", {
        "badges": badges,
        "earned_count": len(earned_map),
        "total_count": len(visible_defs),
    })


def shared_badge_view(request, token):
    sb = get_object_or_404(
        StudentBadge.objects.select_related("badge", "student", "student__profile"),
        share_token=token,
    )
    student = sb.student
    profile = getattr(student, "profile", None)
    if profile and (profile.first_name or profile.last_name):
        display_name = f"{profile.first_name or ''} {profile.last_name or ''}".strip()
    else:
        display_name = student.get_full_name() or student.username

    photo = getattr(profile, "student_photo", None) if profile else None
    avatar_url = photo.url if photo else ""
    if avatar_url:
        avatar_url = request.build_absolute_uri(avatar_url)

    share_url = request.build_absolute_uri()

    return render(request, "gamification/shared_badge.html", {
        "student_badge": sb,
        "badge": sb.badge,
        "display_name": display_name,
        "avatar_url": avatar_url,
        "earned_at": sb.earned_at,
        "share_url": share_url,
    })


@login_required
def student_calendar(request):
    user = request.user
    today = date.today()

    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
    except (ValueError, TypeError):
        year, month = today.year, today.month

    cal = cal_module.Calendar(firstweekday=6)  # Sunday first
    month_days = cal.monthdayscalendar(year, month)

    first_of_month = date(year, month, 1)
    if month == 12:
        last_of_month = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_of_month = date(year, month + 1, 1) - timedelta(days=1)

    holidays = Holiday.objects.filter(date__gte=first_of_month, date__lte=last_of_month)
    events = Event.objects.filter(start_date__gte=first_of_month, start_date__lte=last_of_month)
    announcements = Announcement.objects.filter(date__gte=first_of_month, date__lte=last_of_month)

    now = timezone.localtime(timezone.now())
    semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()
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

    day_data = {}
    for h in holidays:
        day_data.setdefault(h.date.day, []).append({"type": "holiday", "title": h.title})
    for e in events:
        day_data.setdefault(e.start_date.day, []).append({"type": "event", "title": e.title})
    for a in announcements:
        day_data.setdefault(a.date.day, []).append({"type": "announcement", "title": a.title})
    for d in deadlines:
        day_data.setdefault(d.end_time.day, []).append({"type": "deadline", "title": d.activity_name})

    # Build weeks structure with embedded events for template access
    weeks = []
    for week in month_days:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append({"day": 0, "events": []})
            else:
                week_data.append({"day": day, "events": day_data.get(day, [])})
        weeks.append(week_data)

    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    month_name = date(year, month, 1).strftime("%B %Y")

    return render(request, "student/gamification/student_calendar.html", {
        "weeks": weeks,
        "today": today,
        "year": year,
        "month": month,
        "month_name": month_name,
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
    })


@login_required
def quest_map_picker(request):
    user = request.user
    now = timezone.localtime(timezone.now())
    semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

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
                "remaining": max(0, total_modules - completed),
                "pct": pct,
            })

    total_modules_all = sum(s["total"] for s in subjects)
    total_completed_all = sum(s["completed"] for s in subjects)
    overall_pct = int((total_completed_all / total_modules_all) * 100) if total_modules_all else 0
    fully_done = sum(1 for s in subjects if s["total"] > 0 and s["completed"] >= s["total"])

    return render(request, "student/gamification/quest_map_picker.html", {
        "subjects": subjects,
        "total_modules_all": total_modules_all,
        "total_completed_all": total_completed_all,
        "overall_pct": overall_pct,
        "fully_done": fully_done,
    })


@login_required
def quest_map(request, subject_id):
    user = request.user
    subject = get_object_or_404(Subject, pk=subject_id)

    # Verify student is enrolled
    now = timezone.localtime(timezone.now())
    semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()
    if semester:
        enrolled = SubjectEnrollment.objects.filter(
            student=user, subject=subject, semester=semester, status="enrolled",
        ).exists()
        if not enrolled:
            return redirect("quest_map_picker")

    modules_qs = Module.objects.filter(subject=subject).order_by("order", "pk")

    nodes = []
    current_module = None
    current_found = False
    completed_count = 0
    for mod in modules_qs:
        is_completed = _module_done_by_quests(user, mod)
        if is_completed:
            state = "done"
            completed_count += 1
        elif not current_found:
            state = "active"
            current_found = True
            current_module = mod
        else:
            state = "locked"
        nodes.append({"id": mod.pk, "name": mod.file_name, "state": state})

    # Quest-level score for badge display
    term = next((m.term for m in modules_qs if getattr(m, "term", None)), None)
    quest_level_pct = get_student_quest_score(user, subject, term) if term else None

    continue_url = None
    if current_module:
        continue_url = reverse('view-material', args=[current_module.pk])
    elif subject:
        continue_url = reverse('material-list', args=[subject.id])

    # SVG node positions — winding "Duolingo-style" path with sine wave.
    import math
    svg_nodes = []
    total = len(nodes)
    canvas_w = 1200
    canvas_h = 420
    margin_x = 90
    amplitude = 130
    for i, node in enumerate(nodes):
        if total > 1:
            t = i / (total - 1)
            x = margin_x + t * (canvas_w - 2 * margin_x)
        else:
            x = canvas_w / 2
        y = canvas_h / 2 + amplitude * math.sin(i * 0.9)
        svg_nodes.append({**node, "x": round(x), "y": round(y), "idx": i + 1})

    locked_count = sum(1 for n in nodes if n["state"] == "locked")
    active_count = sum(1 for n in nodes if n["state"] == "active")
    total_count = len(nodes)
    pct = int((completed_count / total_count) * 100) if total_count else 0

    return render(request, "student/gamification/quest_map.html", {
        "subject": subject,
        "nodes": svg_nodes,
        "completed_count": completed_count,
        "total_count": total_count,
        "locked_count": locked_count,
        "active_count": active_count,
        "current_module": current_module,
        "progress_pct": pct,
        "continue_url": continue_url,
        "canvas_w": canvas_w,
        "canvas_h": canvas_h,
        "quest_level_pct": quest_level_pct,
    })


_BADGE_TIER_MAP = {
    "BRONZE": "warning",
    "SILVER": "muted",
    "GOLD": "success",
    "PLATINUM": "info",
}
_BADGE_STATUS_MAP = {"Active": "success", "Inactive": "muted"}
_BADGE_CATEGORY_MAP = {
    "Coding": "info",
    "Side Activity": "warning",
    "General": "muted",
}


def _badge_category(badge):
    ctype = (badge.criteria_json or {}).get("type", "")
    if ctype.startswith("coding_"):
        return "Coding"
    if ctype.startswith("side_activity"):
        return "Side Activity"
    return "General"


@login_required
def badge_list(request):
    """[Classedge LMS] Teacher-facing badge index with search + category filter
    + pagination, served from the reusable list-table shell."""
    from accounts.utils import get_pagination_context, paginate_queryset, search_queryset

    search_query = request.GET.get("search", "").strip()
    category_filter = request.GET.get("category", "").strip()
    status_filter = request.GET.get("status", "").strip()

    badges_qs = BadgeDefinition.objects.annotate(
        earned_count=Count("studentbadge"),
    ).order_by("tier", "name")
    badges_qs = search_queryset(badges_qs, search_query, ["name", "description"])
    if status_filter == "active":
        badges_qs = badges_qs.filter(is_active=True)
    elif status_filter == "inactive":
        badges_qs = badges_qs.filter(is_active=False)

    # Category is computed in Python from criteria_json — filter post-fetch.
    rows = []
    for b in badges_qs:
        cat = _badge_category(b)
        if category_filter and cat.lower() != category_filter.lower():
            continue
        rows.append({
            "id": b.pk,
            "icon": b.icon,
            "name": b.name,
            "description": b.description or "",
            "category": cat,
            "tier": (b.tier or "").upper(),
            "earned_count": b.earned_count,
            "is_active": b.is_active,
            "status_label": "Active" if b.is_active else "Inactive",
            "toggle_label": "Deactivate" if b.is_active else "Activate",
            "is_manual": not (b.criteria_json or {}).get("type"),
        })

    page_obj, _ = paginate_queryset(rows, request, items_per_page=10)

    context = {
        "search_query": search_query,
        "category_filter": category_filter,
        "status_filter": status_filter,
        "title": "Badge Library",
        "icon": "fa-award",
        "search_placeholder": "Search by name or description...",
        "empty_icon": "fa-award",
        "empty_label": "badges",
        "extra_filters_template": "teacher/gamification/_badge_filters.html",
        "columns": [
            {"label": "Badge", "type": "name",
             "icon_attr": "icon", "name_attr": "name", "desc_attr": "description"},
            {"label": "Category", "type": "status", "attr": "category",
             "map": _BADGE_CATEGORY_MAP, "width": "140px"},
            {"label": "Tier", "type": "status", "attr": "tier",
             "map": _BADGE_TIER_MAP, "width": "110px"},
            {"label": "Earned", "type": "meta", "attr": "earned_count", "width": "90px"},
            {"label": "Status", "type": "status", "attr": "status_label",
             "map": _BADGE_STATUS_MAP, "width": "110px"},
            {"label": "Action", "align": "right", "type": "actions", "items": [
                {"icon": "fa-pen-to-square", "label": "Edit",
                 "url_name": "badge_edit", "url_arg_attr": "id"},
                {"icon": "fa-medal", "label": "Award",
                 "url_name": "badge_manual_award", "url_arg_attr": "id",
                 "show_attr": "is_manual"},
                {"divider": True},
                {"icon": "fa-power-off", "label_attr": "toggle_label",
                 "form_post": True,
                 "url_name": "badge_toggle_active", "url_arg_attr": "id"},
            ]},
        ],
    }
    context.update(get_pagination_context(page_obj, request))
    if request.GET.get("partial") == "1":
        return render(request, "includes/_list_table.html", context)
    return render(request, "teacher/gamification/badge_management.html", context)


@login_required
@permission_required('gamification.change_badgedefinition', raise_exception=True)
def badge_toggle_active(request, badge_id):
    badge = get_object_or_404(BadgeDefinition, pk=badge_id)
    if request.method == "POST":
        badge.is_active = not badge.is_active
        badge.save(update_fields=["is_active"])
    return redirect("badge_management")


@login_required
def badge_edit(request, badge_id):
    badge = get_object_or_404(BadgeDefinition, pk=badge_id)

    if request.method == "POST":
        badge.name = request.POST.get("name", badge.name)
        badge.description = request.POST.get("description", badge.description)
        badge.icon = request.POST.get("icon", badge.icon)
        badge.tier = request.POST.get("tier", badge.tier)
        badge.save(update_fields=["name", "description", "icon", "tier"])
        return redirect("badge_management")

    return render(request, "teacher/gamification/badge_edit.html", {
        "badge": badge,
        "criteria_display": _json.dumps(badge.criteria_json, indent=2),
        "tier_choices": BadgeDefinition.TIER_CHOICES,
    })


@login_required
@permission_required('gamification.add_studentbadge', raise_exception=True)
def badge_manual_award(request, badge_id):
    badge = get_object_or_404(BadgeDefinition, pk=badge_id)
    from accounts.models import CustomUser

    error = None
    if request.method == "POST":
        student_id = request.POST.get("student")
        reason = request.POST.get("reason", "")
        student = CustomUser.objects.filter(pk=student_id).first()
        if student:
            if StudentBadge.objects.filter(student=student, badge=badge).exists():
                error = "This student already has this badge."
            else:
                StudentBadge.objects.create(
                    student=student, badge=badge,
                    awarded_by=request.user, award_reason=reason,
                )
                return redirect("badge_management")

    students = CustomUser.objects.filter(
        profile__role__name__iexact="student",
    ).order_by("first_name", "last_name")

    return render(request, "teacher/gamification/badge_award.html", {
        "badge": badge,
        "students": students,
        "error": error,
    })


@login_required
@require_POST
def set_featured_badges(request):
    try:
        payload = _json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)

    ids = payload.get('badge_ids')
    if not isinstance(ids, list) or len(ids) != 7:
        return JsonResponse(
            {'error': 'Exactly 7 badges must be selected.'}, status=400
        )

    try:
        ids = [int(x) for x in ids]
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid badge id.'}, status=400)

    owned_count = StudentBadge.objects.filter(
        student=request.user, id__in=ids
    ).count()
    if owned_count != 7:
        return JsonResponse(
            {'error': 'One or more badges are not yours.'}, status=400
        )

    with transaction.atomic():
        StudentBadge.objects.filter(
            student=request.user, is_featured=True
        ).update(is_featured=False)
        StudentBadge.objects.filter(
            student=request.user, id__in=ids
        ).update(is_featured=True)

    return JsonResponse({'featured_ids': ids}, status=200)
