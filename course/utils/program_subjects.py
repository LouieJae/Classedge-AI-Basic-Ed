"""Shared helpers for program-flavored subject list views (regular,
COIL, HALI, CTE). These views were near-clones; this module owns the
truly common parts so each view can be a thin wrapper around its own
queryset shape.

Public surface:
    DEPARTMENT_TO_COLLEGE, DEPARTMENT_TO_COLLEGE_NAME — department→college maps
    resolve_semester_selection(request) — semester dropdown + selected/current
    resolve_program_head_scope(profile)  — department list + college label
    annotate_subject_metrics(subjects, user, selected_semester, current_date)
    apply_program_head_search(subjects, profile, search_query)
"""

from django.db.models import Avg, Q
from django.utils import timezone

from course.models import Attendance, Semester, SubjectEnrollment


DEPARTMENT_TO_COLLEGE = {
    # College of Criminal Justice Education
    'BSCRIM': ['BSCRIM', 'BSISM'],
    'BSISM': ['BSCRIM', 'BSISM'],

    # College of Business Studies
    'BSBA': ['BSBA', 'BSOA', 'BSHM', 'BSA', 'BSE'],
    'BSOA': ['BSBA', 'BSOA', 'BSHM', 'BSA', 'BSE'],
    'BSHM': ['BSBA', 'BSOA', 'BSHM', 'BSA', 'BSE'],
    'BSA': ['BSBA', 'BSOA', 'BSHM', 'BSA', 'BSE'],
    'BSE': ['BSBA', 'BSOA', 'BSHM', 'BSA', 'BSE'],

    # College of Teacher Education
    'BTVTE': ['BTVTE', 'BECE', 'BSPharma'],
    'BECE': ['BTVTE', 'BECE', 'BSPharma'],
    'BSPharma': ['BTVTE', 'BECE', 'BSPharma'],

    # College of Computing
    'BSCS': ['BSCS', 'BSIT', 'BSIS', 'BSCE', 'ACT'],
    'BSIT': ['BSCS', 'BSIT', 'BSIS', 'BSCE', 'ACT'],
    'BSIS': ['BSCS', 'BSIT', 'BSIS', 'BSCE', 'ACT'],
    'BSCE': ['BSCS', 'BSIT', 'BSIS', 'BSCE', 'ACT'],
    'ACT': ['BSCS', 'BSIT', 'BSIS', 'BSCE', 'ACT'],

    # College of Health Sciences
    'BSP': ['BSP', 'BSN'],
    'BSN': ['BSP', 'BSN'],
}


DEPARTMENT_TO_COLLEGE_NAME = {
    'BSCRIM': 'College of Criminal Justice Education',
    'BSISM': 'College of Criminal Justice Education',

    'BSBA': 'College of Business Studies',
    'BSOA': 'College of Business Studies',
    'BSHM': 'College of Business Studies',
    'BSA': 'College of Business Studies',
    'BSE': 'College of Business Studies',

    'BTVTE': 'College of Teacher Education',
    'BECE': 'College of Teacher Education',

    'BSCS': 'College of Computing',
    'BSIT': 'College of Computing',
    'BSIS': 'College of Computing',
    'BSCE': 'College of Computing',
    'ACT': 'College of Computing',

    'BSP': 'College of Health Sciences',
    'BSN': 'College of Health Sciences',

    'Registrar': 'Administrative Department',
    'Admin': 'Administrative Department',
    'HR': 'Administrative Department',
}


PROGRAM_HEAD_SEARCH_ROLES = {'program head', 'academic dean'}


def subject_list_url_name(subject):
    """Pick the right subject-list page for ``subject``.

    Used for "Back to my courses" links and authorization-failure
    redirects so a user navigating from COIL/HALI/CTE doesn't get
    bounced into the regular subject list.
    """
    if subject is None:
        return 'course-list'
    if getattr(subject, 'is_coil', False):
        return 'coil_subjectList'
    if getattr(subject, 'is_hali', False):
        return 'hali_subjectList'
    if getattr(subject, 'is_cte', False):
        return 'cte_subject_list'
    return 'course-list'


