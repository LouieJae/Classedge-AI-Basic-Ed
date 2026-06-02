"""Archive views — read-only browsing of past-semester courses, activities, modules.

These views never let a student submit, retake, or modify anything. They mirror
the current-semester pages but with `is_archive_view=True` so templates can hide
action buttons.
"""
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from activity.models import Activity, StudentActivity
from course.models import Semester, SubjectEnrollment
from module.models import Module
from module.models.student_progress import StudentProgress
from subject.models import Subject


def _current_semester():
    today = timezone.localtime(timezone.now()).date()
    return Semester.objects.filter(
        start_date__lte=today, end_date__gte=today,
    ).first()


def _user_role(user):
    try:
        return (user.role_name)
    except AttributeError:
        return ''


@login_required
def archive_index(request):
    """List past-semester subjects.

    Students see the subjects they were enrolled in. Teachers see the subjects
    they taught (assigned/collaborator/substitute). Admin-style roles see every
    subject from past semesters.
    """
    user = request.user
    current = _current_semester()
    role = _user_role(user)
    admin_roles = {'admin', 'registrar', 'program head', 'academic director', 'super admin'}

    semesters = {}

    def _bucket(subject, semester, source=None):
        if not semester:
            return
        bucket = semesters.setdefault(semester.id, {
            'semester': semester,
            'subjects': [],
            'seen_subject_ids': set(),
        })
        if subject.id in bucket['seen_subject_ids']:
            return
        bucket['seen_subject_ids'].add(subject.id)
        bucket['subjects'].append(subject)

    # Student-side enrollments
    enrollments = (
        SubjectEnrollment.objects
        .filter(student=user)
        .exclude(semester__isnull=True)
        .select_related('subject', 'semester')
    )
    if current:
        enrollments = enrollments.exclude(semester_id=current.id)
    for enr in enrollments:
        _bucket(enr.subject, enr.semester)

    # Teacher-side: subjects this user taught in past semesters (assigned, collab, substitute)
    is_teacher_role = role == 'teacher'
    if is_teacher_role or user.is_superuser or role in admin_roles:
        taught = SubjectEnrollment.objects.exclude(semester__isnull=True).select_related('subject', 'semester')
        if current:
            taught = taught.exclude(semester_id=current.id)
        if is_teacher_role:
            taught = taught.filter(
                Q(subject__assign_teacher=user)
                | Q(subject__substitute_teacher=user)
                | Q(subject__collaborators=user)
            )
        # admin roles see everything
        taught = taught.distinct()
        for enr in taught:
            _bucket(enr.subject, enr.semester)

    semester_groups = sorted(
        semesters.values(),
        key=lambda g: g['semester'].end_date or g['semester'].start_date,
        reverse=True,
    )

    return render(request, 'accounts/archive/archive_index.html', {
        'semester_groups': semester_groups,
        'is_admin_view': user.is_superuser or role in admin_roles or is_teacher_role,
        'is_student_role': role == 'student',
    })


