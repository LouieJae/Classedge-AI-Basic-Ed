"""[Classedge LMS] Coil Admin Operations dashboard view."""
from collections import Counter
from datetime import timedelta

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count
from django.shortcuts import render
from django.utils import timezone

from accounts.utils.dashboard_helpers import time_of_day

from coil.models import CoilPartnerSchool
from course.models.semester_model import Semester
from course.models.subject_enrollment_model import SubjectEnrollment
from subject.models.subject_model import Subject


STATUS_ORDER = ["Pending Acceptance", "Send Invite", "Partner", "Rejected"]
STALE_PENDING_DAYS = 30


def _is_coil_admin(user):
    """[Classedge LMS] True iff the authenticated user owns the Coil Admin role."""
    return (
        user.is_authenticated
        and hasattr(user, "profile")
        and user.profile.role
        and user.profile.role.name == "Coil Admin"
    )




def _kpis(by_status, total_students):
    """[Classedge LMS] Four numbers a COIL admin checks daily — drop 'Rejected'
    (a closed terminal state; still visible in the pipeline funnel)."""
    pending = by_status.get("Pending Acceptance", 0)
    invites = by_status.get("Send Invite", 0)
    partners = by_status.get("Partner", 0)
    return [
        {"label": "Active partners", "value": partners, "icon": "fa-handshake",
         "tone": "ok" if partners else "", "hint": "Confirmed COIL partner schools"},
        {"label": "Students", "value": total_students, "icon": "fa-user-graduate",
         "tone": "", "hint": "Across all partner schools"},
        {"label": "Pending acceptance", "value": pending, "icon": "fa-hourglass-half",
         "tone": "warn" if pending else "", "hint": "Awaiting partner reply"},
        {"label": "Invites to send", "value": invites, "icon": "fa-paper-plane",
         "tone": "warn" if invites else "", "hint": "Drafted, not yet sent"},
    ]


def _partner_rows(qs_all):
    """[Classedge LMS] Sort schools so pending-first, then send-invite, then partner, then rejected."""
    rows = []
    for s in sorted(
        qs_all,
        key=lambda x: (STATUS_ORDER.index(x.status) if x.status in STATUS_ORDER else len(STATUS_ORDER), -x.id),
    ):
        rows.append({
            "id": s.id,
            "name": s.school_name,
            "domain": s.school_domain,
            "status": s.status,
            "students_self_reported": s.student_participating,
            "students_resolved": s.student_count(),
            "location": s.location or "",
            "contact": s.contact_person or "",
            "contact_email": s.school_email or "",
            "contact_phone": s.contact_number or "",
            "registered": s.date_registered,
        })
    return rows


def _funnel_rows(by_status, total):
    """[Classedge LMS] Stage counts + percent of pipeline for the funnel panel."""
    stages = ["Send Invite", "Pending Acceptance", "Partner", "Rejected"]
    rows = []
    for label in stages:
        n = by_status.get(label, 0)
        rows.append({
            "label": label,
            "count": n,
            "pct": round(n / total * 100) if total else 0,
        })
    return rows


