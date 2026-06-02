"""CTE subject list view. See course.utils.program_subjects for the
shared helpers used here and by the COIL/HALI/regular subject lists."""
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, render

from accounts.models import Profile
from subject.models import Schedule, Subject

from course.utils.program_subjects import (
    annotate_subject_metrics,
    apply_program_head_search,
    resolve_program_head_scope,
    resolve_semester_selection,
)
from course.views.coil_and_hali_subject_views import PROGRAM_META


def _build_cte_queryset(*, user, profile, selected_semester):
    base = Subject.objects.filter(is_cte=True).prefetch_related(
        Prefetch('schedules', queryset=Schedule.objects.filter(semester=selected_semester))
    )

    if profile.is_student:
        return base.filter(
            subjectenrollment__student=user,
            subjectenrollment__semester=selected_semester,
        ).distinct().order_by('subject_name')

    if profile.is_teacher:
        return base.filter(
            Q(assign_teacher=user) | Q(substitute_teacher=user, allow_substitute_teacher=True),
            subjectenrollment__semester=selected_semester,
        ).distinct().order_by('subject_name')

    if profile.is_program_head:
        department_list, _ = resolve_program_head_scope(profile)
        qs = base.filter(subjectenrollment__semester=selected_semester)
        if department_list:
            qs = qs.filter(
                Q(assign_teacher__profile__department_fields__name__in=department_list)
                | Q(substitute_teacher__profile__department_fields__name__in=department_list)
            )
        return qs.distinct().order_by('subject_name')

    return base.filter(
        subjectenrollment__semester=selected_semester,
    ).distinct().order_by('subject_name')


@login_required
def cte_subject_list(request):
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
        subjects = _build_cte_queryset(
            user=user, profile=profile, selected_semester=selected_semester,
        )
        subjects = apply_program_head_search(subjects, profile, search_query)
        subjects = list(subjects)
        annotate_subject_metrics(subjects, user, selected_semester, current_date)
    else:
        subjects = []

    paginator = Paginator(subjects, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    is_student = profile.is_student
    parent_template = 'student_base.html' if is_student else 'base_operation.html'

    return render(request, 'course/program_subject_list.html', {
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
        'program_meta': PROGRAM_META['cte'],
        'parent_template': parent_template,
    })
