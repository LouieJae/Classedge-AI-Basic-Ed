from datetime import datetime
from django.db import transaction
from django.utils.dateparse import parse_time
from django.core.exceptions import ValidationError
from accounts.models import CustomUser, Profile
from course.models import Semester
from roles.models import Role
from subject.models import Subject, Schedule
from accounts.utils.signal_utils import _thread_locals


@transaction.atomic
def sync_subject_and_schedule(data):
    # Extract teacher data from flat structure (RMS API format)
    teacher_email = (data.get("teacher_email") or "").strip().lower()
    first_name = (data.get("teacher_first_name") or "").strip()
    last_name = (data.get("teacher_last_name") or "").strip()
    
    if not teacher_email:
        raise ValidationError("Teacher information (with email) is required.")

    # Set flag to tell signal this is an RMS teacher creation
    _thread_locals.creating_rms_teacher = True
    
    try:
        teacher_user, created_user = CustomUser.objects.get_or_create(
            email=teacher_email,
            defaults={
                "username": teacher_email.split("@")[0],
                "first_name": first_name,
                "last_name": last_name,
                "needs_password_setup": False,
                "needs_onboarding": False,
            }
        )
        
    finally:
        # Always clean up the flag
        _thread_locals.creating_rms_teacher = False

    # Extract subject data from flat structure (RMS API format)
    subject_name = (data.get("subject_name") or "").strip()
    subject_short_name = (data.get("subject_short_name") or "").strip()
    subject_type = (data.get("subject_type") or "").strip()
    room_number = (data.get("room_name") or "").strip()
    subject_sync_id = (data.get("subject_sync_id") or "").strip()
    schedule_sync_id = (data.get("sync_id") or "").strip()
    
    if not subject_name:
        raise ValidationError("Subject information is required.")

    # Try to find existing subject by sync_id first (if provided)
    subject_obj = None
    created_subject = False
    
    if subject_sync_id:
        # Create composite sync_id using subject_sync_id + schedule_sync_id
        composite_sync_id = f"{subject_sync_id}_{schedule_sync_id}" if schedule_sync_id else subject_sync_id
        
        # Look for existing subject with matching composite sync_id
        subject_obj = Subject.objects.filter(subject_sync_id=composite_sync_id).first()
        
        if subject_obj:
            # Update existing subject with new data from RMS
            subject_obj.subject_name = subject_name
            subject_obj.subject_short_name = subject_short_name
            subject_obj.assign_teacher = teacher_user
            subject_obj.room_number = room_number
            subject_obj.subject_type = subject_type
            # Don't need to update subject_sync_id as it's already set and is the lookup key
            subject_obj.save()
        else:
            # Create new subject with composite sync_id
            subject_obj = Subject.objects.create(
                subject_name=subject_name,
                subject_short_name=subject_short_name,
                assign_teacher=teacher_user,
                room_number=room_number,
                subject_type=subject_type,
                subject_sync_id=composite_sync_id,
            )
            created_subject = True
    else:
        # Fallback to old behavior if no sync_id provided (composite key lookup)
        subject_obj, created_subject = Subject.objects.get_or_create(
            subject_name=subject_name,
            subject_type=subject_type,
            room_number=room_number,
            defaults={
                "subject_short_name": subject_short_name,
                "assign_teacher": teacher_user,
            }
        )
        if created_subject:
            pass
        else:
            pass

    # Extract academic term data from flat structure (RMS API format)
    semester_key = data.get("semester", "").strip()
    
    semester_map = {
        "1st": "First Semester",
        "2nd": "Second Semester",
        "3rd": "Third Semester",
        "4th": "Fourth Semester",
        "Summer": "Summer",
    }

    # Use provided semester or default to First Semester if missing
    if semester_key:
        semester_name = semester_map.get(semester_key)
        if not semester_name:
            raise ValidationError(f"Invalid semester key: {semester_key}")
    else:
        # Default to First Semester if not provided
        semester_name = "First Semester"

    start_date_str = data.get("start_date")
    end_date_str = data.get("end_date")

    # Try to parse dates, use defaults if not available
    start_date = None
    end_date = None
    
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            if end_date < start_date:
                raise ValidationError("End date cannot be earlier than start date.")
        except (ValueError, TypeError):
            # If dates are invalid, get from existing semester or use defaults
            start_date = None
            end_date = None
    
    # If dates not available, try to get from existing semester with same name
    if not start_date or not end_date:
        existing_semester = Semester.objects.filter(semester_name=semester_name).first()
        if existing_semester:
            start_date = existing_semester.start_date
            end_date = existing_semester.end_date
        else:
            # Use placeholder dates if no existing semester found
            from django.utils import timezone
            today = timezone.now().date()
            start_date = today
            end_date = today

    semester_obj, created_semester = Semester.objects.update_or_create(
        semester_name=semester_name,
        start_date=start_date,
        end_date=end_date,
        defaults={
            "end_semester": False,
            "passing_grade": 75,
            "grade_calculation_method": "Averaging",
        }
    )

    start_time = data.get("start_time")
    end_time = data.get("end_time")
    days = data.get("day")
    
    if not all([start_time, end_time, days]):
        raise ValidationError("Schedule start_time, end_time, and day are required.")

    # Parse days from string to list if needed
    if isinstance(days, str):
        try:
            days = eval(days)
            if not isinstance(days, list):
                raise ValueError
        except Exception:
            raise ValidationError("Invalid day format. Example: ['Mon', 'Tue']")
    elif not isinstance(days, list):
        raise ValidationError("Days must be a list (e.g., ['Mon', 'Tue']).")
    
    # Map full day names to abbreviations (API sends full names, model expects abbreviations)
    day_mapping = {
        'monday': 'Mon',
        'tuesday': 'Tue',
        'wednesday': 'Wed',
        'thursday': 'Thu',
        'friday': 'Fri',
        'saturday': 'Sat',
        'sunday': 'Sun',
        # Also handle abbreviations in case they're already abbreviated
        'mon': 'Mon',
        'tue': 'Tue',
        'wed': 'Wed',
        'thu': 'Thu',
        'fri': 'Fri',
        'sat': 'Sat',
        'sun': 'Sun',
    }
    
    # Convert all day names to abbreviations (case-insensitive, strip whitespace)
    normalized_days = []
    for day in days:
        original_day = day
        day_stripped = day.strip()
        day_lower = day_stripped.lower()
        
        mapped_day = day_mapping.get(day_lower)
        if mapped_day:
            normalized_days.append(mapped_day)
        else:
            normalized_days.append(day_stripped)
    
    days = normalized_days

    start_time_obj = parse_time(start_time)
    end_time_obj = parse_time(end_time)
    if not start_time_obj or not end_time_obj:
        raise ValidationError("Invalid time format. Use HH:MM:SS format.")

    if start_time_obj >= end_time_obj:
        raise ValidationError("Start time must be earlier than end time.")

    # Try to find existing schedule by sync_id first (if provided)
    schedule_obj = None
    created_schedule = False
    
    if schedule_sync_id:
        schedule_obj = Schedule.objects.filter(sync_id=schedule_sync_id).first()
        
        if schedule_obj:
            # Update existing schedule with new data from RMS (including times)
            schedule_obj.subject = subject_obj
            schedule_obj.schedule_start_time = start_time_obj
            schedule_obj.schedule_end_time = end_time_obj
            schedule_obj.semester = semester_obj
            schedule_obj.days_of_week = days
            schedule_obj.schedule_type = "Regular"
            schedule_obj.save()
        else:
            # Create new schedule with sync_id
            schedule_obj = Schedule.objects.create(
                subject=subject_obj,
                semester=semester_obj,
                schedule_start_time=start_time_obj,
                schedule_end_time=end_time_obj,
                days_of_week=days,
                schedule_type="Regular",
                sync_id=schedule_sync_id,
            )
            created_schedule = True
    else:
        # Fallback to old behavior if no sync_id provided
        schedule_obj, created_schedule = Schedule.objects.get_or_create(
            subject=subject_obj,
            semester=semester_obj,
            schedule_start_time=start_time_obj,
            schedule_end_time=end_time_obj,
            defaults={
                "days_of_week": days,
                "schedule_type": "Regular",
            }
        )
    
    return schedule_obj
