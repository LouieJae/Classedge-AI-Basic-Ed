from datetime import datetime, date, time, timedelta

LATE_THRESHOLD_MINUTES = 15
EARLY_GRACE_MINUTES = 5


def _combine(d: date, t: time) -> datetime:
    return datetime.combine(d, t)


def derive_status(now_time: time, schedule_start: time) -> str:
    """Return 'Present' if now < start + 15min, else 'Late'."""
    today = date(2000, 1, 1)
    delta = _combine(today, now_time) - _combine(today, schedule_start)
    if delta < timedelta(minutes=LATE_THRESHOLD_MINUTES):
        return "Present"
    return "Late"


def is_window_open(now_time: time, schedule_start: time, schedule_end: time) -> bool:
    """True if now_time is within [start - 5min, end]."""
    today = date(2000, 1, 1)
    now_dt = _combine(today, now_time)
    open_dt = _combine(today, schedule_start) - timedelta(minutes=EARLY_GRACE_MINUTES)
    close_dt = _combine(today, schedule_end)
    return open_dt <= now_dt <= close_dt


def find_current_schedule(schedules, now_time: time, today_abbr: str):
    """Return the first schedule that's active today and whose check-in window is open."""
    for s in schedules:
        if not s.is_active_semester:
            continue
        if today_abbr not in s.days_of_week:
            continue
        if is_window_open(now_time, s.schedule_start_time, s.schedule_end_time):
            return s
    return None