@login_required
@user_passes_test(_is_coil_admin)
def coil_admin_dashboard(request):
    """[Classedge LMS] Render the Coil Admin Operations dashboard."""
    qs_all = CoilPartnerSchool.objects.all()
    by_status = Counter(qs_all.values_list("status", flat=True))
    total_partners = qs_all.count()
    total_students = sum(s.student_participating for s in qs_all)

    # ── "Needs your attention" highlight ─────────────────────────
    # The COIL admin's job-to-be-done is "move schools from invite →
    # pending → partner". Surface the specific items waiting on them.
    now = timezone.localtime()
    stale_cutoff = now - timedelta(days=STALE_PENDING_DAYS)
    pending_count = by_status.get("Pending Acceptance", 0)
    invites_count = by_status.get("Send Invite", 0)
    stale_pending_count = qs_all.filter(
        status="Pending Acceptance", date_registered__lt=stale_cutoff,
    ).count()

    attention_items = []
    if invites_count:
        attention_items.append({
            "label": f"{invites_count} draft invite{'s' if invites_count != 1 else ''} to send",
            "detail": "Push them out so the pipeline can move.",
            "icon": "fa-paper-plane",
        })
    if stale_pending_count:
        attention_items.append({
            "label": f"{stale_pending_count} pending acceptance{'s' if stale_pending_count != 1 else ''} aging ({STALE_PENDING_DAYS}d+)",
            "detail": "Send a follow-up — they've gone quiet.",
            "icon": "fa-hourglass-half",
        })
    if pending_count and not stale_pending_count:
        attention_items.append({
            "label": f"{pending_count} school{'s' if pending_count != 1 else ''} awaiting reply",
            "detail": "Keep an eye on these — nudge after a week of silence.",
            "icon": "fa-clock",
        })
    attention_status = "warn" if (invites_count or stale_pending_count) else "ok"

    # ── Stale-pending list (so the admin can click straight to follow-up) ──
    stale_pending_list = list(
        qs_all.filter(status="Pending Acceptance", date_registered__lt=stale_cutoff)
        .order_by("date_registered")[:5]
    )
    stale_pending_rows = []
    for s in stale_pending_list:
        age = (now.date() - s.date_registered.date()).days
        stale_pending_rows.append({
            "id": s.id,
            "name": s.school_name,
            "domain": s.school_domain,
            "location": s.location or "",
            "contact": s.contact_person or "",
            "age_days": age,
        })

    # ── Partners by location (geographic spread) ─────────────────
    location_counts = Counter(
        (s.location or "Unspecified").strip() or "Unspecified"
        for s in qs_all if s.status == "Partner"
    )
    location_rows = []
    location_total = sum(location_counts.values()) or 1
    for loc, n in location_counts.most_common(6):
        location_rows.append({
            "label": loc,
            "count": n,
            "pct": round(n / location_total * 100),
        })

    # ── COIL-flagged subjects (which courses run cross-border collabs) ──
    # Enrollee counts come live from SubjectEnrollment (current semester
    # when one is active) instead of the cached Subject.number_of_enrollees.
    today_date = timezone.localdate()
    current_semester = Semester.objects.filter(
        start_date__lte=today_date, end_date__gte=today_date,
    ).first()
    coil_subject_qs = (
        Subject.objects
        .filter(is_coil=True)
        .select_related("assign_teacher")
    )
    coil_enroll_qs = SubjectEnrollment.objects.filter(
        subject__in=coil_subject_qs, status="enrolled",
    )
    if current_semester:
        coil_enroll_qs = coil_enroll_qs.filter(semester=current_semester)
    coil_live_counts = {
        row["subject_id"]: row["c"]
        for row in coil_enroll_qs.values("subject_id").annotate(c=Count("id"))
    }
    coil_subject_rows = []
    for s in coil_subject_qs:
        teacher = s.assign_teacher
        teacher_name = ""
        if teacher:
            teacher_name = f"{teacher.first_name or ''} {teacher.last_name or ''}".strip() or teacher.username
        coil_subject_rows.append({
            "id": s.id,
            "name": s.subject_name,
            "code": s.subject_code or "",
            "teacher": teacher_name or "Unassigned",
            "enrollees": coil_live_counts.get(s.id, 0),
            "status": s.status or "Available",
        })
    coil_subject_rows.sort(key=lambda r: (-r["enrollees"], r["name"] or ""))
    coil_subject_rows = coil_subject_rows[:6]
    coil_subject_total = Subject.objects.filter(is_coil=True).count()

    context = {
        "role_tag": "Coil Admin",
        "time_of_day": time_of_day(),
        "as_of": now.strftime("%b %d · %I:%M %p"),
        "kpis": _kpis(by_status, total_students),
        "partner_rows": _partner_rows(qs_all),
        "funnel_rows": _funnel_rows(by_status, total_partners),
        "totals": {
            "partners": total_partners,
            "students": total_students,
            "pending": pending_count,
            "invites": invites_count,
        },
        "attention_items": attention_items,
        "attention_status": attention_status,
        "stale_pending_count": stale_pending_count,
        "stale_pending_rows": stale_pending_rows,
        "location_rows": location_rows,
        "coil_subject_rows": coil_subject_rows,
        "coil_subject_total": coil_subject_total,
    }
    return render(request, "operations/coil_admin_dashboard.html", context)
