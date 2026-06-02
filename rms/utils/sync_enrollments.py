from datetime import datetime
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from accounts.models import CustomUser, Profile
from course.models import Semester, SubjectEnrollment
from subject.models import Subject
from accounts.utils.signal_utils import _thread_locals
from django.utils import timezone
from accounts.models import Course
import logging

logger = logging.getLogger(__name__)


def get_course(course_name):
    """Look up a Course by name. Does NOT create one if missing.

    The Departments & Programs RMS import is the single source of truth for
    the course catalog. If a referenced course is unknown here, that's a
    signal to run that import first — silently creating thin Course rows
    from enrollment payloads hides catalog drift and produces rows with no
    department FK or short name.
    """
    if not course_name:
        return None
    course = Course.objects.filter(name=course_name).first()
    if course is None:
        logger.warning(
            "Enrollment sync: course %r not found in catalog. "
            "Run the Departments & Programs RMS import to populate it.",
            course_name,
        )
    return course


def _get_or_create_student_user(student_email, first_name, last_name):
    """Fetch existing user by email or create one with a unique username."""
    existing_user = CustomUser.objects.filter(email=student_email).first()
    if existing_user:
        updated = False
        if first_name and existing_user.first_name != first_name:
            existing_user.first_name = first_name
            updated = True
        if last_name and existing_user.last_name != last_name:
            existing_user.last_name = last_name
            updated = True
        if updated:
            existing_user.save(update_fields=["first_name", "last_name"])
        return existing_user, False

    base_username = student_email.split("@")[0]
    username = base_username
    suffix = 1

    while CustomUser.objects.filter(username=username).exists():
        username = f"{base_username}{suffix}"
        suffix += 1

    try:
        user = CustomUser.objects.create(
            email=student_email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            needs_password_setup=False,
            needs_onboarding=False,
        )
        return user, True
    except IntegrityError:
        user = CustomUser.objects.get(email=student_email)
        return user, False


def _build_subject_caches():
    """
    Build in-memory lookup caches for subjects to avoid N+1 queries.

    Returns:
        tuple: (sync_id_lookup, prefix_lookup, name_lookup)
            - sync_id_lookup: {subject_sync_id: Subject} for exact matches
            - prefix_lookup: {partial_sync_id: [Subject, ...]} for prefix matches
            - name_lookup: {(name, type, room): Subject} for name-based fallback
    """
    sync_id_lookup = {}
    prefix_lookup = {}
    name_lookup = {}

    for subj in Subject.objects.select_related('assign_teacher').all():
        if subj.subject_sync_id:
            sync_id_lookup[subj.subject_sync_id] = subj
            if '_' in subj.subject_sync_id:
                prefix = subj.subject_sync_id.rsplit('_', 1)[0]
                prefix_lookup.setdefault(prefix, []).append(subj)

        key = (subj.subject_name, subj.subject_type, subj.room_number)
        name_lookup[key] = subj

    return sync_id_lookup, prefix_lookup, name_lookup


def _find_subject(item, sync_id_lookup, prefix_lookup, name_lookup):
    """
    Resolve a subject from an API item using cached lookups.

    Resolution order:
    1. Composite sync_id  (subject_sync_id + '_' + schedule_sync_id)
    2. Exact subject_sync_id
    3. Prefix match on subject_sync_id (narrowed by teacher / type+room)
    4. Name + type + room fallback (handles missing subject_sync_id)
    5. Name-only loose fallback
    """
    subject_sync_id = (item.get('subject_sync_id') or '').strip()
    schedule_sync_id = (item.get('schedule_sync_id') or '').strip()
    subject_name = (item.get('subject_name') or '').strip()
    subject_type = (item.get('subject_type') or '').strip()
    room_number = (item.get('schedule_room') or '').strip()
    teacher_email = (item.get('teacher_email') or '').strip().lower()

    # Strategy 1: composite sync_id
    if subject_sync_id and schedule_sync_id:
        composite = f"{subject_sync_id}_{schedule_sync_id}"
        if composite in sync_id_lookup:
            return sync_id_lookup[composite]

    # Strategy 2: exact subject_sync_id
    if subject_sync_id and subject_sync_id in sync_id_lookup:
        return sync_id_lookup[subject_sync_id]

    # Strategy 3: prefix match
    if subject_sync_id and subject_sync_id in prefix_lookup:
        candidates = prefix_lookup[subject_sync_id]
        if teacher_email:
            for c in candidates:
                if c.assign_teacher and c.assign_teacher.email == teacher_email:
                    return c
        for c in candidates:
            if c.subject_type == subject_type and c.room_number == room_number:
                return c
        return candidates[0]

    # Strategy 4: name + type + room
    if subject_name:
        key = (subject_name, subject_type, room_number)
        if key in name_lookup:
            return name_lookup[key]

        # Strategy 5: name-only loose match
        for (sname, stype, sroom), subj in name_lookup.items():
            if sname == subject_name:
                return subj

    return None


