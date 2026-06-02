from datetime import timedelta

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch
from django.utils import timezone
from subject.models import Subject
from activity.models import Activity, ActivityType, StudentActivity
from activity.utils.authorization import check_subject_access
from course.models.subject_enrollment_model import SubjectEnrollment
from course.models.semester_model import Semester
from course.models.term_model import Term
from course.utils.program_subjects import subject_list_url_name
from ..models.module import Module
from django.http import JsonResponse
from django.db.models import Count

@login_required
def student_pdf_viewer(request):
    """Self-hosted PDF.js viewer. Reads ?file=<url>&module=<id> from the query
    string client-side, renders the PDF, and saves page changes back to
    /module_progress/ so the student can resume where they left off.
    """
    return render(request, 'student/pdf_viewer.html')


@login_required
@permission_required('module.view_module', raise_exception=True)
def subject_student_roster(request, id):
    """Teacher-facing page listing all students enrolled in a subject."""
    subject = get_object_or_404(Subject, pk=id)
    has_access, redirect_response = check_subject_access(request, subject)
    if not has_access:
        return redirect_response

    search = request.GET.get('search', '').strip()
    roster_qs = (
        SubjectEnrollment.objects
        .filter(subject=subject, status='enrolled', student__isnull=False)
        .select_related('student', 'student__profile')
        .order_by('student__last_name', 'student__first_name')
    )
    if search:
        roster_qs = roster_qs.filter(
            Q(student__first_name__icontains=search)
            | Q(student__last_name__icontains=search)
            | Q(student__email__icontains=search)
            | Q(student__username__icontains=search)
        )

    students = [e.student for e in roster_qs]
    return render(request, 'module/subject-student-roster.html', {
        'subject': subject,
        'subject_id': id,
        'students': students,
        'students_count': len(students),
        'search_query': search,
        'back_url_name': subject_list_url_name(subject),
    })


