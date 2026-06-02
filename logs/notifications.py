"""Lightweight helper for creating in-app notifications.

Phase 1 of the proactive-notification engine. Writes rows to the existing
``logs.Notification`` model (which carries a target ``path`` + ``due_at``),
which the bell-popover context processor
(``message.context_processors.unread_notifications_count``) surfaces alongside
messages and subject logs.

Keep call sites trivial:

    from logs.notifications import notify
    notify(student, "Your grade was posted.", path="/my/grades/",
           entity_type="grade_visible", entity_id=subject.id, dedupe_hours=12)
"""
from datetime import timedelta

from django.utils import timezone

from logs.models import Notification


def notify(user, message, *, name="", path="", entity_type="",
           entity_id="", due_at=None, created_by=None, dedupe_hours=None):
    """Create one notification for ``user``. Returns the row, or None if skipped.

    When ``dedupe_hours`` is set (with entity_type + entity_id), a matching
    notification created within that window suppresses a duplicate — so a
    daily reminder job or a re-toggled setting won't spam the bell.
    """
    if user is None:
        return None

    entity_id = str(entity_id or "")
    if dedupe_hours and entity_type and entity_id:
        since = timezone.now() - timedelta(hours=dedupe_hours)
        exists = Notification.objects.filter(
            user_id=user, entity_type=entity_type, entity_id=entity_id,
            created_at__gte=since,
        ).exists()
        if exists:
            return None

    return Notification.objects.create(
        user_id=user,
        message=message,
        name=(name or message)[:255],
        path=path or "",
        entity_type=entity_type or None,
        entity_id=entity_id,
        due_at=due_at,
        created_by=created_by,
    )