def resolve_semester_selection(request):
    """Parse the ?semester= dropdown selection against the current semester.

    Returns (all_semesters, current_semester, selected_semester,
    selected_semester_id_str, search_query). When the GET param points at
    a missing semester, falls back to current and surfaces a warning via
    messages (callers can decide whether to honor it).
    """
    from django.contrib import messages

    semesters = Semester.objects.all()
    current_date = timezone.localtime(timezone.now()).date()
    current_semester = Semester.current()

    selected_semester_id = request.GET.get('semester', '').strip()
    if selected_semester_id.isdigit():
        selected_semester = Semester.objects.filter(id=int(selected_semester_id)).first()
        if not selected_semester:
            messages.warning(
                request,
                "The selected semester does not exist. Showing the default semester.",
            )
            selected_semester = current_semester
    else:
        selected_semester = current_semester

    return (
        semesters,
        current_semester,
        selected_semester,
        selected_semester_id,
        request.GET.get('search', '').strip(),
        current_date,
    )


def resolve_program_head_scope(profile):
    """For a program-head viewer, return (department_list, college_name).

    Returns (None, "All Subjects") when no department is assigned, so the
    caller falls back to showing every available subject.
    """
    program_head_department = profile.department_fields.name if profile.department_fields else None
    if not program_head_department:
        return None, "All Subjects"
    department_list = DEPARTMENT_TO_COLLEGE.get(
        program_head_department, [program_head_department]
    )
    college_name = DEPARTMENT_TO_COLLEGE_NAME.get(program_head_department, "My Subjects")
    return department_list, college_name


def apply_program_head_search(subjects, profile, search_query):
    """Apply the standard subject_name / teacher name / subject_code search,
    but only for program heads / academic deans (matches original behavior)."""
    if not (search_query and profile.role_name in PROGRAM_HEAD_SEARCH_ROLES):
        return subjects
    return subjects.filter(
        Q(subject_name__icontains=search_query)
        | Q(assign_teacher__first_name__icontains=search_query)
        | Q(assign_teacher__last_name__icontains=search_query)
        | Q(subject_code__icontains=search_query)
    ).distinct()


def annotate_subject_metrics(subjects, user, selected_semester, current_date):
    """Decorate each Subject in the queryset with:
        student_count, present_student_count, overall_avg_progress,
        is_online, is_classroom_mode
    Mutates the subject objects in place (preserves the template contract
    used by course/program_subject_list.html).
    """
    # Imports here to avoid a circular import at module load (course.models
    # ↔ classroom.models ↔ activity.models ↔ module.models).
    from activity.models import Activity
    from classroom.models import Classroom_mode, Teacher_Attendance
    from module.models import Module, StudentProgress

    classroom_mode_map = {
        cm.subject_id: cm.is_classroom_mode
        for cm in Classroom_mode.objects.filter(subject__in=subjects)
    }

    for subject in subjects:
        subject.student_count = SubjectEnrollment.objects.filter(
            subject=subject, semester=selected_semester
        ).count()

        subject.present_student_count = Attendance.objects.filter(
            Q(subject=subject)
            & Q(date=current_date)
            & (Q(status__status='Present') | Q(status__status='Present_Online'))
        ).count()

        modules = Module.objects.filter(subject=subject)
        activities = Activity.objects.filter(subject=subject)
        total_modules = modules.count()
        total_activities = activities.count()

        avg_module = StudentProgress.objects.filter(
            student=user, module__in=modules
        ).aggregate(avg=Avg('progress'))['avg'] or 0
        avg_activity = StudentProgress.objects.filter(
            student=user, activity__in=activities
        ).aggregate(avg=Avg('progress'))['avg'] or 0

        denom = total_modules + total_activities
        subject.overall_avg_progress = (
            (avg_module * total_modules + avg_activity * total_activities) / denom
            if denom else 0
        )

        teacher_attendance = Teacher_Attendance.objects.filter(
            subject=subject, is_active=True
        ).first()
        subject.is_online = bool(teacher_attendance)
        subject.is_classroom_mode = (
            classroom_mode_map.get(subject.id, False) and subject.is_online
        )

    return subjects
