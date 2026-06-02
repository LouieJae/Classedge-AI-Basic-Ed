"""
Authorization utilities for activity app.
Centralized authorization checks to prevent unauthorized access to activities.
"""
from django.shortcuts import redirect
from django.contrib import messages
from course.models import SubjectEnrollment, Semester
from course.utils.program_subjects import subject_list_url_name
from django.utils import timezone


# Admin-like roles that bypass subject/activity gating.
# - 'admin', 'dean', 'program head', 'academic director' — supervisory
#   roles that need read access across every subject/activity.
# - 'time keeper' — included in both sets so they can enter assessment
#   rooms during proctoring as well as view the parent subject context.
SUBJECT_ADMIN_ROLES = {'admin', 'dean', 'program head', 'academic director', 'time keeper'}
ACTIVITY_ADMIN_ROLES = SUBJECT_ADMIN_ROLES


def _resolve_roles(user, admin_roles):
    """Return (is_student, is_teacher, is_admin) for ``user``.

    ``is_admin`` here is role-based (not permission-based) — we deliberately
    do NOT bypass via has_perm to keep the gate aligned with actual job role.
    """
    if not user.is_authenticated:
        return False, False, False
    return user.is_student, user.is_teacher, user.role_name in admin_roles


def _teacher_is_assigned(subject, user):
    """True if ``user`` is the assigned teacher, a collaborator, or the
    active substitute (only when allow_substitute_teacher is on, matching
    Subject.active_teacher semantics)."""
    if subject.assign_teacher == user:
        return True
    if user in subject.collaborators.all():
        return True
    return subject.substitute_teacher == user and subject.allow_substitute_teacher


def check_activity_access(request, activity, require_teacher=False, require_student=False):
    """
    Check if user has permission to access an activity.

    Args:
        request: Django request object
        activity: Activity object
        require_teacher: If True, only teachers assigned to subject can access
        require_student: If True, only enrolled students can access

    Returns:
        tuple: (has_access: bool, redirect_response: HttpResponse or None)
    """
    user = request.user
    subject = activity.subject
    is_student, is_teacher, is_admin = _resolve_roles(user, ACTIVITY_ADMIN_ROLES)

    if is_admin and not (require_teacher or require_student):
        return True, None

    if is_student:
        if require_teacher:
            messages.error(request, "You do not have permission to access this page.")
            return False, redirect(subject_list_url_name(subject))

        # Check enrollment for the current semester AND the activity's term semester.
        now = timezone.localtime(timezone.now())
        current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()
        activity_semester = activity.term.semester if activity.term else current_semester
        semesters = [current_semester, activity_semester] if activity_semester else [current_semester]

        is_enrolled = SubjectEnrollment.objects.filter(
            student=user,
            subject=subject,
            semester__in=semesters,
            status='enrolled',
        ).exists()
        if not is_enrolled:
            messages.error(request, "You are not enrolled in this subject.")
            return False, redirect(subject_list_url_name(subject))
        return True, None

    if is_teacher:
        if require_student:
            messages.error(request, "You do not have permission to access this page.")
            return False, redirect(subject_list_url_name(subject))
        if not _teacher_is_assigned(subject, user):
            messages.error(request, "You are not assigned to this subject.")
            return False, redirect(subject_list_url_name(subject))
        return True, None

    if is_admin:
        return True, None

    messages.error(request, "You do not have permission to access this activity.")
    return False, redirect(subject_list_url_name(subject))


def check_subject_access(request, subject, require_teacher=False, require_student=False):
    """
    Check if user has permission to access a subject.

    Args:
        request: Django request object
        subject: Subject object
        require_teacher: If True, only teachers assigned to subject can access
        require_student: If True, only enrolled students can access

    Returns:
        tuple: (has_access: bool, redirect_response: HttpResponse or None)
    """
    user = request.user
    is_student, is_teacher, is_admin = _resolve_roles(user, SUBJECT_ADMIN_ROLES)

    if is_admin and not (require_teacher or require_student):
        return True, None

    if is_student:
        if require_teacher:
            messages.error(request, "You do not have permission to access this page.")
            return False, redirect(subject_list_url_name(subject))

        now = timezone.localtime(timezone.now())
        current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()
        is_enrolled = SubjectEnrollment.objects.filter(
            student=user,
            subject=subject,
            semester=current_semester,
            status='enrolled',
        ).exists()
        if not is_enrolled:
            messages.error(request, "You are not enrolled in this subject.")
            return False, redirect(subject_list_url_name(subject))
        return True, None

    if is_teacher:
        if require_student:
            messages.error(request, "You do not have permission to access this page.")
            return False, redirect(subject_list_url_name(subject))
        if not _teacher_is_assigned(subject, user):
            messages.error(request, "You are not assigned to this subject.")
            return False, redirect(subject_list_url_name(subject))
        return True, None

    if is_admin:
        return True, None

    messages.error(request, "You do not have permission to access this subject.")
    return False, redirect(subject_list_url_name(subject))


def activity_has_submissions(activity):
    """Return True when at least one student has finalized an attempt on this
    activity. Used to lock down question edits after submissions exist so
    teachers can't silently invalidate already-graded work.
    """
    from activity.models import StudentActivity
    return StudentActivity.objects.filter(
        activity=activity, retake_count__gte=1
    ).exists()