@login_required
def archive_subject(request, subject_id, semester_id):
    """Read-only subject page for a past semester.

    Students see their own activities + module progress. Teachers/admins see
    the class roster with each student's score + completion.
    """
    user = request.user
    subject = get_object_or_404(Subject, pk=subject_id)
    semester = get_object_or_404(Semester, pk=semester_id)

    role = _user_role(user)
    admin_roles = {'admin', 'registrar', 'program head', 'academic director', 'super admin'}

    is_taught = (
        subject.assign_teacher_id == user.id
        or subject.substitute_teacher_id == user.id
        or subject.collaborators.filter(id=user.id).exists()
    )
    is_admin_view = user.is_superuser or role in admin_roles or (role == 'teacher' and is_taught)

    # Authorization: enrolled OR taught it OR admin-style role.
    was_enrolled = SubjectEnrollment.objects.filter(
        student=user, subject=subject, semester=semester,
    ).exists()
    if not (was_enrolled or is_admin_view):
        return render(request, 'accounts/archive/archive_denied.html', status=403)

    activities = (
        Activity.objects
        .filter(subject=subject, term__semester=semester, status=True)
        .select_related('activity_type')
        .distinct()
        .order_by('end_time')
    )

    modules = Module.objects.filter(
        subject=subject, term__semester=semester,
    ).order_by('order', 'pk')

    # ── Student view: their own progress per activity/module ──
    activity_rows = []
    module_rows = []
    if not is_admin_view:
        student_activities = {
            sa.activity_id: sa for sa in StudentActivity.objects.filter(
                student=user, activity__in=activities,
            )
        }
        for act in activities.filter(Q(remedial=False) | Q(remedial_students=user)):
            sa = student_activities.get(act.pk)
            activity_rows.append({
                'activity': act,
                'score': sa.total_score if sa else None,
                'max_score': act.max_score,
                'submitted': bool(sa and (sa.retake_count or 0) >= 1),
                'submitted_at': sa.end_time if sa else None,
            })

        module_progress = {
            mp.module_id: mp for mp in StudentProgress.objects.filter(
                student=user, module__in=modules,
            )
        }
        for mod in modules:
            mp = module_progress.get(mod.pk)
            module_rows.append({
                'module': mod,
                'completed': bool(mp and mp.completed),
                'progress': float(mp.progress) if mp else 0.0,
            })

    # ── Admin/teacher view: class roster with score/progress aggregates ──
    roster_rows = []
    if is_admin_view:
        enrolled = (
            SubjectEnrollment.objects
            .filter(subject=subject, semester=semester)
            .select_related('student', 'student__profile')
            .order_by('student__last_name', 'student__first_name')
        )
        roster_students = [e.student for e in enrolled if e.student]
        total_activity = activities.count()
        total_module = modules.count()
        sas = StudentActivity.objects.filter(
            activity__in=activities, student__in=roster_students,
        ).values('student_id', 'activity_id', 'total_score', 'retake_count', 'end_time')
        sa_by_student = {}
        for row in sas:
            d = sa_by_student.setdefault(row['student_id'], {'submitted': 0, 'total_score': 0.0})
            if (row.get('retake_count') or 0) >= 1:
                d['submitted'] += 1
            d['total_score'] += float(row.get('total_score') or 0)
        mps = StudentProgress.objects.filter(
            module__in=modules, student__in=roster_students,
        ).values('student_id', 'completed')
        mp_by_student = {}
        for row in mps:
            d = mp_by_student.setdefault(row['student_id'], {'done': 0})
            if row.get('completed'):
                d['done'] += 1
        for s in roster_students:
            sa = sa_by_student.get(s.id, {'submitted': 0, 'total_score': 0.0})
            mp = mp_by_student.get(s.id, {'done': 0})
            roster_rows.append({
                'student': s,
                'activities_submitted': sa['submitted'],
                'activities_total': total_activity,
                'modules_done': mp['done'],
                'modules_total': total_module,
                'total_score': sa['total_score'],
            })

    return render(request, 'accounts/archive/archive_subject.html', {
        'subject': subject,
        'semester': semester,
        'activity_rows': activity_rows,
        'module_rows': module_rows,
        'roster_rows': roster_rows,
        'is_admin_view': is_admin_view,
        'activities_count': activities.count(),
        'modules_count': modules.count(),
        'is_archive_view': True,
        'is_student_role': role == 'student',
    })


@login_required
def archive_module(request, module_id):
    """Read-only view of a past-semester module's content."""
    module = get_object_or_404(Module, pk=module_id)
    # Authorization: must have been enrolled in the module's subject/semester.
    user = request.user
    if module.term and module.term.semester_id:
        if not SubjectEnrollment.objects.filter(
            student=user, subject=module.subject, semester=module.term.semester,
        ).exists():
            return render(request, 'accounts/archive/archive_denied.html', status=403)
    return render(request, 'accounts/archive/archive_module.html', {
        'module': module,
        'subject': module.subject,
        'semester': module.term.semester if module.term else None,
        'is_archive_view': True,
        'is_student_role': _user_role(user) == 'student',
    })
