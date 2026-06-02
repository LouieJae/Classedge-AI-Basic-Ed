from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from course.models import Attendance, AttendanceStatus, Semester, SubjectEnrollment
from course.utils.self_attendance import derive_status, find_current_schedule
from subject.models import Subject

ENABLE_LEAD_MINUTES = 15  # how early a teacher may open self-attendance before class start


@login_required
@require_POST
def student_self_mark_attendance(request, subject_id):
    """Student-facing self check-in. Idempotent — re-clicks show a status notice."""
    subject = get_object_or_404(Subject, id=subject_id)

    if not subject.self_attendance_enabled:
        messages.error(request, "Self-attendance is disabled for this subject.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    enrolled = SubjectEnrollment.objects.filter(
        student=request.user, subject=subject, status="enrolled"
    ).exists()
    if not enrolled:
        return HttpResponseForbidden("You are not enrolled in this subject.")

    now = timezone.localtime()
    today = now.date()
    today_abbr = now.strftime("%a")

    schedules = list(subject.schedules.filter(is_active_semester=True))
    schedule = find_current_schedule(schedules, now.time(), today_abbr)
    if schedule is None:
        messages.error(request, "No active class right now. You can only check in during scheduled class time.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    status_name = derive_status(now.time(), schedule.schedule_start_time)
    status_obj = AttendanceStatus.objects.filter(status=status_name).first()
    if status_obj is None:
        messages.error(request, f"Attendance status '{status_name}' is not configured.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    attendance, created = Attendance.objects.get_or_create(
        student=request.user,
        subject=subject,
        date=today,
        defaults={
            "status": status_obj,
            "schedule": schedule,
            "teacher": subject.assign_teacher,
            "marked_at": now,
            "self_marked": True,
            "graded": True,
        },
    )

    if created:
        messages.success(request, f"You are marked {status_name} for {subject.subject_name}.")
    else:
        messages.info(
            request,
            f"You are already marked {attendance.status.status} for {subject.subject_name} today.",
        )

    return redirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@require_POST
def toggle_self_attendance(request, subject_id):
    """Teacher-only toggle that opens/closes self-attendance for a subject."""
    subject = get_object_or_404(Subject, id=subject_id)

    is_primary = subject.assign_teacher_id == request.user.id
    is_substitute = (
        subject.allow_substitute_teacher
        and subject.substitute_teacher_id == request.user.id
    )
    if not (is_primary or is_substitute):
        return HttpResponseForbidden("Only the subject's teacher can change this setting.")

    now = timezone.localtime()
    today = now.date()
    today_abbr = now.strftime("%a")
    in_semester = Semester.objects.filter(
        schedules__subject=subject,
        start_date__lte=today,
        end_date__gte=today,
        end_semester=False,
    ).exists()
    if not in_semester:
        messages.error(
            request,
            "Self-attendance can only be toggled during the subject's active semester.",
        )
        return redirect(request.META.get("HTTP_REFERER", "/"))

    # When ENABLING: only allow inside the schedule window
    # ([start - 15 min, end]) on a day the class actually meets.
    # Disabling is always allowed so a teacher can close attendance early.
    will_enable = not subject.self_attendance_enabled
    if will_enable:
        window_open = False
        for sched in subject.schedules.filter(is_active_semester=True):
            if today_abbr not in sched.days_of_week:
                continue
            start_dt = datetime.combine(today, sched.schedule_start_time)
            end_dt = datetime.combine(today, sched.schedule_end_time)
            open_at = start_dt - timedelta(minutes=ENABLE_LEAD_MINUTES)
            now_naive = now.replace(tzinfo=None)
            if open_at <= now_naive <= end_dt:
                window_open = True
                break
        if not window_open:
            messages.error(
                request,
                f"You can open self-attendance only within {ENABLE_LEAD_MINUTES} "
                f"minutes before class starts and until class ends.",
            )
            return redirect(request.META.get("HTTP_REFERER", "/"))

    subject.self_attendance_enabled = will_enable
    subject.save(update_fields=["self_attendance_enabled"])
    state = "enabled" if subject.self_attendance_enabled else "disabled"
    messages.success(request, f"Self-attendance {state} for {subject.subject_name}.")
    return redirect(request.META.get("HTTP_REFERER", "/"))
