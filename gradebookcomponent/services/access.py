"""[Classedge LMS] Access-control helpers for gradebook views."""
from django.core.exceptions import PermissionDenied


def can_audit_all_gradebooks(user):
    """[Classedge LMS] True for roles that may inspect every subject's gradebook
    (read-only audit), regardless of teaching assignment. Registrar is the
    primary audience; superusers/staff and admin-like roles also qualify.
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return bool(
        getattr(user, 'is_registrar', False)
        or getattr(user, 'is_admin', False)
        or getattr(user, 'is_program_head', False)
        or getattr(user, 'is_dean', False)
    )


def authorize_subject_access(user, subject):
    """[Classedge LMS] Raise PermissionDenied unless user owns or collaborates on
    the subject, or has a school-wide audit role (registrar, admin, etc).
    """
    if subject.assign_teacher_id == user.id:
        return
    if subject.collaborators.filter(pk=user.pk).exists():
        return
    if can_audit_all_gradebooks(user):
        return
    raise PermissionDenied("Not authorized for this subject.")
