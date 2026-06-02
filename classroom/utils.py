from datetime import datetime, timedelta
from django.utils.timezone import localtime
from .models import Teacher_Attendance


def format_duration(duration):
    """Format a timedelta as 'HH:MM' string."""
    total_seconds = duration.total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    return f"{hours:02d}:{minutes:02d}"


def format_time(time_obj):
    """Format a time object as '1:30 PM' (12-hour, no leading zero)."""
    if time_obj:
        formatted_time = time_obj.strftime('%I:%M %p')
        if formatted_time.startswith('0'):
            formatted_time = formatted_time[1:]
        return formatted_time
    return "-"


def duration_to_minutes(duration_str):
    """Convert 'HH:MM' duration string to total minutes."""
    if duration_str == "-" or not duration_str:
        return 0
    try:
        hours, minutes = map(int, duration_str.split(':'))
        return hours * 60 + minutes
    except (ValueError, IndexError):
        return 0


def get_matching_dates(schedule_days, start_date, end_date):
    """Return dates within [start_date, end_date] that match schedule's days_of_week."""
    days_map = {
        "Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6
    }
    if not start_date or not end_date:
        return []

    schedule_day_numbers = [days_map[day] for day in schedule_days if day in days_map]
    matching_dates = []
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() in schedule_day_numbers:
            matching_dates.append(current_date)
        current_date += timedelta(days=1)
    return matching_dates


def _update_time_bound(date_data, field, raw_field, new_time, is_min):
    """
    Update a time bound (earliest start or latest end) if new_time is more extreme.
    Returns True if the value was updated (recalculation needed).
    """
    current_raw = date_data.get(raw_field)
    if current_raw is None:
        date_data[field] = format_time(new_time)
        date_data[raw_field] = new_time
        return True

    should_update = new_time < current_raw if is_min else new_time > current_raw
    if should_update:
        date_data[field] = format_time(new_time)
        date_data[raw_field] = new_time
        return True
    return False


def _process_attendance_record(record, record_date, date_str, date_data, report_data_entry):
    """Process a single attendance record into date_data, updating durations and totals."""
    actual_start_time = localtime(record.time_started).time()
    actual_end_time = localtime(record.time_ended).time()
    effective_start_time = actual_start_time

    # Clamp early starts to scheduled start
    budget_start_raw = date_data.get('_budget_start_time')
    if budget_start_raw and actual_start_time < budget_start_raw:
        effective_start_time = budget_start_raw

    if not date_data['has_attendance']:
        # First attendance record for this date.
        # When the teacher clocked in before the scheduled start, both the
        # display ("Actual Start") and downstream Excel export should show
        # the scheduled start — not the raw early time — so the report
        # reads consistently with how variance is already computed.
        date_data['actual_start'] = format_time(effective_start_time)
        date_data['actual_end'] = format_time(actual_end_time)
        date_data['earliest_start_time'] = effective_start_time
        date_data['latest_end_time'] = actual_end_time
        date_data['earliest_actual_start'] = effective_start_time

        calculated_duration = datetime.combine(record_date, actual_end_time) - datetime.combine(record_date, effective_start_time)
        formatted_dur = format_duration(calculated_duration)

        date_data['actual_duration'] = formatted_dur
        date_data['_raw_duration'] = calculated_duration
        date_data['computed_start'] = format_time(effective_start_time)
        date_data['computed_end'] = format_time(actual_end_time)
        date_data['computed_duration'] = formatted_dur
        date_data['has_attendance'] = True

        report_data_entry['total_attendance_time'] += calculated_duration
    else:
        # Subsequent records: track extremes and recalculate if window expanded
        start_changed = _update_time_bound(date_data, 'computed_start', 'earliest_start_time', effective_start_time, is_min=True)
        end_changed = _update_time_bound(date_data, 'computed_end', 'latest_end_time', actual_end_time, is_min=False)

        # Track earliest start for display, using the clamped value so
        # an early clock-in never appears as "before the scheduled start".
        current_earliest = date_data.get('earliest_actual_start')
        if current_earliest is None or effective_start_time < current_earliest:
            date_data['earliest_actual_start'] = effective_start_time
        date_data['actual_start'] = format_time(date_data['earliest_actual_start'])
        date_data['actual_end'] = date_data['computed_end']

        if (start_changed or end_changed) and date_data['earliest_start_time'] and date_data['latest_end_time']:
            # Subtract previous duration from total
            previous_duration = date_data.get('_raw_duration', timedelta(0))
            report_data_entry['total_attendance_time'] -= previous_duration

            calculated_duration = datetime.combine(record_date, date_data['latest_end_time']) - datetime.combine(record_date, date_data['earliest_start_time'])
            formatted_dur = format_duration(calculated_duration)

            date_data['actual_duration'] = formatted_dur
            date_data['_raw_duration'] = calculated_duration
            date_data['computed_duration'] = formatted_dur

            report_data_entry['total_attendance_time'] += calculated_duration


