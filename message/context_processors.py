import re
from urllib.parse import urlencode
from django.urls import reverse, NoReverseMatch
from .models import *
from logs.models import SubjectLog, UserSubjectLog


# Activity-related SubjectLog messages are formatted as:
#   "A New <type> Named '<name>' Has Been Added For <subject>."
# We pull the name out so the bell-popover link can resolve to the
# specific Activity's assessment-details page. SubjectLog has no FK to
# Activity (just a boolean `activity` flag), so this string match is
# the cleanest path that doesn't require a schema migration.
_ACTIVITY_NAME_RE = re.compile(r"Named '(.+?)'")


def _activity_target_for_log(log):
    """Return the assessment-details URL for the Activity referenced by
    a SubjectLog, or None if we can't pin it to a specific Activity."""
    if not log.activity:
        return None
    m = _ACTIVITY_NAME_RE.search(log.message or "")
    if not m:
        return None
    name = m.group(1)
    # Import here to avoid a circular import at app load.
    from activity.models import Activity
    activity = (
        Activity.objects
        .filter(subject_id=log.subject_id, activity_name=name)
        .order_by('-pk')
        .first()
    )
    if not activity or not activity.local_id:
        return None
    try:
        return reverse('assessment-details', args=[activity.local_id])
    except NoReverseMatch:
        return None


def _safe_url(name, *args):
    """Reverse a URL by name, returning '#' if it doesn't resolve.
    Lets the context processor stay safe across deployments where a
    given URL (e.g. 'inbox', 'classroom_mode') may be unregistered."""
    try:
        return reverse(name, args=args)
    except NoReverseMatch:
        return '#'

def unread_messages_count(request):
    if not request.user.is_authenticated:
        return {'unread_messages_count': 0, 'unread_messages': []}

    unread_messages = MessageUnreadStatus.objects.filter(user=request.user).values_list('message', flat=True)
    unread_count = len(unread_messages)

    return {
        'unread_messages_count': unread_count,
        'unread_messages': Message.objects.filter(id__in=unread_messages).order_by('-timestamp')[:5]
    }


