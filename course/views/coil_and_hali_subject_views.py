"""COIL and HALI subject list views.

The student/teacher/program-head queryset shape is near-identical to the
regular subject list and to the CTE list. The truly shared pieces
(semester resolution, program-head department scoping, per-subject
metric decoration, program-head search) live in
``course.utils.program_subjects``.

COIL-specific invite/participation actions moved to ``coil.views``.
"""
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from accounts.models import Profile
from subject.forms import CoilSubjectForm
from subject.models import Subject

from course.utils.program_subjects import (
    annotate_subject_metrics,
    apply_program_head_search,
    resolve_program_head_scope,
    resolve_semester_selection,
)


# Per-program presentation metadata reused by the shared template
# (course/program_subject_list.html). Keep these in the view module so each
# program owns its branding without the template doing string switches.
PROGRAM_META = {
    'coil': {
        'slug': 'coil',
        'label': 'COIL',
        'name': 'Collaborative Online International Learning',
        'icon': 'fa-handshake-angle',
        'list_url_name': 'coil_subjectList',
    },
    'hali': {
        'slug': 'hali',
        'label': 'HALI',
        'name': 'Higher Asian Learning Initiative',
        'icon': 'fa-globe-americas',
        'list_url_name': 'hali_subjectList',
    },
    'cte': {
        'slug': 'cte',
        'label': 'CTE',
        'name': 'Career & Technical Education',
        'icon': 'fa-screwdriver-wrench',
        'list_url_name': 'cte_subject_list',
    },
}


def _build_coil_or_hali_queryset(*, user, profile, selected_semester, category_flag, apply_semester_to_non_students):
    """Queryset shape shared by COIL and HALI. ``category_flag`` is the
    dict-style filter for the program flag, e.g. ``{'is_coil': True}``.
    HALI applies the enrollment-semester filter to non-students; COIL
    historically does not — that's the only structural divergence."""
    base = Subject.objects.filter(**category_flag)

    if profile.is_student:
        return base.filter(
            subjectenrollment__student=user,
            subjectenrollment__semester=selected_semester,
        ).distinct().order_by('subject_name')

    if profile.is_teacher:
        teacher_q = (
            Q(assign_teacher=user, subjectenrollment__semester=selected_semester)
            | Q(assign_teacher=user, subjectenrollment__isnull=True)
            | Q(substitute_teacher=user, allow_substitute_teacher=True)
            | Q(collaborators=user)
        )
        return base.filter(teacher_q).distinct().order_by('subject_name')

    if profile.is_program_head:
        department_list, _ = resolve_program_head_scope(profile)
        qs = base
        if apply_semester_to_non_students:
            qs = qs.filter(subjectenrollment__semester=selected_semester)
        if department_list:
            qs = qs.filter(
                Q(assign_teacher__profile__department_fields__name__in=department_list)
                | Q(substitute_teacher__profile__department_fields__name__in=department_list)
            )
        return qs.distinct().order_by('subject_name')

    # Default: every available subject (optionally semester-scoped)
    qs = base
    if apply_semester_to_non_students:
        qs = qs.filter(subjectenrollment__semester=selected_semester)
    else:
        qs = qs.filter(status='Available')
    return qs.distinct().order_by('subject_name')


def _render_program_list(request, *, category_flag, program_meta, apply_semester_to_non_students, extra_context=None):
    user = request.user
    profile = get_object_or_404(Profile, user=user)

    (
        semesters,
        current_semester,
        selected_semester,
        selected_semester_id,
        search_query,
        current_date,
    ) = resolve_semester_selection(request)

    if profile.is_program_head:
        _, college_name = resolve_program_head_scope(profile)
    else:
        college_name = "My Subjects"

    if selected_semester:
        subjects = _build_coil_or_hali_queryset(
            user=user,
            profile=profile,
            selected_semester=selected_semester,
            category_flag=category_flag,
            apply_semester_to_non_students=apply_semester_to_non_students,
        )
        subjects = apply_program_head_search(subjects, profile, search_query)
        subjects = list(subjects)
        annotate_subject_metrics(subjects, user, selected_semester, current_date)
    else:
        subjects = []

    paginator = Paginator(subjects, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Pick the right base template: students see the student shell,
    # everyone else (teacher / program head / dean / registrar / etc.)
    # gets the operations shell. The shared content template extends
    # whichever was selected.
    is_student = profile.is_student
    parent_template = 'student_base.html' if is_student else 'base_operation.html'

    context = {
        'page_obj': page_obj,
        'subjects': page_obj.object_list,
        'semesters': semesters,
        'selected_semester_id': selected_semester_id,
        'selected_semester': selected_semester,
        'current_semester': current_semester,
        'current_day': datetime.now().strftime('%a'),
        'can_view_teacher_attendance': user.has_perm('classroom.view_teacher_attendance'),
        'search_query': search_query,
        'is_program_head_or_dean': profile.role_name in ['program head', 'academic dean'],
        'is_student_view': is_student,
        'college_name': college_name,
        'program_meta': program_meta,
        'parent_template': parent_template,
    }
    if extra_context:
        context.update(extra_context)
    return render(request, 'course/program_subject_list.html', context)


@login_required
def coil_subjectList(request):
    return _render_program_list(
        request,
        category_flag={'is_coil': True},
        program_meta=PROGRAM_META['coil'],
        apply_semester_to_non_students=False,
        extra_context={
            'form': CoilSubjectForm(),
            'is_registrar_or_coil_admin': (
                request.user.is_authenticated
                and request.user.role_name in ['registrar', 'coil admin']
            ),
        },
    )


@login_required
def hali_subjectList(request):
    return _render_program_list(
        request,
        category_flag={'is_hali': True},
        program_meta=PROGRAM_META['hali'],
        apply_semester_to_non_students=True,
    )
