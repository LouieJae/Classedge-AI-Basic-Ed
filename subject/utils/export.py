import csv
from django.http import HttpResponse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from subject.models import Subject, Schedule
from subject.utils.days import ORDER 

def _h12_and_ampm(t):
    """Return ('H:MM', 'AM'|'PM') from a datetime.time object."""
    h = t.hour % 12 or 12
    return (f"{h}:{t.minute:02d}", "AM" if t.hour < 12 else "PM")


def _join_days(days):
    """Join days in canonical ORDER using ', ' so parse_days() can read it."""
    days = list(days or [])
    days_sorted = sorted(days, key=lambda d: ORDER.index(d)) if all(d in ORDER for d in days) else days
    return ", ".join(days_sorted)


@login_required
def export_subjects_and_schedules(request):
    """
    Export subjects+schedules in the exact CSV shape your import expects.
    One row per Schedule.
    """
    ts = timezone.now().strftime("%Y%m%d-%H%M%S")
    filename = f"subjects_schedules_{ts}.csv"

    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    resp.write("\ufeff")  # BOM for Excel

    writer = csv.writer(resp)
    writer.writerow([
        "Subject Name",
        "Subject Code",
        "Subject Short Name",
        "Subject Description",
        "Room Number",
        "Teacher Name",
        "Schedule Type",
        "Day",
        "Start Time",
        "AM/PM",
        "End Time",
        "End AM/PM",
    ])

    # Prefetch schedules; we use assign_teacher (primary) to match your import behavior
    subjects = (
        Subject.objects
        .select_related("assign_teacher")
        .prefetch_related(Prefetch("schedules", queryset=Schedule.objects.all()))
        .order_by("subject_code", "subject_name")
    )

    for subj in subjects:
        teacher = subj.assign_teacher
        teacher_name = ((teacher.get_full_name() or "").strip()
                        if teacher else "")
        if not teacher_name and teacher:
            # fallback if first/last name empty
            teacher_name = (teacher.first_name or "").strip()
            if teacher.last_name:
                teacher_name = (teacher_name + " " + teacher.last_name).strip()
            if not teacher_name:
                teacher_name = teacher.username or teacher.email or ""

        schedules = list(subj.schedules.all())

        # If a subject has no schedules yet, export a placeholder row (optional).
        # Comment this block if you only want rows with schedules.
        if not schedules:
            writer.writerow([
                subj.subject_name or "",
                subj.subject_code or "",
                subj.subject_short_name or "",
                subj.subject_description or "",
                subj.room_number or "",
                teacher_name,
                "",              # Schedule Type
                "",              # Day
                "",              # Start Time
                "",              # AM/PM
                "",              # End Time
                "",              # End AM/PM
            ])
            continue

        for sched in schedules:
            start_t, start_ampm = _h12_and_ampm(sched.schedule_start_time)
            end_t, end_ampm     = _h12_and_ampm(sched.schedule_end_time)
            days_str = _join_days(sched.days_of_week)

            writer.writerow([
                subj.subject_name or "",
                subj.subject_code or "",
                subj.subject_short_name or "",
                subj.subject_description or "",
                subj.room_number or "",
                teacher_name,
                sched.schedule_type or "",
                days_str,
                start_t,
                start_ampm,
                end_t,
                end_ampm,  # we explicitly provide End AM/PM so import doesn't need to fall back
            ])

    return resp
