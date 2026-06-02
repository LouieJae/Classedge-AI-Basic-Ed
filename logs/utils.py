from django.contrib.auth import get_user_model
from .models import Notification
from course.models import SubjectEnrollment

User = get_user_model()

def create_notifications_for_subject_students(
    subject,
    entity_id,
    message_template,
    entity_type=None,
    created_by=None,
    name=None,
    due_at=None,
    path=None,
):
    """
    Create notifications for all students enrolled in a subject.
    
    Args:
        subject: The subject object
        entity_id: The ID of the entity (activity, module, etc.)
        message_template: Message template string
        entity_type: Optional type identifier for filtering
        created_by: The user who created this notification (optional)
        name: The notification name/title (optional)
        due_at: The due date/time for the notification (optional)
    
    Returns:
        List of created notification objects
    """
    if not subject:
        return []

    # Get all enrolled students for this subject. Materializing as a list
    # lets us pass the IDs into a single existence-check query below
    # instead of running one .exists() per student (N+1).
    enrolled_students = list(
        User.objects.filter(
            subjectenrollment__subject=subject,
            subjectenrollment__status='enrolled',
        ).distinct()
    )
    if not enrolled_students:
        return []

    # One bulk SELECT for existing notifications (vs. one per student).
    enrolled_ids = [s.id for s in enrolled_students]
    existing_user_ids = set(
        Notification.objects.filter(
            user_id__in=enrolled_ids,
            entity_id=entity_id,
            entity_type=entity_type,
            message__icontains=message_template[:50],
        ).values_list('user_id', flat=True)
    )

    created_notifications = []
    # We still INSERT one row at a time so each Notification's post_save
    # signal fires — the signal handler spawns the OneSignal push in a
    # background thread. Switching to bulk_create would skip the signal
    # entirely and break push delivery.
    for student in enrolled_students:
        if student.id in existing_user_ids:
            continue
        notification = Notification.objects.create(
            user_id=student,
            entity_id=entity_id,
            message=message_template,
            created_by=created_by,
            entity_type=entity_type,
            name=name,
            due_at=due_at,
            path=path,
        )
        created_notifications.append(notification)

    return created_notifications

def create_notification_for_teacher(
    subject,
    entity_id,
    message_template,
    entity_type=None,
    created_by=None,
    name=None,
    due_at=None,
    path=None,
):
    """
    Create notification for the teacher of a subject.
    
    Args:
        subject: The subject object
        entity_id: The ID of the entity
        message_template: Message template string
        entity_type: Optional type identifier for filtering
        created_by: The user who created this notification (optional)
        name: The notification name/title (optional)
        due_at: The due date/time for the notification (optional)
    
    Returns:
        Notification object or None
    """
    if not subject or not hasattr(subject, 'teacher'):
        return None
    
    teacher = subject.teacher
    if not teacher:
        return None
    
    if not Notification.objects.filter(
        user_id=teacher,
        entity_id=entity_id,
        entity_type=entity_type,
        message__icontains=message_template[:50]
    ).exists():
        return Notification.objects.create(
            user_id=teacher,
            entity_id=entity_id,
            message=message_template,
            created_by=created_by,
            entity_type=entity_type,
            name=name,
            due_at=due_at,
            path=path,
        )

    return None