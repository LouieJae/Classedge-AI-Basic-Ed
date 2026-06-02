from django.shortcuts import render, redirect
from course.models import SubjectEnrollment, Semester
from accounts.models import Profile, Course
from subject.models import Subject
from roles.models import Role
from accounts.models import CustomUser, StudentSDG
from course.forms import *
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from .utils import _parse_subject_tokens, _norm_name
from django.db import transaction
import re
import csv
from django.utils.timezone import now
from django.db.models import F


@login_required
@permission_required('course.add_subjectenrollment', raise_exception=True)
def import_students_and_enroll(request):
    if request.method != 'POST':
        return render(request, 'course/subjectEnrollment/import_student_and_enroll.html')

    import_file = request.FILES.get('import_file')
    if not import_file:
        messages.error(request, "No file selected. Please upload a CSV file.")
        return redirect('import_students_and_enroll')

    try:
        # Read and parse CSV file
        content = import_file.read().decode('utf-8-sig').splitlines()
        reader = csv.DictReader(content)
        fieldnames = reader.fieldnames or []
        
        # Convert CSV rows to list of dictionaries for Celery
        csv_data = list(reader)
        
        if not csv_data:
            messages.error(request, "CSV file is empty.")
            return redirect('import_students_and_enroll')
        
        # Queue the task asynchronously
        from course.tasks import process_enrollment_import
        task = process_enrollment_import.delay(csv_data, request.user.id)
        
        messages.success(
            request,
            f"Enrollment import started! Processing {len(csv_data)} rows in the background. "
            f"Task ID: {task.id}. You can continue working while the import completes."
        )
        
        return redirect('subjectEnrollmentList')
        
    except Exception as e:
        messages.error(request, f"Error reading file: {str(e)}")
        return redirect('import_students_and_enroll')


# Original synchronous version (kept for reference/fallback)
@login_required
@permission_required('course.add_subjectenrollment', raise_exception=True)
def import_students_and_enroll_sync(request):
    if request.method != 'POST':
        return render(request, 'course/subjectEnrollment/import_student_and_enroll.html')

    import_file = request.FILES.get('import_file')
    if not import_file:
        messages.error(request, "No file selected. Please upload a CSV file.")
        return redirect('import_students_and_enroll')

    try:
        content = import_file.read().decode('utf-8-sig').splitlines()
        reader = csv.DictReader(content)
        fieldnames = reader.fieldnames or []

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
            """
            Match subject_name ignoring extra spacing, case-insensitive.
            Fallback to subject_code match if name not found.
            """
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

            if qs.count() > 1:
                subj = qs.first()
            subject_by_name_cache[norm] = subj
            return subj

        def resolve_subjects_from_row(row, row_num):
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
                if not subj:
                    messages.error(request, f"Row {row_num}: Subject with ID {sid} not found.")
                    continue
                if subj.id not in seen_ids:
                    found.append(subj); seen_ids.add(subj.id)

            for nm in names:
                subj = get_subject_by_name(nm)
                if not subj:
                    messages.error(request, f"Row {row_num}: Subject named '{nm}' not found (by name or code).")
                    continue
                if subj.id not in seen_ids:
                    found.append(subj); seen_ids.add(subj.id)

            return found

        def get_or_create_user_profile(email, first_name, last_name, identification, course, row_num):
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
            if profile_created:
                updated = []
                if first_name and profile.first_name != first_name:
                    profile.first_name = first_name; updated.append('first_name')
                if last_name and profile.last_name != last_name:
                    profile.last_name = last_name; updated.append('last_name')
                if profile.role != role:
                    profile.role = role; updated.append('role')
                if identification and profile.id_number != identification:
                    profile.id_number = identification; updated.append('id_number')
                if course and profile.course != course:
                    profile.course = course; updated.append('course')
                if updated:
                    profile.save(update_fields=updated)
            return user, profile

        success, partial, skipped = 0, 0, 0
        with transaction.atomic():
            for row_num, row in enumerate(reader, start=2):  # header=1, first data row=2
                try:
                    email = (row.get('Email') or '').strip().lower()
                    last_name = (row.get('Last Name') or '').strip()
                    first_name = (row.get('First Name') or '').strip()
                    id_number = (row.get('Identification') or '').strip()
                    semester_full_name = (row.get('Semester') or '').strip()
                    course_name = (row.get('Course') or '').strip()

                    if not email:
                        messages.error(request, f"Row {row_num}: Missing Email.")
                        skipped += 1
                        continue
                    if not semester_full_name:
                        messages.error(request, f"Row {row_num}: Missing Semester for {email}.")
                        skipped += 1
                        continue

                    semester = get_semester(semester_full_name)
                    if not semester:
                        messages.error(request, f"Row {row_num}: Semester '{semester_full_name}' not found for {email}.")
                        skipped += 1
                        continue

                    course = get_course(course_name)
                    if course_name and not course:
                        messages.warning(request, f"Row {row_num}: Course '{course_name}' not found for {first_name} {last_name}. Ignoring course.")

                    user, _profile = get_or_create_user_profile(
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        identification=id_number,
                        course=course,
                        row_num=row_num
                    )

                    subjects = resolve_subjects_from_row(row, row_num)
                    if not subjects:
                        messages.error(request, f"Row {row_num}: No valid subjects found for {email}. Row skipped.")
                        skipped += 1
                        continue

                    created_any = False

                    for subj in subjects:
                        # 1) Already has a REAL enrollment?
                        real_exists = SubjectEnrollment.objects.filter(
                            student=user,
                            subject=subj,
                            semester=semester
                        ).exists()
                        if real_exists:
                            messages.info(
                                request,
                                f"{first_name} {last_name} already enrolled in {subj.subject_name} for {semester.semester_name}."
                            )
                            continue

                        # 2) UPGRADE a placeholder row if it exists (student IS NULL)
                        placeholder = (
                            SubjectEnrollment.objects
                            .select_for_update()
                            .filter(student__isnull=True, subject=subj, semester=semester)
                            .first()
                        )

                        if placeholder:
                            placeholder.student = user
                            placeholder.save(update_fields=['student'])
                            messages.success(
                                request,
                                f"{first_name} {last_name} enrolled in {subj.subject_name} (converted from placeholder)."
                            )
                            created_any = True
                            continue

                        # 3) Otherwise, create a brand-new REAL enrollment
                        se, created = SubjectEnrollment.objects.get_or_create(
                            student=user,
                            subject=subj,
                            semester=semester,
                            defaults={'status': 'enrolled'}
                        )
                        if created:
                            messages.success(request, f"{first_name} {last_name} enrolled in {subj.subject_name}.")
                            created_any = True
                            
                            for sdg in subj.target_sdgs.all():
                                obj, created_sdg = StudentSDG.objects.get_or_create(
                                    student=user,
                                    sdg=sdg,
                                    defaults={'count': 1}
                                )
                                if not created_sdg:
                                    StudentSDG.objects.filter(student=user, sdg=sdg).update(count=F('count') + 1)

                        else:
                            messages.info(
                                request,
                                f"{first_name} {last_name} already enrolled in {subj.subject_name} for {semester.semester_name}."
                            )

                    if created_any:
                        success += 1
                    else:
                        partial += 1

                except Exception as e:
                    messages.error(request, f"Row {row_num}: Unexpected error: {e}")
                    skipped += 1
                    continue

        messages.success(
            request,
            f"Student import and enrollment completed. Created={success}, Partial={partial}, Skipped={skipped}."
        )

    except Exception as e:
        messages.error(request, f"Error importing file: {str(e)}")

    return redirect('subjectEnrollmentList')