def _resolve_semester():
    """Return the active semester, falling back to most recent."""
    today = timezone.now().date()
    semester = Semester.objects.filter(
        start_date__lte=today, end_date__gte=today
    ).first()
    if not semester:
        semester = Semester.objects.order_by('-start_date').first()
    return semester


def sync_enrollments_bulk(items):
    """
    Process all enrollment items in bulk for maximum performance.

    Strategy for existing data:
    - Users: get_or_create (update name if changed)
    - Enrollments: bulk_create with ignore_conflicts=True
      → existing enrollments are silently skipped, no wasted writes
    - Subjects / Semester: resolved once from pre-built caches

    Args:
        items (list): List of dicts from RMS student-schedules API

    Returns:
        dict: {created, skipped, failed, failed_items}
    """
    if not items:
        return {'created': 0, 'skipped': 0, 'failed': 0, 'failed_items': []}

    # ── 1. Pre-build subject caches (1 query instead of N) ─────────────────
    sync_id_lookup, prefix_lookup, name_lookup = _build_subject_caches()

    # ── 2. Resolve semester once ────────────────────────────────────────────
    semester_obj = _resolve_semester()
    if not semester_obj:
        return {
            'created': 0,
            'skipped': 0,
            'failed': len(items),
            'failed_items': [{'error': 'No semester found', 'count': len(items)}]
        }

    # ── 3. Collect unique emails & course names ─────────────────────────────
    email_data = {}  # email -> {first_name, last_name, course_name}
    for item in items:
        email_raw = item.get('student_school_email') or item.get('student_email') or ''
        email = email_raw.strip().lower()
        if not email:
            continue
        if email not in email_data:
            email_data[email] = {
                'first_name': (item.get('student_first_name') or '').strip(),
                'last_name': (item.get('student_last_name') or '').strip(),
                'course_name': (item.get('course_name') or '').strip(),
            }

    # ── 4. Pre-fetch existing users in one query ────────────────────────────
    user_cache = {
        u.email: u
        for u in CustomUser.objects.filter(email__in=email_data.keys())
    }

    # ── 5. Create missing users (must be one-by-one due to signals/username uniqueness) ──
    _thread_locals.creating_rms_student = True
    try:
        for email, info in email_data.items():
            if email not in user_cache:
                user, _ = _get_or_create_student_user(
                    email, info['first_name'], info['last_name']
                )
                user_cache[email] = user
            else:
                # Update name if changed
                user = user_cache[email]
                updated = False
                if info['first_name'] and user.first_name != info['first_name']:
                    user.first_name = info['first_name']
                    updated = True
                if info['last_name'] and user.last_name != info['last_name']:
                    user.last_name = info['last_name']
                    updated = True
                if updated:
                    user.save(update_fields=['first_name', 'last_name'])
    finally:
        _thread_locals.creating_rms_student = False

    # ── 6. Pre-fetch existing enrollments for this semester (avoid duplicates) ──
    existing_pairs = set(
        SubjectEnrollment.objects.filter(
            semester=semester_obj,
            student__isnull=False,
        ).values_list('student_id', 'subject_id')
    )

    # ── 7. Pre-fetch/create courses in batch ───────────────────────────────
    course_cache = {}
    unique_courses = {d['course_name'] for d in email_data.values() if d['course_name']}
    for cname in unique_courses:
        try:
            course_cache[cname] = get_course(cname)
        except Exception:
            course_cache[cname] = None

    # ── 8. Update profiles (course) in bulk ────────────────────────────────
    profiles_to_update = []
    for email, info in email_data.items():
        user = user_cache.get(email)
        if not user:
            continue
        course = course_cache.get(info['course_name'])
        try:
            profile, created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'first_name': info['first_name'],
                    'last_name': info['last_name'],
                    'course': course,
                }
            )
            if not created and profile.course != course:
                profile.course = course
                profiles_to_update.append(profile)
        except Exception:
            pass

    if profiles_to_update:
        Profile.objects.bulk_update(profiles_to_update, ['course'], batch_size=500)

    # ── 9. Resolve subjects and build enrollment list ───────────────────────
    enrollments_to_create = []
    failed_items = []
    skipped_count = 0
    seen_pairs = set()  # deduplicate within this batch

    for item in items:
        email_raw = item.get('student_school_email') or item.get('student_email') or ''
        email = email_raw.strip().lower()

        if not email:
            failed_items.append({
                'student': 'unknown',
                'subject': item.get('subject_name', 'Unknown'),
                'error': 'Missing student email',
            })
            continue

        student_user = user_cache.get(email)
        if not student_user:
            failed_items.append({
                'student': email,
                'subject': item.get('subject_name', 'Unknown'),
                'error': 'User could not be resolved',
            })
            continue

        subject_obj = _find_subject(item, sync_id_lookup, prefix_lookup, name_lookup)
        if not subject_obj:
            subject_sync_id = (item.get('subject_sync_id') or '').strip()
            subject_name = (item.get('subject_name') or 'Unknown').strip()
            failed_items.append({
                'student': email,
                'subject': subject_name,
                'error': (
                    f"Subject not found (sync_id='{subject_sync_id}', name='{subject_name}'). "
                    "Run class-schedules sync first."
                ),
            })
            continue

        pair = (student_user.id, subject_obj.id)

        # Skip already-enrolled students
        if pair in existing_pairs or pair in seen_pairs:
            skipped_count += 1
            continue

        seen_pairs.add(pair)
        enrollments_to_create.append(SubjectEnrollment(
            student=student_user,
            subject=subject_obj,
            semester=semester_obj,
            status='enrolled',
            can_view_grade=False,
        ))

    # ── 10. Bulk insert new enrollments ────────────────────────────────────
    created_count = 0
    if enrollments_to_create:
        with transaction.atomic():
            created_objs = SubjectEnrollment.objects.bulk_create(
                enrollments_to_create,
                batch_size=500,
                ignore_conflicts=True,
            )
            created_count = len(created_objs)

        # Remove placeholder (student=NULL) enrollments for subjects that now have real students
        new_subject_ids = {e.subject_id for e in enrollments_to_create}
        SubjectEnrollment.objects.filter(
            subject_id__in=new_subject_ids,
            semester=semester_obj,
            student__isnull=True,
        ).delete()

    return {
        'created': created_count,
        'skipped': skipped_count,
        'failed': len(failed_items),
        'failed_items': failed_items,
    }


