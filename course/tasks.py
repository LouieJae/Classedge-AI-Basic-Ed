import re
from collections import defaultdict
from datetime import timedelta

from celery import shared_task
from celery.utils.log import get_task_logger
from django.db import transaction
from django.db.models import F, Count
from django.core.mail import send_mass_mail
from django.conf import settings
from django.utils import timezone

logger = get_task_logger(__name__)


@shared_task
def mark_absent_for_ended_classes():
    """
    Every 5 min: create Absent rows for students who did not self-mark
    in any schedule whose end_time just passed (within a 10-min look-back)
    on today's weekday, where the subject has self_attendance_enabled.
    """
    from subject.models import Schedule
    from course.models import Attendance, AttendanceStatus, SubjectEnrollment

    now = timezone.localtime()
    today = now.date()
    today_abbr = now.strftime("%a")
    window_start_time = (now - timedelta(minutes=10)).time()

    absent_status = AttendanceStatus.objects.filter(status="Absent").first()
    if absent_status is None:
        return {"status": "no_absent_status_configured"}

    schedules = (
        Schedule.objects
        .filter(
            subject__self_attendance_enabled=True,
            is_active_semester=True,
            schedule_end_time__lte=now.time(),
            schedule_end_time__gte=window_start_time,
        )
        .select_related("subject", "subject__assign_teacher")
    )

    created_total = 0
    for schedule in schedules:
        if today_abbr not in schedule.days_of_week:
            continue
        subject = schedule.subject

        enrolled_student_ids = list(
            SubjectEnrollment.objects
            .filter(subject=subject, status="enrolled", student__isnull=False)
            .values_list("student_id", flat=True)
        )
        if not enrolled_student_ids:
            continue

        already_marked_ids = set(
            Attendance.objects
            .filter(subject=subject, date=today, student_id__in=enrolled_student_ids)
            .values_list("student_id", flat=True)
        )

        to_create = [
            Attendance(
                student_id=sid,
                subject=subject,
                schedule=schedule,
                date=today,
                status=absent_status,
                teacher=subject.assign_teacher,
                marked_at=None,
                self_marked=False,
                graded=True,
            )
            for sid in enrolled_student_ids if sid not in already_marked_ids
        ]
        if to_create:
            Attendance.objects.bulk_create(to_create, ignore_conflicts=True)
            created_total += len(to_create)

    return {"status": "ok", "created": created_total}


