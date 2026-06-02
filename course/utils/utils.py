import csv
import logging
import re

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.timezone import now
from django.http import HttpResponse

from subject.models import Subject
from course.models import Semester, SubjectEnrollment
from activity.models import Activity, ActivityQuestion
from logs.models import SubjectLog

logger = logging.getLogger(__name__)

def copy_activities_from_previous_semester(subject_id, old_semester_id, new_semester_id, selected_activity_ids):
    subject = get_object_or_404(Subject, id=subject_id)
    old_semester = get_object_or_404(Semester, id=old_semester_id)
    new_semester = get_object_or_404(Semester, id=new_semester_id)

    activities = Activity.objects.filter(subject=subject, term__semester=old_semester, pk__in=selected_activity_ids).exclude(activity_type__name='Participation').exclude(remedial=True)

    logger.info("Found %s activities to copy from semester %s to %s",
                activities.count(), old_semester.semester_name, new_semester.semester_name)

    for activity in activities:
        if Activity.objects.filter(
                subject=subject,
                activity_name=activity.activity_name,
                activity_type=activity.activity_type,
                term__semester=new_semester
        ).exists():
            logger.debug("Activity '%s' already exists in target semester '%s', skipping.",
                         activity.activity_name, new_semester.semester_name)
            continue

        # Create the new activity
        new_activity = Activity.objects.create(
            activity_name=activity.activity_name,
            activity_type=activity.activity_type,
            subject=activity.subject,
            term=None,  # Empty term
            start_time=None,  # Empty start time
            end_time=None,  # Empty end time
            show_score=activity.show_score,
            remedial=False  # Don't copy the remedial flag for non-remedial activities
        )
        # Copy additional_modules relationship if exists
        if activity.additional_modules.exists():
            new_activity.additional_modules.set(activity.additional_modules.all())
        logger.debug("Created new activity: %s", new_activity.activity_name)

        # Copy associated questions for the activity
        questions = ActivityQuestion.objects.filter(activity=activity)
        for question in questions:
            new_question = ActivityQuestion.objects.create(
                activity=new_activity,
                subject=new_activity.subject,
                question_text=question.question_text,
                correct_answer=question.correct_answer,
                quiz_type=question.quiz_type,
                score=question.score
            )
            logger.debug("Copied question to %s", new_activity.activity_name)

            if question.quiz_type.name == 'Multiple Choice':
                for choice in question.choices.all():
                    new_question.choices.create(choice_text=choice.choice_text)
                logger.debug("Copied choices for question on %s", new_activity.activity_name)

        # # Associate students in the new semester with the new activity
        # students = CustomUser.objects.filter(subjectenrollment__subject=subject, profile__role__name__iexact='Student', subjectenrollment__semester=new_semester).distinct()
        # for student in students:
        #     StudentActivity.objects.create(
        #         student=student,
        #         activity=new_activity,
        #         term=None  # This can be updated later when the term is defined
        #     )
        #     print(f"Associated student {student.email} with new activity {new_activity.activity_name}")

        # Optionally log the copy
        SubjectLog.objects.create(
            subject=subject,
            message=f"Copied activity '{activity.activity_name}' from {old_semester.semester_name} to {new_semester.semester_name}."
        )
        logger.debug("Logged copy of activity: %s", activity.activity_name)

    logger.info("Finished copying activities from %s to %s",
                old_semester.semester_name, new_semester.semester_name)
    return f"Activities from {old_semester.semester_name} have been successfully copied to {new_semester.semester_name}."


def _norm_name(s: str) -> str:
    """Collapse internal whitespace and lowercase for robust matching."""
    return ' '.join((s or '').split()).lower()


# Helper: strip ONE OR MORE layers of balanced wrapping around the entire string, e.g.
# "(A, B)" -> "A, B", "[ (58, 48) ]" -> "(58, 48)"; but
_WRAP = {'(': ')', '[': ']', '{': '}'}
def _strip_balanced_wrapping(s: str) -> str:
    s = (s or '').strip()
    while len(s) >= 2 and s[0] in _WRAP and s[-1] == _WRAP[s[0]]:
        s = s[1:-1].strip()
    return s