@transaction.atomic
def sync_enrollment(data):
    """
    Single-record sync (kept for backward compatibility and direct calls).
    For large datasets prefer sync_enrollments_bulk().
    """
    student_school_email = data.get("student_school_email")
    if student_school_email:
        student_email = student_school_email.strip().lower()
    else:
        student_email_raw = data.get("student_email", "")
        student_email = student_email_raw.strip().lower() if student_email_raw else ""

    first_name = (data.get("student_first_name") or "").strip()
    last_name = (data.get("student_last_name") or "").strip()
    course_name_raw = data.get("course_name")
    course_name = course_name_raw.strip() if course_name_raw else ""

    if not student_email:
        raise ValidationError("Student email is required.")

    course = None
    if course_name:
        try:
            course = get_course(course_name)
        except Exception:
            course = None

    _thread_locals.creating_rms_student = True
    try:
        student_user, _ = _get_or_create_student_user(
            student_email=student_email,
            first_name=first_name,
            last_name=last_name,
        )
        profile, created_profile = Profile.objects.get_or_create(
            user=student_user,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "course": course,
            }
        )
        if not created_profile and profile.course != course:
            profile.course = course
            profile.save()
    finally:
        _thread_locals.creating_rms_student = False

    # Build per-call caches (small overhead, correctness over speed for single records)
    sync_id_lookup, prefix_lookup, name_lookup = _build_subject_caches()
    subject_obj = _find_subject(data, sync_id_lookup, prefix_lookup, name_lookup)

    if not subject_obj:
        subject_sync_id = (data.get('subject_sync_id') or '').strip()
        subject_name = (data.get('subject_name') or 'Unknown').strip()
        raise ValidationError(
            f"Subject not found (sync_id='{subject_sync_id}', name='{subject_name}'). "
            "Run class-schedules sync first."
        )

    semester_obj = _resolve_semester()
    if not semester_obj:
        raise ValidationError("No matching semester found for enrollment.")

    enrollment_obj, created_enrollment = SubjectEnrollment.objects.update_or_create(
        student=student_user,
        subject=subject_obj,
        semester=semester_obj,
        defaults={
            "status": "enrolled",
            "can_view_grade": False,
        }
    )

    if created_enrollment:
        SubjectEnrollment.objects.filter(
            subject=subject_obj,
            semester=semester_obj,
            student__isnull=True
        ).delete()

    return enrollment_obj