def unread_notifications_count(request):
    if not request.user.is_authenticated:
        return {'unread_notifications_count': 0, 'notifications': [], 'show_logs': False}

    # [Classedge LMS] Subject logs are visible only to students (enrolled
    # subjects) and teachers (assigned subjects). show_logs is exposed for
    # legacy templates (templates/includes/navbar.html) that gate the
    # whole panel on it.
    from course.models import SubjectEnrollment
    from subject.models import Subject

    user_role = ""
    if hasattr(request.user, 'profile') and getattr(request.user.profile, 'role', None):
        user_role = request.user.role_name or ""
    show_logs = user_role in ('student', 'teacher')

    # Get general user notifications
    user_notifications = MessageNotification.objects.filter(user=request.user).order_by('-created_at')

    # Subject-scope activity logs to the user's own subjects so a teacher
    # doesn't see another teacher's class. Falls back to none for
    # non-student/non-teacher roles.
    subject_logs = SubjectLog.objects.none()
    if show_logs:
        if user_role == 'student':
            allowed_ids = SubjectEnrollment.objects.filter(student=request.user).values_list('subject', flat=True)
        else:  # teacher
            allowed_ids = Subject.objects.filter(assign_teacher=request.user).values_list('id', flat=True)
        subject_logs = SubjectLog.objects.filter(activity=True, subject__in=allowed_ids).order_by('-created_at')[:10]

    # Get friend request notifications (but avoid adding duplicates)
    existing_friend_request_notifs = set(
        MessageNotification.objects.filter(user=request.user, message__icontains="sent you a friend request.").values_list('message', flat=True)
    )

    friend_requests = FriendRequest.objects.filter(recipient=request.user, status="pending").order_by('-created_at')

    inbox_url = _safe_url('inbox')

    friend_notifications_list = []

    for friend in friend_requests:
        friend_message = f"{friend.sender.get_full_name()} sent you a friend request."

        # Only add if it is not already in the notifications model
        if friend_message not in existing_friend_request_notifs:
            friend_notifications_list.append({
                "id": friend.id,
                "message": friend_message,
                "created_at": friend.created_at,
                "icon": "fas fa-user-friends",
                "type": "friend_request",
                "is_read": False,  # Always unread
                "link": inbox_url,  # Friend requests are actioned from the inbox UI
            })

    # Convert user notifications. Most user_notification messages today are
    # friend-request copies (see message/views.py::add_friend), so the inbox
    # is the right landing surface — that's where the friend modal lives.
    # For unread rows the link is wrapped in `open_notification?next=…` so
    # the server marks-as-read on click *before* redirecting to the real
    # destination — guaranteed flip, no JS race.
    user_notifications_list = []
    for notif in user_notifications:
        target = inbox_url
        if not notif.is_read:
            try:
                open_url = reverse('open_notification', args=[notif.id])
                link = f"{open_url}?{urlencode({'next': target})}"
            except NoReverseMatch:
                link = target
        else:
            link = target
        user_notifications_list.append({
            "id": notif.id,
            "message": notif.message,
            "created_at": notif.created_at,
            "icon": "fas fa-bell",
            "type": "user_notification",
            "is_read": notif.is_read,
            "link": link,
        })

    # Convert subject logs — per-user read state lives on UserSubjectLog
    # (auto-created on first sighting), and each unread row routes
    # through open_subject_log so the click both marks the per-user row
    # read AND redirects to the most specific page we can resolve:
    #   • If the log mentions a known Activity (by name match), → that
    #     activity's assessment-details page (the cuid URL).
    #   • Otherwise, → the subject's material list as a sensible fallback.
    subject_logs_list = []
    for log in subject_logs:
        user_log, _ = UserSubjectLog.objects.get_or_create(user=request.user, subject_log=log)
        target = _activity_target_for_log(log) or _safe_url('material-list', log.subject_id)
        if not user_log.read:
            try:
                open_url = reverse('open_subject_log', args=[log.id])
                link = f"{open_url}?{urlencode({'next': target})}"
            except NoReverseMatch:
                link = target
        else:
            link = target
        subject_logs_list.append({
            "id": log.id,
            "message": log.message,
            "created_at": log.created_at,
            "icon": "fas fa-book",
            "type": "subject_log",
            "is_read": user_log.read,
            "link": link,
        })

    # Academic notifications (grade posted, deadline approaching, …) created
    # via logs.notifications.notify. Each carries its own target `path`, so
    # unread rows route through open_academic_notification (mark-read → next).
    from logs.models import Notification as AcademicNotification
    academic_list = []
    academic_qs = AcademicNotification.objects.filter(user_id=request.user).order_by('-created_at')[:20]
    for n in academic_qs:
        target = n.path or '/'
        if not n.is_read:
            try:
                open_url = reverse('open_academic_notification', args=[n.id])
                link = f"{open_url}?{urlencode({'next': target})}"
            except NoReverseMatch:
                link = target
        else:
            link = target
        academic_list.append({
            "id": n.id,
            "message": n.message,
            "created_at": n.created_at,
            "icon": "fas fa-bell",
            "type": "academic",
            "is_read": n.is_read,
            "link": link,
        })

    # Combine all notifications
    combined_notifications = friend_notifications_list + user_notifications_list + subject_logs_list + academic_list

    # Sort notifications by latest created_at
    combined_notifications.sort(key=lambda x: x['created_at'], reverse=True)

    # Count unread notifications across the whole combined list
    unread_count = sum(1 for n in combined_notifications if not n["is_read"])

    # Promote all unread rows ahead of read ones so the count and the
    # visible rows agree (previously capped at 5: the bell could claim
    # "7 unread" while rendering only 5). The .notif-list has its own
    # max-height + scroll, so we can safely render up to 20 here.
    unread_rows = [n for n in combined_notifications if not n['is_read']]
    read_rows = [n for n in combined_notifications if n['is_read']]
    limited_notifications = (unread_rows + read_rows[:max(0, 20 - len(unread_rows))])

    return {
        'unread_notifications_count': unread_count,  # Correct unread count
        'notifications': limited_notifications,  # Pass combined notifications
        'show_logs': show_logs,  # Legacy navbar.html still gates on this
    }



def pending_friend_requests_count(request):
    if not request.user.is_authenticated:
        return {'pending_friend_requests_count': 0}

    pending_count = FriendRequest.objects.filter(recipient=request.user, status="pending").count()
    return {'pending_friend_requests_count': pending_count}