def _split_multi(cell: str):
    """
    Split a cell that may look like:
      '58'
      '(58,48,38)'
      'Subject A, Subject B'
      '(Subject A, Subject  B)'
    Returns a list of tokens (strings), trimmed. Parentheses/brackets are only
    removed when they wrap the ENTIRE cell (balanced wrapping).
    """
    if cell is None:
        return []
    s = _strip_balanced_wrapping(str(cell))
    # split on comma/pipe/semicolon (NOT parentheses)
    tokens = [t.strip() for t in re.split(r'\s*[|;,]\s*', s) if t.strip()]
    return tokens


def _parse_subject_tokens(cell: str):
    """
    Accept a mixed list: numbers => IDs, others => names.
    Returns (id_tokens: [int], name_tokens: [str])

    IDs may be bare digits ('58') or wrapped once e.g. '(58)', '[58]', '{58}'.
    """
    ids, names = [], []
    for tok in _split_multi(cell):
        tok_str = tok.strip()
        # Allow optional single pair of wrappers around pure digits
        if re.fullmatch(r'[\(\[\{]?\s*\d+\s*[\)\]\}]?', tok_str):
            m = re.search(r'\d+', tok_str)
            if m:
                try:
                    ids.append(int(m.group(0)))
                    continue
                except ValueError:
                    pass  # fall through to names if something odd happens
        # Otherwise treat as a name token
        names.append(tok_str)
    return ids, names


def _get_bool(request, key: str, default: bool = False):
    """
    Parse boolean-ish GET params. True if value in {1, '1', 'true', 'yes', 'on'} (case-insensitive).
    """
    raw = request.GET.get(key)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


@login_required
@permission_required('course.view_subjectenrollment', raise_exception=True)
def export_students_with_subjects_csv(request):
    """
    Exports one row per student for a given semester:
    Email, First Name, Last Name, Identification, Semester, Course, Subject Names

    Query params:
      - semester_id (required)
      - status (optional; default=enrolled) => enrolled|dropped|completed|all
      - teacher_only (optional; 1/0) => if 1, include only subjects where subject.assign_teacher = request.user
    """
    semester_id = request.GET.get('semester_id')
    if not semester_id:
        return HttpResponse("Missing required parameter: semester_id", status=400)
    semester = get_object_or_404(Semester, id=semester_id)

    status = (request.GET.get('status') or 'enrolled').lower()
    teacher_only = str(request.GET.get('teacher_only', '0')).lower() in {'1', 'true', 'yes', 'on'}

    # Base: only REAL enrollments (exclude placeholders)
    qs = (
        SubjectEnrollment.objects
        .select_related(
            'semester',
            'student', 'student__profile', 'student__profile__course',
            'subject'
        )
        .filter(semester=semester, student__isnull=False)
    )

    if status in {'enrolled', 'dropped', 'completed'}:
        qs = qs.filter(status=status)
    # 'all' => no status filter

    if teacher_only:
        qs = qs.filter(subject__assign_teacher=request.user)

    # Group subjects by student
    by_student = {}  # {student_id: {"email":..., "first":..., "last":..., "ident":..., "course":..., "subjects":[...]}}

    for se in qs:
        stu = se.student
        prof = getattr(stu, 'profile', None)
        course = getattr(prof, 'course', None)

        bucket = by_student.setdefault(stu.id, {
            "email": stu.email or '',
            "first": getattr(stu, 'first_name', '') or '',
            "last": getattr(stu, 'last_name', '') or '',
            "ident": getattr(prof, 'id_number', '') if prof else '',
            "course": getattr(course, 'name', '') if course else '',
            "subjects": set(),  # use set to avoid accidental dups
        })

        subj = se.subject
        if subj:
            # prefer subject_name; fallback to subject_code
            label = (getattr(subj, 'subject_name', '') or '').strip() or (getattr(subj, 'subject_code', '') or '').strip()
            if label:
                bucket["subjects"].add(label)

    # Build semester cell with year (or range if spans two years)
    start_year = getattr(semester.start_date, 'year', None)
    end_year = getattr(semester.end_date, 'year', None)
    if start_year and end_year and start_year != end_year:
        semester_cell = f"{semester.semester_name} {start_year}-{end_year}"
    else:
        year_for_export = start_year or end_year
        semester_cell = f"{semester.semester_name} {year_for_export}" if year_for_export else semester.semester_name

    # Prepare CSV response
    ts = now().strftime('%Y%m%d_%H%M%S')
    filename = f"students_subjects_{semester.semester_name.replace(' ', '_')}_{ts}.csv"
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')  # BOM for Excel

    writer = csv.writer(response)
    writer.writerow(["Email", "First Name", "Last Name", "Identification", "Semester", "Course", "Subject Names"])

    # Stable ordering: by last, first, email
    for _, rec in sorted(by_student.items(), key=lambda kv: (kv[1]["last"].lower(), kv[1]["first"].lower(), kv[1]["email"].lower())):
        subjects_joined = ", ".join(sorted(rec["subjects"], key=str.lower))
        writer.writerow([
            rec["email"],
            rec["first"],
            rec["last"],
            rec["ident"],
            semester_cell,  
            rec["course"],
            subjects_joined,
        ])

    return response


