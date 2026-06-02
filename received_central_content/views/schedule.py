from collections import Counter
from datetime import timedelta

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from received_central_content.auth import require_central_token
from subject.models.subject_model import Subject
from subject.models.schedule_model import Schedule
from course.models.term_model import Term


@require_GET
@require_central_token
def subject_schedule(request, subject_id):
    try:
        subject = Subject.objects.get(pk=subject_id)
    except Subject.DoesNotExist:
        return JsonResponse({"error": "subject_not_found"}, status=404)

    schedule = (
        Schedule.objects
        .filter(subject=subject, is_active_semester=True)
        .select_related("semester")
        .first()
    )

    if not schedule:
        return JsonResponse({"error": "no_active_schedule"}, status=400)

    term = (
        Term.objects
        .filter(semester=schedule.semester)
        .order_by("start_date")
        .first()
    )

    if not term or not term.start_date or not term.end_date:
        return JsonResponse({"error": "no_term_assigned"}, status=400)

    day_map = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
    schedule_days = [day_map[d] for d in schedule.days_of_week if d in day_map]

    sessions = []
    current = term.start_date
    while current <= term.end_date:
        if current.weekday() in schedule_days:
            start_t = schedule.schedule_start_time
            end_t = schedule.schedule_end_time
            start_minutes = start_t.hour * 60 + start_t.minute
            end_minutes = end_t.hour * 60 + end_t.minute
            duration = end_minutes - start_minutes
            sessions.append({
                "date": current.isoformat(),
                "start_time": start_t.strftime("%H:%M"),
                "end_time": end_t.strftime("%H:%M"),
                "minutes": duration,
            })
        current += timedelta(days=1)

    durations = [s["minutes"] for s in sessions]
    mode_minutes = Counter(durations).most_common(1)[0][0] if durations else 0

    return JsonResponse({
        "subject_id": subject.pk,
        "subject_name": subject.subject_name,
        "term": {
            "name": term.term_name,
            "start_date": term.start_date.isoformat(),
            "end_date": term.end_date.isoformat(),
        },
        "sessions": sessions,
        "session_count": len(sessions),
        "minutes_per_session": mode_minutes,
    })