@shared_task(bind=True, max_retries=3)
def process_enrollment_import(self, csv_data, user_id):
    """
    Process CSV enrollment import asynchronously.
    
    Args:
        csv_data: List of dictionaries containing CSV row data
        user_id: ID of the user who initiated the import (for logging)
    """
    logger.info(
        "Enrollment import started: task=%s user=%s rows=%s retries=%s",
        self.request.id, user_id, len(csv_data), self.request.retries,
    )

    try:
        from course.models import SubjectEnrollment, Semester
        from accounts.models import Profile, Course, CustomUser, StudentSDG
        from subject.models import Subject
        from roles.models import Role
        from course.utils.utils import _parse_subject_tokens, _norm_name

        logger.debug("Initializing caches and processing data")
        
        # Caches
        subject_by_id_cache = {}
        subject_by_name_cache = {}
        semester_cache = {}
        course_cache = {}
        
        role, _ = Role.objects.get_or_create(name='Student')
        
        def parse_semester_name_and_year(semester_full_name: str):
            s = (semester_full_name or '').strip()
            m = re.match(r'^(.*\S)\s+(\d{4})$', s)
            if not m:
                return None, None
            return m.group(1), int(m.group(2))
        
        def get_semester(semester_full_name: str):
            sem_name, year = parse_semester_name_and_year(semester_full_name)
            if not sem_name or not year:
                return None
            key = f"{sem_name}_{year}"
            if key in semester_cache:
                return semester_cache[key]
            sem = (
                Semester.objects.filter(semester_name=sem_name, start_date__year=year).first()
                or Semester.objects.filter(semester_name=sem_name, end_date__year=year).first()
            )
            if sem:
                semester_cache[key] = sem
            else:
                return None
            return sem
        
        def get_course(course_name: str):
            if not course_name:
                return None
            norm = _norm_name(course_name)
            if norm in course_cache:
                return course_cache[norm]
            course = Course.objects.filter(name__iexact=course_name.strip()).first()
            if course:
                course_cache[norm] = course
            return course
        
        def get_subject_by_id(sid: int):
            if sid in subject_by_id_cache:
                return subject_by_id_cache[sid]
            subj = Subject.objects.filter(id=sid).first()
            subject_by_id_cache[sid] = subj
            return subj
        
        def get_subject_by_name(name: str):
            norm = _norm_name(name)
            if norm in subject_by_name_cache:
                return subject_by_name_cache[norm]
            
            parts = [re.escape(p) for p in (name or '').split()]
            if parts:
                pattern = r'^' + r'\s+'.join(parts) + r'$'
                qs = Subject.objects.filter(subject_name__iregex=pattern)
            else:
                qs = Subject.objects.none()
            
            if not qs.exists():
                subj = Subject.objects.filter(subject_code__iexact=(name or '').strip()).first()
                subject_by_name_cache[norm] = subj
                return subj
            
            subj = qs.first()
            subject_by_name_cache[norm] = subj
            return subj
        
        def resolve_subjects_from_row(row):
            raw_cell = (
                row.get('Subject ID')
                or row.get('Subject IDs')
                or row.get('Subjects')
                or row.get('Subject Names')
                or row.get('Subject Name')
                or ''
            )
            ids, names = _parse_subject_tokens(raw_cell)
            
            found, seen_ids = [], set()
            
            for sid in ids:
                subj = get_subject_by_id(sid)
                if subj and subj.id not in seen_ids:
                    found.append(subj)
                    seen_ids.add(subj.id)
            
            for nm in names:
                subj = get_subject_by_name(nm)
                if subj and subj.id not in seen_ids:
                    found.append(subj)
                    seen_ids.add(subj.id)
            
            return found
        
        def get_or_create_user_profile(email, first_name, last_name, identification, course):
            user, user_created = CustomUser.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.replace('@', '_').replace('.', '_'),
                    'first_name': first_name,
                    'last_name': last_name,
                }
            )
            
            profile, profile_created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'role': role,
                    'id_number': identification,
                    'course': course,
                    'first_name': first_name,
                    'last_name': last_name,
                }
            )
            if not profile_created:
                updated = []
                if first_name and profile.first_name != first_name:
                    profile.first_name = first_name
                    updated.append('first_name')
                if last_name and profile.last_name != last_name:
                    profile.last_name = last_name
                    updated.append('last_name')
                if profile.role != role:
                    profile.role = role
                    updated.append('role')
                if identification and profile.id_number != identification:
                    profile.id_number = identification
                    updated.append('id_number')
                if course and profile.course != course:
                    profile.course = course
                    updated.append('course')
                if updated:
                    profile.save(update_fields=updated)
            return user, profile
        
        success, partial, skipped = 0, 0, 0
        errors = []
        
        with transaction.atomic():
            for row_num, row in enumerate(csv_data, start=2):
                try:
                    email = (row.get('Email') or '').strip().lower()
                    last_name = (row.get('Last Name') or '').strip()
                    first_name = (row.get('First Name') or '').strip()
                    id_number = (row.get('Identification') or '').strip()
                    semester_full_name = (row.get('Semester') or '').strip()
                    course_name = (row.get('Course') or '').strip()
                    
                    if not email:
                        errors.append(f"Row {row_num}: Missing Email")
                        skipped += 1
                        continue
                    if not semester_full_name:
                        errors.append(f"Row {row_num}: Missing Semester for {email}")
                        skipped += 1
                        continue
                    
                    semester = get_semester(semester_full_name)
                    if not semester:
                        errors.append(f"Row {row_num}: Semester '{semester_full_name}' not found for {email}")
                        skipped += 1
                        continue
                    
                    course = get_course(course_name)
                    
                    user, _profile = get_or_create_user_profile(
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        identification=id_number,
                        course=course
                    )
                    
                    subjects = resolve_subjects_from_row(row)
                    if not subjects:
                        errors.append(f"Row {row_num}: No valid subjects found for {email}")
                        skipped += 1
                        continue
                    
                    created_any = False
                    
                    for subj in subjects:
                        real_exists = SubjectEnrollment.objects.filter(
                            student=user,
                            subject=subj,
                            semester=semester
                        ).exists()
                        if real_exists:
                            continue
                        
                        placeholder = (
                            SubjectEnrollment.objects
                            .select_for_update()
                            .filter(student__isnull=True, subject=subj, semester=semester)
                            .first()
                        )
                        
                        if placeholder:
                            placeholder.student = user
                            placeholder.save(update_fields=['student'])
                            created_any = True
                            continue
                        
                        se, created = SubjectEnrollment.objects.get_or_create(
                            student=user,
                            subject=subj,
                            semester=semester,
                            defaults={'status': 'enrolled'}
                        )
                        if created:
                            created_any = True
                            
                            for sdg in subj.target_sdgs.all():
                                obj, created_sdg = StudentSDG.objects.get_or_create(
                                    student=user,
                                    sdg=sdg,
                                    defaults={'count': 1}
                                )
                                if not created_sdg:
                                    StudentSDG.objects.filter(student=user, sdg=sdg).update(count=F('count') + 1)
                    
                    if created_any:
                        success += 1
                    else:
                        partial += 1
                
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                    skipped += 1
                    continue
        
        logger.info(
            "Enrollment import completed: success=%s partial=%s skipped=%s errors=%s",
            success, partial, skipped, len(errors),
        )
        if errors:
            for err in errors[:10]:
                logger.warning("Enrollment import error: %s", err)

        return {
            "status": "success",
            "success": success,
            "partial": partial,
            "skipped": skipped,
            "errors": errors[:50]
        }

    except Exception as exc:
        logger.exception("Error in enrollment import")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def process_manual_enrollment(self, student_profile_ids, subject_ids, semester_id, user_id):
    """
    Process manual enrollment asynchronously.
    
    Args:
        student_profile_ids: List of profile IDs to enroll
        subject_ids: List of subject IDs
        semester_id: Semester ID
        user_id: ID of the user who initiated the enrollment
    """
    logger.info(
        "Manual enrollment started: task=%s user=%s students=%s subjects=%s semester=%s retries=%s",
        self.request.id, user_id, len(student_profile_ids), len(subject_ids),
        semester_id, self.request.retries,
    )

    try:
        from course.models import SubjectEnrollment, Semester
        from accounts.models import CustomUser, StudentSDG
        from subject.models import Subject

        logger.debug("Fetching semester, students, and subjects")
        
        semester = Semester.objects.get(id=semester_id)
        
        # Load students & subjects in bulk
        students = list(
            CustomUser.objects
            .filter(profile__id__in=student_profile_ids)
            .select_related('profile')
            .only('id', 'first_name', 'last_name', 'email', 'profile__id', 'profile__role')
        )
        subjects = list(
            Subject.objects
            .filter(id__in=subject_ids)
            .prefetch_related('target_sdgs')
            .only('id', 'subject_name', 'is_coil', 'is_hali', 'max_number_of_enrollees', 'number_of_enrollees')
        )
        
        student_ids = [s.id for s in students]
        subject_pk_list = [s.id for s in subjects]
        
        # Handle placeholder creation if no students
        if not student_profile_ids:
            existing_placeholders = set(
                SubjectEnrollment.objects
                .filter(student__isnull=True, subject_id__in=subject_pk_list, semester=semester)
                .values_list('subject_id', flat=True)
            )
            
            to_create_placeholders = [
                SubjectEnrollment(subject_id=sub_id, semester=semester)
                for sub_id in subject_pk_list
                if sub_id not in existing_placeholders
            ]
            
            if to_create_placeholders:
                SubjectEnrollment.objects.bulk_create(
                    to_create_placeholders,
                    batch_size=500,
                    ignore_conflicts=True
                )
                logger.info("Created %s enrollment placeholders", len(to_create_placeholders))
            
            return {
                "status": "success",
                "placeholders_created": len(to_create_placeholders),
                "enrollments_created": 0
            }
        
        # Existing enrollments
        existing_pairs = set(
            SubjectEnrollment.objects
            .filter(
                student__isnull=False,
                student_id__in=student_ids,
                subject_id__in=subject_pk_list,
                semester=semester
            )
            .values_list('student_id', 'subject_id')
        )
        
        # Prior enrollments for retake flags
        prior_pairs = set(
            SubjectEnrollment.objects
            .filter(
                student__isnull=False,
                student_id__in=student_ids,
                subject_id__in=subject_pk_list
            )
            .exclude(semester=semester)
            .values_list('student_id', 'subject_id')
        )
        
        # Capacity check
        subject_by_id = {s.id: s for s in subjects}
        capacity_needed_ids = [sid for sid, s in subject_by_id.items() if (s.is_coil or s.is_hali) and s.max_number_of_enrollees]
        
        current_counts = defaultdict(int)
        if capacity_needed_ids:
            for row in (
                SubjectEnrollment.objects
                .filter(
                    subject_id__in=capacity_needed_ids,
                    status='enrolled',
                    student__isnull=False
                )
                .values('subject_id')
                .annotate(n=Count('student', distinct=True))
            ):
                current_counts[row['subject_id']] = row['n']
        
        full_subject_ids = {
            sid for sid in capacity_needed_ids
            if current_counts[sid] >= (subject_by_id[sid].max_number_of_enrollees or 0)
        }
        
        # Build enrollment list
        to_create = []
        enrollment_data = []
        duplicates_count = 0
        full_count = 0
        retakes_count = 0
        
        with transaction.atomic():
            for stu in students:
                for sub in subjects:
                    pair = (stu.id, sub.id)
                    
                    if pair in existing_pairs:
                        duplicates_count += 1
                        continue
                    
                    if sub.id in full_subject_ids:
                        full_count += 1
                        continue
                    
                    to_create.append(SubjectEnrollment(
                        student_id=stu.id,
                        subject_id=sub.id,
                        semester=semester,
                        status='enrolled'
                    ))
                    enrollment_data.append((stu, sub, semester))
                    
                    if pair in prior_pairs:
                        retakes_count += 1
            
            # Bulk create
            created_enrollments = []
            if to_create:
                created_enrollments = SubjectEnrollment.objects.bulk_create(
                    to_create,
                    batch_size=1000,
                    ignore_conflicts=True
                )
            
            # Update SDG counts
            if created_enrollments:
                student_sdg_updates = defaultdict(lambda: defaultdict(int))
                
                subject_sdgs = {
                    s.id: list(s.target_sdgs.values_list('id', flat=True))
                    for s in subjects
                }
                
                for enrollment in created_enrollments:
                    sdg_ids = subject_sdgs.get(enrollment.subject_id, [])
                    for sdg_id in sdg_ids:
                        student_sdg_updates[enrollment.student_id][sdg_id] += 1
                
                for student_id, sdg_map in student_sdg_updates.items():
                    for sdg_id, increment in sdg_map.items():
                        obj, created = StudentSDG.objects.get_or_create(
                            student_id=student_id,
                            sdg_id=sdg_id,
                            defaults={'count': increment}
                        )
                        if not created:
                            StudentSDG.objects.filter(pk=obj.pk).update(count=F('count') + increment)
            
            # Update enrollee counts for COIL/HALI
            if capacity_needed_ids and enrollment_data:
                touched_subject_ids = {sub.id for _, sub, _ in enrollment_data}
                recalc_ids = list(set(touched_subject_ids) & set(capacity_needed_ids))
                
                if recalc_ids:
                    fresh_counts = defaultdict(int)
                    for row in (
                        SubjectEnrollment.objects
                        .filter(
                            subject_id__in=recalc_ids,
                            status='enrolled',
                            student__isnull=False
                        )
                        .values('subject_id')
                        .annotate(n=Count('student', distinct=True))
                    ):
                        fresh_counts[row['subject_id']] = row['n']
                    
                    dirty_subjects = []
                    for sid in recalc_ids:
                        subj = subject_by_id[sid]
                        new_count = fresh_counts.get(sid, 0)
                        if subj.number_of_enrollees != new_count:
                            subj.number_of_enrollees = new_count
                            dirty_subjects.append(subj)
                    
                    if dirty_subjects:
                        Subject.objects.bulk_update(dirty_subjects, ['number_of_enrollees'], batch_size=500)
        
        # Send emails after commit
        if enrollment_data:
            email_messages = []
            for stu, sub, sem in enrollment_data:
                subject_text = "LMS Enrollment Confirmation"
                body = (
                    f"Hi {stu.get_full_name()},\n\n"
                    f"You have been enrolled in:\n"
                    f"Subject: {sub.subject_name}\n"
                    f"Semester: {sem.semester_name}\n\n"
                    f"Access the LMS here: https://classedge.hccci.edu.ph/\n\n"
                    f"If you have any questions, please contact your instructor.\n\n"
                    f"Best,\nLMS Team"
                )
                email_messages.append((subject_text, body, settings.DEFAULT_FROM_EMAIL, [stu.email]))
            
            try:
                send_mass_mail(email_messages, fail_silently=False)
                logger.info("Sent %s enrollment emails", len(email_messages))
            except Exception:
                logger.exception("Failed to send enrollment emails")

        logger.info(
            "Manual enrollment completed: created=%s duplicates=%s full=%s retakes=%s",
            len(created_enrollments), duplicates_count, full_count, retakes_count,
        )

        return {
            "status": "success",
            "enrollments_created": len(created_enrollments),
            "duplicates": duplicates_count,
            "full_subjects": full_count,
            "retakes": retakes_count
        }

    except Exception as exc:
        logger.exception("Error in manual enrollment")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))