@login_required
@permission_required('course.view_subjectenrollment', raise_exception=True)
def export_all_students_with_subjects_csv(request):
    """
    Exports all students with their subjects across all semesters:
    Email, First Name, Last Name, Identification, Semester, Course, Subject Names

    Query params:
      - status (optional; default=enrolled) => enrolled|dropped|completed|all
      - teacher_only (optional; 1/0) => if 1, include only subjects where subject.assign_teacher = request.user
    """
    status = (request.GET.get('status') or 'enrolled').lower()
    teacher_only = str(request.GET.get('teacher_only', '0')).lower() in {'1', 'true', 'yes', 'on'}

    # Base: only REAL enrollments (exclude placeholders)
    qs = (
        SubjectEnrollment.objects
        .select_related(
            'semester',
            'student', 'student__profile', 'student__profile__course',
            'subject'
        )
        .filter(student__isnull=False)
    )

    if status in {'enrolled', 'dropped', 'completed'}:
        qs = qs.filter(status=status)
    # 'all' => no status filter

    if teacher_only:
        qs = qs.filter(subject__assign_teacher=request.user)

    # Group subjects by student and semester
    by_student_semester = {}  # {(student_id, semester_name): {...}}

    for se in qs:
        stu = se.student
        prof = getattr(stu, 'profile', None)
        course = getattr(prof, 'course', None)
        
        # Build semester name with year
        sem = se.semester
        start_year = getattr(sem.start_date, 'year', None)
        end_year = getattr(sem.end_date, 'year', None)
        if start_year and end_year and start_year != end_year:
            semester_name = f"{sem.semester_name} {start_year}-{end_year}"
        else:
            year_for_export = start_year or end_year
            semester_name = f"{sem.semester_name} {year_for_export}" if year_for_export else sem.semester_name

        key = (stu.id, semester_name)
        bucket = by_student_semester.setdefault(key, {
            "email": stu.email or '',
            "first": getattr(stu, 'first_name', '') or '',
            "last": getattr(stu, 'last_name', '') or '',
            "ident": getattr(prof, 'id_number', '') if prof else '',
            "course": getattr(course, 'name', '') if course else '',
            "semester": semester_name,
            "subjects": set(),
        })

        subj = se.subject
        if subj:
            # prefer subject_name; fallback to subject_code
            label = (getattr(subj, 'subject_name', '') or '').strip() or (getattr(subj, 'subject_code', '') or '').strip()
            if label:
                bucket["subjects"].add(label)

    # Prepare CSV response
    ts = now().strftime('%Y%m%d_%H%M%S')
    filename = f"students_subjects_all_semesters_{ts}.csv"
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')  # BOM for Excel

    writer = csv.writer(response)
    writer.writerow(["Email", "First Name", "Last Name", "Identification", "Semester", "Course", "Subject Names"])

    # Stable ordering: by last, first, email, then semester
    for _, rec in sorted(by_student_semester.items(), 
                        key=lambda kv: (kv[1]["last"].lower(), 
                                      kv[1]["first"].lower(), 
                                      kv[1]["email"].lower(),
                                      kv[1]["semester"].lower())):
        subjects_joined = ", ".join(sorted(rec["subjects"], key=str.lower))
        writer.writerow([
            rec["email"],
            rec["first"],
            rec["last"],
            rec["ident"],
            rec["semester"],
            rec["course"],
            subjects_joined,
        ])

    return response