@transaction.atomic
def create_placeholder_enrollments_for_empty_subjects(semester=None):
    """
    Create placeholder enrollments (student=NULL) for subjects that have no enrolled students.
    This matches the behavior of EnrollStudentViewSync when no students are selected.
    
    Args:
        semester: Optional semester to check. If None, uses current semester.
    
    Returns:
        int: Number of placeholder enrollments created
    """
    # Get semester
    if not semester:
        today = timezone.now().date()
        semester = Semester.objects.filter(start_date__lte=today, end_date__gte=today).first()
        
        # Fallback to most recent semester
        if not semester:
            semester = Semester.objects.order_by('-start_date').first()
    
    if not semester:
        return 0
    
    # Get all subjects that were synced from RMS (have subject_sync_id)
    synced_subjects = Subject.objects.filter(subject_sync_id__isnull=False).exclude(subject_sync_id='')
    
    if not synced_subjects.exists():
        return 0
    
    # Find subjects with no real enrollments (student__isnull=False) in this semester
    subjects_with_students = set(
        SubjectEnrollment.objects.filter(
            subject__in=synced_subjects,
            semester=semester,
            student__isnull=False
        ).values_list('subject_id', flat=True).distinct()
    )
    
    # Find subjects that already have placeholders
    subjects_with_placeholders = set(
        SubjectEnrollment.objects.filter(
            subject__in=synced_subjects,
            semester=semester,
            student__isnull=True
        ).values_list('subject_id', flat=True).distinct()
    )
    
    # Subjects that need placeholders: synced subjects without students and without existing placeholders
    all_synced_subject_ids = set(synced_subjects.values_list('id', flat=True))
    subjects_needing_placeholders = all_synced_subject_ids - subjects_with_students - subjects_with_placeholders
    
    if not subjects_needing_placeholders:
        return 0
    
    # Create placeholders
    placeholders_to_create = [
        SubjectEnrollment(
            subject_id=subject_id,
            semester=semester,
            student=None,  # Explicitly set to NULL
            can_view_grade=True,
            status='enrolled'
        )
        for subject_id in subjects_needing_placeholders
    ]
    
    created = SubjectEnrollment.objects.bulk_create(
        placeholders_to_create,
        batch_size=500,
        ignore_conflicts=True
    )
    
    return len(created)