def material_list(request, id):
    is_student = request.user.is_authenticated and request.user.is_student

    # Subject-level access gate: enrolled students, the primary teacher, an
    # active substitute, or a collaborator. Admins bypass.
    subject_for_auth = get_object_or_404(Subject, pk=id)
    has_access, redirect_response = check_subject_access(request, subject_for_auth)
    if not has_access:
        return redirect_response

    # Detect tab early so we can skip work the current view doesn't render.
    active_view = request.GET.get('view', 'lessons')
    if active_view not in ('lessons', 'assessments'):
        active_view = 'lessons'

    modules = Module.objects.filter(subject_id=id).select_related('subject', 'term')
    # Prefetch the lesson-anchored activities so we don't fire one query per
    # lesson on the current page (N+1 → 1). Only attach when the lessons view
    # actually needs them; the assessments tab never reads lesson_activities.
    if not is_student and active_view == 'lessons':
        modules = modules.prefetch_related(
            Prefetch(
                'additional_activities',
                queryset=(
                    Activity.objects.filter(status=True)
                    .exclude(activity_type__name__iexact='Participation')
                    .select_related('activity_type', 'subject')
                    .order_by('end_time', 'local_id')
                ),
                to_attr='_prefetched_lesson_activities',
            )
        )

    # Students only see lessons whose audience includes them (empty list =
    # everyone, otherwise explicit) and that have already opened. Past lessons
    # stay visible so students can review them.
    if is_student:
        modules = modules.filter(
            Q(display_lesson_for_selected_users__isnull=True)
            | Q(display_lesson_for_selected_users=request.user)
        ).distinct()
        now = timezone.now()
        modules = modules.filter(
            Q(start_date__isnull=True) | Q(start_date__lte=now)
        )

    subject = modules.first().subject if modules.exists() else get_object_or_404(Subject, pk=id)

    search_query = request.GET.get('search', '').strip()
    if search_query:
        modules = modules.filter(
            Q(file_name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(term__term_name__icontains=search_query)
        )

    # ── Term filter ──────────────────────────────────────────────────
    # Default: only show materials whose term lives in the active
    # semester so the panel doesn't dump every historical term at once.
    # Dropdown options: "Active semester" (default), "All terms", or a
    # specific term. available_terms is restricted to terms that
    # actually have materials in this subject so the list stays short.
    active_semester = Semester.current()
    requested_term = request.GET.get('term', '').strip()
    available_terms = list(
        Term.objects
        .filter(
            id__in=Module.objects
            .filter(subject_id=id, term__isnull=False)
            .values_list('term_id', flat=True),
        )
        .select_related('semester')
        .order_by('-semester__start_date', 'term_name')
        .distinct()
    )

    if requested_term == 'all':
        selected_term = 'all'
    elif requested_term.isdigit() and any(t.id == int(requested_term) for t in available_terms):
        selected_term = int(requested_term)
    elif active_semester:
        selected_term = 'active'
    else:
        selected_term = 'all'

    if selected_term == 'active' and active_semester:
        modules = modules.filter(term__semester_id=active_semester.id)
    elif selected_term not in ('all', 'active'):
        modules = modules.filter(term_id=selected_term)

    sort_by = request.GET.get('sort', '-id')
    valid_sorts = ['file_name', '-file_name', 'start_date', '-start_date', 'end_date', '-end_date', 'term__term_name', '-term__term_name', '-id']
    if sort_by not in valid_sorts:
        sort_by = '-id'
    modules = modules.order_by(sort_by)

    items_per_page = request.GET.get('per_page', '10')
    try:
        items_per_page = int(items_per_page)
        if items_per_page not in [5, 10, 25, 50]:
            items_per_page = 10
    except (ValueError, TypeError):
        items_per_page = 10

    paginator = Paginator(modules, items_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    template = 'student/material-list.html' if is_student else 'material/material-list.html'

    # Attach the related activities (via additional_modules M2M reverse) to
    # each lesson on the current page so the template can render them as
    # children. We exclude Participation (rarely answered explicitly), and
    # for students respect remedial gating + completed-flag for marking
    # already-done items.
    completed_activity_ids = set()
    if is_student:
        # An activity is "completed" only when the attempt has actually ended —
        # i.e., StudentActivity.end_time is in the past. (On start of a timed
        # attempt end_time is set to start + duration; on submit it's set to
        # timezone.now(). Either way, `end_time < now` ⇒ finished.)
        completed_activity_ids = set(
            StudentActivity.objects.filter(
                student=request.user,
                end_time__lt=timezone.now(),
            ).values_list('activity_id', flat=True)
        )

    # Skip per-lesson activity hydration on the assessments tab — the
    # template doesn't render lesson_activities there. Students never see
    # lesson-anchored activities under each lesson regardless of tab.
    if not is_student and active_view == 'lessons':
        for lesson in page_obj:
            lesson_activities = getattr(lesson, '_prefetched_lesson_activities', None)
            if lesson_activities is None:
                # Defensive fallback in case the prefetch was bypassed
                # (e.g. cached queryset). Should not happen on the happy path.
                lesson_activities = list(
                    lesson.additional_activities.filter(status=True)
                    .exclude(activity_type__name__iexact='Participation')
                    .select_related('activity_type', 'subject')
                    .order_by('end_time', 'local_id')
                )
            for a in lesson_activities:
                a.is_completed = a.id in completed_activity_ids
            lesson.lesson_activities = lesson_activities
    else:
        for lesson in page_obj:
            lesson.lesson_activities = []

    now = timezone.now()
    subject_progress_pct = 0
    completed_count = 0
    total_activities = 0
    next_lesson = None
    if is_student and subject:
        base_qs = Activity.objects.filter(subject=subject, status=True).filter(
            Q(remedial=False) | Q(remedial_students=request.user)
        ).exclude(activity_type__name__iexact='Participation').distinct()
        total_activities = base_qs.count()
        completed_count = len(completed_activity_ids & set(base_qs.values_list('local_id', flat=True)))
        if total_activities:
            subject_progress_pct = int(round(completed_count * 100.0 / total_activities))

        # Next not-yet-opened lesson (for "Continue Learning" hint)
        next_lesson = (
            Module.objects.filter(subject=subject)
            .filter(Q(start_date__isnull=True) | Q(start_date__lte=now))
            .order_by('-id')
            .first()
        )

    # Student sidebar: Due Soon (next 3 days) + To Do (everything else open) —
    # scoped to this subject only.
    due_activities = []
    todo_activities = []
    if is_student and subject:
        soon_cutoff = now + timedelta(days=3)
        subject_base_qs = (
            Activity.objects
            .filter(subject=subject, status=True)
            .filter(Q(remedial=False) | Q(remedial_students=request.user))
            .exclude(activity_type__name__iexact='Participation')
            .select_related('activity_type', 'subject')
            .distinct()
        )
        # Due Soon: end_time falls within the next 3 days, not yet submitted.
        # We deliberately do NOT gate on start_time — a student needs to see
        # something due in 2 days even if it hasn't opened yet.
        due_activities = list(
            subject_base_qs.filter(
                end_time__gte=now,
                end_time__lte=soon_cutoff,
            ).exclude(local_id__in=completed_activity_ids)
            .order_by('end_time')
        )
        due_ids = {a.local_id for a in due_activities}
        # To Do: open now AND still actionable — i.e., deadline is in the future
        # (or the activity has no deadline). Past-due activities are excluded
        # here regardless of submission status; they're considered "done" from
        # the sidebar's perspective.
        todo_activities = list(
            subject_base_qs.filter(
                Q(start_time__isnull=True) | Q(start_time__lte=now)
            ).filter(
                Q(end_time__isnull=True) | Q(end_time__gte=now)
            ).exclude(local_id__in=completed_activity_ids)
            .exclude(local_id__in=due_ids)
            .order_by('end_time', '-local_id')
        )

    # Sidebar Classmates preview — count of other enrolled students in this
    # subject for the viewer's current semester, plus the first 3 for the
    # avatar stack.
    classmates_count = 0
    classmates_preview = []
    if is_student and subject:
        viewer_enrollment = (
            SubjectEnrollment.objects
            .filter(subject=subject, student=request.user, status='enrolled')
            .order_by('-enrollment_date')
            .first()
        )
        if viewer_enrollment and viewer_enrollment.semester_id:
            classmates_qs = (
                SubjectEnrollment.objects
                .filter(
                    subject=subject,
                    semester_id=viewer_enrollment.semester_id,
                    status='enrolled',
                    student__isnull=False,
                )
                .exclude(student=request.user)
                .select_related('student', 'student__profile')
                .order_by('student__last_name', 'student__first_name')
            )
            classmates_count = classmates_qs.count()
            classmates_preview = [e.student for e in classmates_qs[:3]]

    # Student "Assessments" tab — per-subject status breakdown.
    assessment_items = []
    assessment_counts = {}
    if is_student and subject:
        assessment_activities = (
            Activity.objects
            .filter(subject=subject, status=True)
            .exclude(activity_type__name__iexact='Participation')
            .select_related('subject', 'term', 'activity_type')
            .order_by('end_time', 'start_time')
            .order_by('-pk')
        )
        # "Submitted" only counts when the student actually went through
        # SubmitAnswersView (which bumps retake_count). A bare StudentActivity
        # row may be created on first open, so existence alone isn't enough.
        submitted_map = {
            sa.activity_id: sa
            for sa in StudentActivity.objects.filter(
                student=request.user,
                activity__in=assessment_activities,
                retake_count__gte=1,
            )
        }
        one_week = now + timedelta(days=7)
        for a in assessment_activities:
            sa = submitted_map.get(a.local_id)
            is_submitted = sa is not None
            score = sa.total_score if sa else None
            late_window_end = a.end_time
            if a.end_time and a.allow_late_submission and a.late_submission_days:
                late_window_end = a.end_time + timedelta(days=a.late_submission_days)

            if is_submitted:
                opened_late = bool(a.end_time and sa.start_time and sa.start_time > a.end_time)
                if a.show_score and score is not None and score > 0:
                    status_tag = 'graded'
                elif opened_late:
                    status_tag = 'submitted_late'
                else:
                    status_tag = 'submitted'
            elif a.end_time and a.end_time < now and late_window_end and now <= late_window_end:
                status_tag = 'late_open'
            elif late_window_end and late_window_end < now:
                status_tag = 'missed'
            elif a.start_time and a.start_time > now:
                status_tag = 'upcoming'
            elif a.end_time and a.end_time <= one_week:
                status_tag = 'due_soon'
            else:
                status_tag = 'open'

            assessment_items.append({
                'activity': a,
                'status': status_tag,
                'is_submitted': is_submitted,
                'score': score,
                'late_window_end': late_window_end,
            })

        assessment_counts = {
            'all': len(assessment_items),
            'due_soon': sum(1 for i in assessment_items if i['status'] == 'due_soon'),
            'open': sum(1 for i in assessment_items if i['status'] == 'open'),
            'upcoming': sum(1 for i in assessment_items if i['status'] == 'upcoming'),
            'late_open': sum(1 for i in assessment_items if i['status'] == 'late_open'),
            'missed': sum(1 for i in assessment_items if i['status'] == 'missed'),
            'submitted': sum(
                1 for i in assessment_items
                if i['status'] in ('submitted', 'submitted_late', 'graded')
            ),
        }

    # Teacher sidebar — per-subject quick stats + grading-needed surface.
    teacher_stats = {}
    needs_grading = []
    if not is_student and subject:
        enrolled_count = SubjectEnrollment.objects.filter(
            subject=subject, status='enrolled',
        ).count()
        teacher_stats = {
            'enrolled': enrolled_count,
            'materials': page_obj.paginator.count if hasattr(page_obj, 'paginator') else 0,
        }
        # Activities with at least one submission that hasn't been scored yet
        # (total_score is None) — these are what the teacher should grade next.
        ungraded_qs = (
            StudentActivity.objects
            .filter(
                subject=subject,
                retake_count__gte=1,
                total_score__isnull=True,
            )
            .exclude(activity__activity_type__name__iexact='Participation')
            .select_related('activity', 'student', 'activity__activity_type')
            .order_by('-end_time')[:5]
        )
        needs_grading = list(ungraded_qs)
        teacher_stats['ungraded'] = (
            StudentActivity.objects
            .filter(subject=subject, retake_count__gte=1, total_score__isnull=True)
            .exclude(activity__activity_type__name__iexact='Participation')
            .count()
        )

    # Teacher "Assessments" tab — per-subject list with management-facing
    # status (open/upcoming/closed/draft) + submission counts. Separate
    # from the student tab so the data shape matches teacher actions
    # (no per-viewer score, but yes per-activity submission totals).
    if not is_student and subject:
        if active_view == 'assessments':
            teacher_activities = list(
                Activity.objects
                .filter(subject=subject)
                .exclude(activity_type__name__iexact='Participation')
                .select_related('subject', 'term', 'activity_type')
                .order_by('-pk')
            )
            # Count actually-submitted attempts per activity (retake_count >= 1).
            # `StudentActivity.pk` resolves to whatever the model's PK is (the
            # model uses `local_id` as its primary key, not `id`), so we
            # aggregate over `pk` to stay model-agnostic.
            activity_local_ids = [a.local_id for a in teacher_activities]
            submitted_counts = dict(
                StudentActivity.objects
                .filter(activity_id__in=activity_local_ids, retake_count__gte=1)
                .values('activity_id')
                .annotate(c=Count('pk'))
                .values_list('activity_id', 'c')
            )
            for a in teacher_activities:
                sub_count = submitted_counts.get(a.local_id, 0)
                if not a.status:
                    status_tag = 'draft'
                elif a.start_time and a.start_time > now:
                    status_tag = 'upcoming'
                elif a.end_time and a.end_time < now:
                    status_tag = 'closed'
                else:
                    status_tag = 'open'
                assessment_items.append({
                    'activity': a,
                    'status': status_tag,
                    'submitted_count': sub_count,
                })
            assessment_counts = {
                'all': len(assessment_items),
                'open': sum(1 for i in assessment_items if i['status'] == 'open'),
                'upcoming': sum(1 for i in assessment_items if i['status'] == 'upcoming'),
                'closed': sum(1 for i in assessment_items if i['status'] == 'closed'),
                'draft': sum(1 for i in assessment_items if i['status'] == 'draft'),
            }
        else:
            # Lessons view only needs aggregate totals for the tab badges —
            # skip the per-activity status loop and submission counts.
            base_qs = (
                Activity.objects
                .filter(subject=subject)
                .exclude(activity_type__name__iexact='Participation')
            )
            total_assessments = base_qs.count()
            open_count = base_qs.filter(
                status=True,
            ).filter(
                Q(start_time__isnull=True) | Q(start_time__lte=now)
            ).filter(
                Q(end_time__isnull=True) | Q(end_time__gte=now)
            ).count()
            assessment_counts = {
                'all': total_assessments,
                'open': open_count,
            }
        # Now that we know the totals, surface them in teacher_stats too.
        teacher_stats['assessments'] = assessment_counts.get('all', 0)
        teacher_stats['open_assessments'] = assessment_counts.get('open', 0)

    # Enrolled students roster for the teacher sidebar (active enrollments,
    # most-recent semester present on the subject).
    enrolled_students = []
    enrolled_students_count = 0
    if not is_student and subject:
        roster_qs = (
            SubjectEnrollment.objects
            .filter(subject=subject, status='enrolled', student__isnull=False)
            .select_related('student', 'student__profile')
            .order_by('student__last_name', 'student__first_name')
        )
        enrolled_students_count = roster_qs.count()
        enrolled_students = [e.student for e in roster_qs[:200]]

    # Activity types for the "New assessment" dropdown on the teacher
    # assessments tab — matches the picker on /assessment-list/.
    # "Participation" is the canonical name for "Major Assessment" (see
    # activity/migrations/0004_relabel_participation_to_major_assessment.py);
    # only Attendance is hidden from the assessment picker.
    assessment_activity_types = []
    if not is_student and subject and active_view == 'assessments':
        assessment_activity_types = list(
            ActivityType.objects.exclude(name__iexact='Attendance')
            .order_by('name')
        )

    # Material rename (clickable lesson name) is restricted to the teacher
    # actually assigned to this subject — admins / deans / other teachers
    # shouldn't be able to edit a lesson title that doesn't belong to them.
    # Active substitute counts as the teacher; subject.active_teacher returns
    # the substitute when one is allowed/assigned, else the primary teacher.
    _active_teacher = subject.active_teacher if subject is not None else None
    can_edit_material = (
        request.user.is_authenticated
        and not is_student
        and _active_teacher is not None
        and _active_teacher.pk == request.user.pk
    )

    return render(request, template, {
        'page_obj': page_obj,
        'subject': subject,
        'subject_id': id,
        'search_query': search_query,
        'sort_by': sort_by,
        'items_per_page': items_per_page,
        'available_terms': available_terms,
        'selected_term': selected_term,
        'active_semester': active_semester,
        'is_student_role': is_student,
        'can_edit_material': can_edit_material,
        'now': now,
        'subject_progress_pct': subject_progress_pct,
        'subject_completed_count': completed_count,
        'subject_total_activities': total_activities,
        'next_lesson': next_lesson,
        'due_activities': due_activities,
        'todo_activities': todo_activities,
        'assessment_items': assessment_items,
        'assessment_counts': assessment_counts,
        'active_view': active_view,
        'classmates_count': classmates_count,
        'classmates_preview': classmates_preview,
        'teacher_stats': teacher_stats,
        'needs_grading': needs_grading,
        'assessment_activity_types': assessment_activity_types,
        'enrolled_students': enrolled_students,
        'enrolled_students_count': enrolled_students_count,
        'back_url_name': subject_list_url_name(subject),
    })

@login_required
@permission_required('module.view_module', raise_exception=True)
def material_list_cm(request, id):
    # Same subject-level gate as the regular material_list view — Classroom
    # Mode shouldn't be reachable by teachers not assigned to the subject.
    subject_for_auth = get_object_or_404(Subject, pk=id)
    has_access, redirect_response = check_subject_access(request, subject_for_auth)
    if not has_access:
        return redirect_response

    modules = Module.objects.filter(subject_id=id).select_related('subject', 'term')
    subject = modules.first().subject if modules.exists() else None
    
    search_query = request.GET.get('search', '').strip()
    if search_query:
        modules = modules.filter(
            Q(file_name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(term__term_name__icontains=search_query)
        )
    
    sort_by = request.GET.get('sort', '-id')
    valid_sorts = ['file_name', '-file_name', 'start_date', '-start_date', 'end_date', '-end_date', 'term__term_name', '-term__term_name', '-id']
    if sort_by not in valid_sorts:
        sort_by = '-id'
    modules = modules.order_by(sort_by)
    
    items_per_page = request.GET.get('per_page', '10')
    try:
        items_per_page = int(items_per_page)
        if items_per_page not in [5, 10, 25, 50]:
            items_per_page = 10
    except (ValueError, TypeError):
        items_per_page = 10
    
    paginator = Paginator(modules, items_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'module/material-list-cm.html', {
        'page_obj': page_obj,
        'subject': subject,
        'subject_id': id,
        'search_query': search_query,
        'sort_by': sort_by,
        'items_per_page': items_per_page,
    })


@login_required
@permission_required('module.add_module', raise_exception=True)
def file_validation_data(request):
    validation_data = {
        'allowed_extensions': [
            'pdf', 'jpg', 'jpeg', 'png',
            'mp4', 'avi', 'mov', 'wmv',
            'ppt', 'pptx', 'doc', 'docx', 'xls', 'xlsx',
        ],
        'max_file_size_mb': 30
    }
    return JsonResponse(validation_data)
