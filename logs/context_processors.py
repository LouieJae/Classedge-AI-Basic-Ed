# context_processors.py
from .models import SubjectLog, UserSubjectLog
from course.models import SubjectEnrollment
from subject.models import Subject

def subject_logs(request):
    if request.user.is_authenticated:
        # --- FIX START: Safe Role Check ---
        user_role = ""
        # Check if profile exists and has a role before accessing .name
        if hasattr(request.user, 'profile') and request.user.profile.role:
            user_role = request.user.role_name
        # --- FIX END ---

        show_logs = user_role in ['student', 'teacher']
        logs_with_read_status = []
        unread_notifications_count = 0

        if show_logs:
            if user_role == 'student':
                # Students: Show logs from enrolled subjects
                enrolled_subjects = SubjectEnrollment.objects.filter(student=request.user).values_list('subject', flat=True)
                logs = SubjectLog.objects.filter(activity=True, subject__in=enrolled_subjects).order_by('-created_at')[:5]
            elif user_role == 'teacher':
                # Teachers: Show logs from subjects they are assigned to
                teacher_subjects = Subject.objects.filter(assign_teacher=request.user).values_list('id', flat=True)
                logs = SubjectLog.objects.filter(activity=True, subject__in=teacher_subjects).order_by('-created_at')[:5]
            else:
                logs = []

            for log in logs:
                user_log, created = UserSubjectLog.objects.get_or_create(user=request.user, subject_log=log)
                logs_with_read_status.append({
                    "id": log.id,
                    "message": log.message,
                    "created_at": log.created_at,
                    "read": user_log.read,
                    "url": f"/material/list/{log.subject.id}/"
                })
                if not user_log.read:
                    unread_notifications_count += 1

        return {
            'show_logs': show_logs,
            'notifications': logs_with_read_status, 
            'unread_notifications_count': unread_notifications_count
        }
    return {}