def build_attendance_report_data(schedule_data, start_date, end_date, teacher_id=None):
    """
    Process schedule and attendance records into a unified report structure.

    Returns:
        tuple: (final_report_data list, all_dates_list sorted list)
    """
    report_data = {}
    all_dates = set()

    # Process schedule data first
    for schedule in schedule_data:
        teacher_key = schedule.subject.assign_teacher.id
        subject_id = schedule.subject.id
        teacher_name = f"{schedule.subject.assign_teacher.first_name} {schedule.subject.assign_teacher.last_name}"
        subject_name = schedule.subject.subject_name

        key = (teacher_key, subject_id)

        if key not in report_data:
            report_data[key] = {
                'teacher_name': teacher_name,
                'subject_name': subject_name,
                'teacher_id': teacher_key,
                'subject_id': subject_id,
                'dates': {},
                'total_scheduled_time': timedelta(0),
                'total_attendance_time': timedelta(0)
            }

        schedule_days = schedule.days_of_week
        matching_dates = get_matching_dates(schedule_days, start_date, end_date)
        all_dates.update(matching_dates)

        for match_date in matching_dates:
            schedule_start = datetime.combine(match_date, schedule.schedule_start_time)
            schedule_end = datetime.combine(match_date, schedule.schedule_end_time)
            scheduled_duration = schedule_end - schedule_start

            date_str = match_date.strftime("%Y-%m-%d")

            if date_str not in report_data[key]['dates']:
                report_data[key]['dates'][date_str] = _make_date_entry(
                    match_date,
                    budget_start=format_time(schedule.schedule_start_time),
                    budget_end=format_time(schedule.schedule_end_time),
                    budget_duration=format_duration(scheduled_duration),
                    budget_start_time=schedule.schedule_start_time,
                    budget_duration_td=scheduled_duration,
                )

            report_data[key]['total_scheduled_time'] += scheduled_duration

    # Process attendance records
    attendance_records = Teacher_Attendance.objects.filter(
        time_started__date__gte=start_date,
        time_started__date__lte=end_date,
        time_ended__isnull=False
    )

    if teacher_id:
        try:
            attendance_records = attendance_records.filter(teacher_id=int(teacher_id))
        except (ValueError, TypeError):
            pass

    for record in attendance_records:
        teacher_key = record.teacher.id
        subject_id = record.subject.id
        record_date = localtime(record.time_started).date()
        date_str = record_date.strftime("%Y-%m-%d")

        key = (teacher_key, subject_id)

        if key not in report_data:
            teacher_name = f"{record.teacher.first_name} {record.teacher.last_name}"
            subject_name = record.subject.subject_name
            report_data[key] = {
                'teacher_name': teacher_name,
                'subject_name': subject_name,
                'teacher_id': teacher_key,
                'subject_id': subject_id,
                'dates': {},
                'total_scheduled_time': timedelta(0),
                'total_attendance_time': timedelta(0)
            }

        if date_str not in report_data[key]['dates']:
            all_dates.add(record_date)
            report_data[key]['dates'][date_str] = _make_date_entry(record_date)

        _process_attendance_record(record, record_date, date_str, report_data[key]['dates'][date_str], report_data[key])

    # Filter out subjects with no scheduled classes in the date range
    report_data = {key: data for key, data in report_data.items() if data['total_scheduled_time'] > timedelta(0)}

    # Convert to list and calculate variances
    final_report_data = []

    for key, data in report_data.items():
        total_scheduled = format_duration(data['total_scheduled_time'])
        total_attendance = format_duration(data['total_attendance_time'])

        variance_time = data['total_scheduled_time'] - data['total_attendance_time']
        variance = format_duration(abs(variance_time))
        variance_negative = variance_time.total_seconds() < 0

        date_entries = []
        for date_str_key, date_data in sorted(data['dates'].items()):
            daily_variance = None
            daily_variance_negative = False

            raw_dur = date_data.get('_raw_duration')
            raw_budget = date_data.get('_budget_duration')
            if raw_dur and raw_budget:
                vt = raw_budget - raw_dur
                daily_variance = format_duration(abs(vt))
                daily_variance_negative = vt.total_seconds() < 0

            date_entries.append({
                'date': date_data['date'],
                'date_str': date_str_key,
                'budget_start': date_data['budget_start'],
                'budget_end': date_data['budget_end'],
                'budget_duration': date_data['budget_duration'],
                'actual_start': date_data['actual_start'],
                'actual_end': date_data['actual_end'],
                'actual_duration': date_data['actual_duration'],
                'computed_start': date_data['computed_start'],
                'computed_end': date_data['computed_end'],
                'computed_duration': date_data['computed_duration'],
                'has_attendance': date_data['has_attendance'],
                'daily_variance': daily_variance,
                'daily_variance_negative': daily_variance_negative
            })

        final_report_data.append({
            'teacher_id': data['teacher_id'],
            'subject_id': data['subject_id'],
            'teacher_name': data['teacher_name'],
            'subject_name': data['subject_name'],
            'date_entries': date_entries,
            'total_scheduled_time': total_scheduled,
            'total_attendance_time': total_attendance,
            'variance': variance,
            'variance_negative': variance_negative
        })

    final_report_data.sort(key=lambda x: (x['teacher_name'], x['subject_name']))
    all_dates_list = sorted(list(all_dates))

    return final_report_data, all_dates_list


def _make_date_entry(date_obj, budget_start="-", budget_end="-", budget_duration="-", budget_start_time=None, budget_duration_td=None):
    """Create a date_data dict with defaults."""
    return {
        'date': date_obj,
        'budget_start': budget_start,
        'budget_end': budget_end,
        'budget_duration': budget_duration,
        '_budget_start_time': budget_start_time,
        '_budget_duration': budget_duration_td,
        'actual_start': "-",
        'actual_end': "-",
        'actual_duration': "-",
        'computed_start': "-",
        'computed_end': "-",
        'computed_duration': "-",
        'has_attendance': False,
        'earliest_start_time': None,
        'latest_end_time': None,
        'earliest_actual_start': None,
        '_raw_duration': None,
    }
