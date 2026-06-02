from celery import shared_task
from django.utils import timezone
from django.utils.timezone import localtime, make_aware, get_current_timezone
from django.db import transaction
from datetime import datetime, timedelta


@shared_task(bind=True, max_retries=3)
def auto_end_class(self, attendance_id):
    """
    Automatically end a class session when scheduled end time is reached.
    
    Args:
        attendance_id: ID of the Teacher_Attendance record
    """
    try:
        from classroom.models import Teacher_Attendance
        from course.models import Semester
        
        # Get the attendance record
        try:
            teacher_attendance = Teacher_Attendance.objects.get(id=attendance_id, is_active=True)
        except Teacher_Attendance.DoesNotExist:
            return {"status": "already_ended", "attendance_id": attendance_id}
        
        current_time = localtime(timezone.now())
        current_day = current_time.strftime('%a')

        # Get current semester
        today_date = current_time.date()
        current_semester = Semester.objects.filter(
            start_date__lte=today_date,
            end_date__gte=today_date
        ).first()
        
        # Get the schedule for today to find the scheduled end time
        subject = teacher_attendance.subject
        schedules = subject.schedules.filter(
            days_of_week__icontains=current_day
        )
        
        # Add semester filter if current semester exists
        if current_semester:
            schedules = schedules.filter(semester=current_semester)

        scheduled_end_time = None
        if schedules.exists():
            start_time = localtime(teacher_attendance.time_started).time()
            for schedule in schedules:
                early_start = (datetime.combine(today_date, schedule.schedule_start_time) - timedelta(minutes=15)).time()
                if early_start <= start_time <= schedule.schedule_end_time:
                    scheduled_end_time = schedule.schedule_end_time
                    break
        
        # Determine the end time to save
        if scheduled_end_time:
            # Use scheduled end time
            end_time = datetime.combine(current_time.date(), scheduled_end_time)
            end_time = make_aware(end_time, get_current_timezone())
        else:
            # No schedule found, use current time
            end_time = current_time

        with transaction.atomic():
            teacher_attendance.time_ended = end_time
            teacher_attendance.is_active = False
            teacher_attendance.manual_ended = False  # Auto-ended
            teacher_attendance.celery_task_id = None  # Clear task ID
            teacher_attendance.save(update_fields=['time_ended', 'is_active', 'manual_ended', 'celery_task_id'])
        
        # Verify the save
        teacher_attendance.refresh_from_db()

        return {
            "status": "success",
            "attendance_id": attendance_id,
            "end_time": end_time.isoformat()
        }
        
    except Exception as exc:
        
        if self.request.retries < 3:
            retry_in = 60 * (2 ** self.request.retries)
        # Retry the task with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))