import threading
from django.db import close_old_connections, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from migration.side_effects import push_suppressed
from .models import Notification
from .views import _send_onesignal_notification


def _dispatch_push_async(user_id, username, heading, message, notification_data):
    """Run the OneSignal HTTP call off the request thread.

    Each call to OneSignal's REST API costs ~1–2 s round-trip. With one
    Notification per enrolled student (15–20 users on a real subject),
    keeping it in the request loop adds 20–40 s of blocking I/O to every
    lesson/assessment creation. Daemon thread → fire-and-forget."""
    try:
        external_ids = [str(user_id)]
        result = _send_onesignal_notification(
            heading=heading,
            message=message,
            external_ids=external_ids,
            data=notification_data,
        )
        if result.get('success'):
            print(f"[NotificationSignal] Push sent to user {user_id} ({username}): {result.get('notification_id')}")
        else:
            print(f"[NotificationSignal] Push FAILED for user {user_id} ({username}): {result.get('error')}")
    except Exception as e:
        print(f"[NotificationSignal] Push thread error for user {user_id}: {e}")
    finally:
        # Each thread gets its own DB connection — return it to the pool so
        # the connection doesn't leak when the thread exits.
        close_old_connections()


@receiver(post_save, sender=Notification)
def send_push_notification_on_create(sender, instance, created, **kwargs):
    """Queue a OneSignal push for any newly-created Notification.

    Runs in a background thread so the request that created the
    Notification returns immediately."""
    if not created:
        return
    # Thread-local switch flipped on by the migration writer while importing
    # rows. Every migrated Activity / Module fans out into Notifications that
    # none of the migrated users have subscribed devices for, so we silence
    # the OneSignal call for those rows only. Notification rows are still
    # created in the DB so the in-app bell keeps working.
    if push_suppressed():
        return
    try:
        user = instance.user_id
        if not user:
            print(f"[NotificationSignal] No user on notification {instance.id}, skipping push")
            return

        # Restrict lesson/activity pushes to students only
        if instance.entity_type in ('lesson', 'module', 'activity'):
            role_name = ''
            try:
                role = getattr(getattr(user, 'profile', None), 'role', None)
                role_name = (role.name.lower() if role and role.name else '')
            except Exception:
                role_name = ''
            if role_name != 'student':
                print(f"[NotificationSignal] Skipping push for entity_type={instance.entity_type} — user role is '{role_name}', not student")
                return

        heading, message = _format_notification_content(instance)
        notification_data = {
            'entityType': instance.entity_type or 'general',
            'entityId': instance.entity_id,
            'notificationId': instance.id,
            'path': instance.path or '',
        }
        if instance.due_at:
            notification_data['dueAt'] = instance.due_at.isoformat()

        # Fire the push after the current transaction commits so any DB
        # state the OneSignal payload references (course names, etc.) is
        # actually visible. If no transaction is active, on_commit runs
        # the callback immediately, which is also fine.
        def _start_thread(
            uid=user.id, uname=user.username,
            h=heading, m=message, d=notification_data,
        ):
            threading.Thread(
                target=_dispatch_push_async,
                args=(uid, uname, h, m, d),
                daemon=True,
            ).start()

        transaction.on_commit(_start_thread)
    except Exception as e:
        # Don't let push-dispatch wiring break notification creation.
        print(f"[NotificationSignal] dispatch setup error: {e}")
        import traceback
        print(f"[NotificationSignal] Traceback: {traceback.format_exc()}")


def _format_notification_content(notification):
    """
    Format notification heading and message based on entity_type.
    
    Args:
        notification: Notification instance
        
    Returns:
        tuple: (heading, message) formatted for push notification
    """
    entity_type = notification.entity_type or 'general'
    
    # Get instructor name if available
    instructor_name = "Instructor"
    if notification.created_by:
        instructor_name = f"{notification.created_by.first_name} {notification.created_by.last_name}".strip()
        if not instructor_name:
            instructor_name = notification.created_by.username
    
    # Get course/subject name from the notification context
    course_name = "Course"
    try:
        if entity_type == 'activity':
            from activity.models import Activity
            activity = Activity.objects.filter(pk=notification.entity_id).first()
            if activity and activity.subject:
                course_name = activity.subject.subject_name
        elif entity_type == 'lesson' or entity_type == 'module':
            from module.models import Module
            module = Module.objects.filter(id=notification.entity_id).first()
            if module and module.subject:
                course_name = module.subject.subject_name
    except Exception as e:
        print(f"[NotificationFormat] Could not fetch course name: {e}")
    
    # Format based on entity type
    if entity_type == 'lesson' or entity_type == 'module':
        # 📖 New Lesson: [Course Name]
        heading = f"📖 New Lesson: {course_name}"
        
        # [Instructor Name] posted "[Lesson Title]." Tap to start learning!
        lesson_title = notification.name or "New Lesson"
        message = f'{instructor_name} posted "{lesson_title}." Tap to start learning!'
        
    elif entity_type == 'activity':
        # 🚀 New Activity: [Course Name]
        heading = f"🚀 New Activity: {course_name}"
        
        # [Instructor Name] assigned "[Activity Title]." Due: [Date].
        activity_title = notification.name or "New Activity"
        
        if notification.due_at:
            from django.utils import timezone
            # Format due date
            due_date = notification.due_at.strftime("%b %d, %Y %I:%M %p")
            message = f'{instructor_name} assigned "{activity_title}." Due: {due_date}.'
        else:
            message = f'{instructor_name} assigned "{activity_title}." Tap to view details!'
            
    else:
        # Default format for other types
        heading = notification.name or 'New Notification'
        message = notification.message
    
    return heading, message
