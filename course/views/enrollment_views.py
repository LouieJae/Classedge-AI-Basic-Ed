import logging

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404

logger = logging.getLogger(__name__)
from course.models import SubjectEnrollment, Semester
from accounts.models import Profile
from subject.models import Subject
from roles.models import Role
from django.views import View
from accounts.models import CustomUser, StudentSDG
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import permission_required
from datetime import date
from collections import defaultdict
from django.db import transaction
from django.conf import settings
from django.db.models import Count
from django.core.mail import send_mass_mail
import threading
from django.db.models import F
from django.core.paginator import Paginator
from django.core.paginator import PageNotAnInteger, EmptyPage

@method_decorator(login_required, name='dispatch')
class EnrollStudentView(View):

    @method_decorator(permission_required('course.add_subjectenrollment', raise_exception=True))
    def get(self, request, *args, **kwargs):
        student_role = Role.objects.get(name__iexact='student')
        profiles = Profile.objects.filter(role=student_role)
        subjects = Subject.objects.all()
        semesters = Semester.objects.all()

        students_by_course = {}
        for profile in profiles:
            course = profile.course.name if profile.course else "No Course"
            if course not in students_by_course:
                students_by_course[course] = []
            students_by_course[course].append({
                'id': profile.id,
                'first_name': profile.first_name,
                'last_name': profile.last_name,
                'email': profile.user.email,
                'grade_year_level': profile.grade_year_level,
            })

        year_levels = profiles.values_list('grade_year_level', flat=True).distinct().exclude(grade_year_level__isnull=True)

        return render(request, 'course/subjectEnrollment/enroll-student.html', {
            'profiles': profiles,
            'subjects': subjects,
            'semesters': semesters,
            'students_by_course': students_by_course,
            'year_levels': year_levels,
        })

    def post(self, request, *args, **kwargs):
        student_profile_ids = request.POST.getlist('student_profile')  # profile IDs
        selected_subject_ids = request.POST.getlist('subject_ids')     # subject IDs (strings)
        semester_id = request.POST.get('semester_id')
        
        if not semester_id:
            messages.error(request, "Please select a semester.")
            return redirect('enrollment-list')
        
        if not selected_subject_ids:
            messages.error(request, "Please select at least one subject.")
            return redirect('enrollment-list')
        
        # Queue the enrollment task asynchronously
        from course.tasks import process_manual_enrollment
        task = process_manual_enrollment.delay(
            student_profile_ids,
            selected_subject_ids,
            semester_id,
            request.user.id
        )
        
        if student_profile_ids:
            messages.success(
                request,
                f"Enrollment started! Processing {len(student_profile_ids)} student(s) for {len(selected_subject_ids)} subject(s) in the background."
            )
        else:
            messages.success(
                request,
                f"Creating subject placeholders for {len(selected_subject_ids)} subject(s) in the background."
            )
        
        return redirect('enrollment-list')


# Original synchronous version (kept for reference/fallback)
@method_decorator(login_required, name='dispatch')
class EnrollStudentViewSync(View):

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        student_profile_ids = request.POST.getlist('student_profile')  # profile IDs
        selected_subject_ids = request.POST.getlist('subject_ids')     # subject IDs (strings)
        semester_id = request.POST.get('semester_id')

        semester = get_object_or_404(Semester, id=semester_id)

        # 1) Load students & subjects in bulk
        students = list(
            CustomUser.objects
            .filter(profile__id__in=student_profile_ids)
            .select_related('profile')
            .only('id', 'first_name', 'last_name', 'email', 'profile__id', 'profile__role')
        )
        subjects = list(
            Subject.objects
            .filter(id__in=selected_subject_ids)
            .only('id', 'subject_name', 'is_coil', 'is_hali', 'max_number_of_enrollees', 'number_of_enrollees')
        )

        # Common IDs we’ll reuse
        student_ids = [s.id for s in students]
        subject_pk_list = [s.id for s in subjects]

        # === Branch A: No students selected → ensure placeholders ===
        if not student_profile_ids:
            existing_placeholders = set(
                SubjectEnrollment.objects
                .filter(student__isnull=True, subject_id__in=subject_pk_list, semester=semester)
                .values_list('subject_id', flat=True)
            )

            to_create_placeholders = [
                SubjectEnrollment(subject_id=sub_id, semester=semester)  # student remains NULL
                for sub_id in subject_pk_list
                if sub_id not in existing_placeholders
            ]

            if to_create_placeholders:
                SubjectEnrollment.objects.bulk_create(
                    to_create_placeholders,
                    batch_size=500,
                    ignore_conflicts=True  # safe with partial unique constraint
                )
                messages.success(request, f"Created {len(to_create_placeholders)} subject placeholder(s) for teachers.")
            else:
                messages.info(request, "Placeholders already exist for all selected subjects in this semester.")

            return redirect('subjectEnrollmentList')

        # === Branch B: Students selected → create real enrollments ===

        # 2) Existing enrollments for this semester (skip duplicates) — REAL students only
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

        # 3) Prior enrollments in other semesters (for retake flags) — REAL students only
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

        # 4) Capacity check for COIL/HALI (count REAL students only)
        subject_by_id = {s.id: s for s in subjects}
        capacity_needed_ids = [sid for sid, s in subject_by_id.items() if (s.is_coil or s.is_hali) and s.max_number_of_enrollees]

        current_counts = defaultdict(int)
        if capacity_needed_ids:
            for row in (
                SubjectEnrollment.objects
                .filter(
                    subject_id__in=capacity_needed_ids,
                    status='enrolled',
                    student__isnull=False  # exclude placeholders
                )
                .values('subject_id')
                .annotate(n=Count('student', distinct=True))
            ):
                current_counts[row['subject_id']] = row['n']

        full_subject_ids = {
            sid for sid in capacity_needed_ids
            if current_counts[sid] >= (subject_by_id[sid].max_number_of_enrollees or 0)
        }

        # 5) Build to-create list; track retakes and messages
        to_create = []
        enrollment_data = []  # for emails
        duplicates_count = 0
        full_msgs = set()
        retakes_msgs = []

        for stu in students:
            for sub in subjects:
                pair = (stu.id, sub.id)

                if pair in existing_pairs:
                    duplicates_count += 1
                    continue

                if sub.id in full_subject_ids:
                    full_msgs.add(f"{sub.subject_name} is already full.")
                    continue

                to_create.append(SubjectEnrollment(
                    student_id=stu.id,
                    subject_id=sub.id,
                    semester=semester,
                ))
                enrollment_data.append((stu, sub, semester))

                if pair in prior_pairs:
                    retakes_msgs.append(
                        f"{stu.get_full_name()} is retaking {sub.subject_name} for {semester.semester_name}."
                    )

        # 6) Bulk create (ignore race-condition duplicates)
        created_enrollments = []
        if to_create:
            created_enrollments = SubjectEnrollment.objects.bulk_create(
                to_create,
                batch_size=1000,
                ignore_conflicts=True
            )
        
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
                    
            new_entries = []
            updates = []
            
            for student_id, sdg_map in student_sdg_updates.items():
                for sdg_id, increment in sdg_map.items():
                    obj, created = StudentSDG.objects.get_or_create(
                        student_id=student_id,
                        sdg_id=sdg_id,
                        defaults= {'count': increment}
                        )
                    if not created:
                        updates.append((obj.pk, increment))
                        
            for pk, increment in updates:
                StudentSDG.objects.filter(pk=pk).update(count=F('count') + increment)
                 

        # 7) Recompute & persist enrollee counts for COIL/HALI subjects touched — REAL students only
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
                        student__isnull=False  # exclude placeholders
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

        # 8) Send enrollment emails AFTER COMMIT
        if enrollment_data:
            def _send_all():
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
                except Exception:
                    logger.exception("Failed to send enrollment emails")

            transaction.on_commit(lambda: threading.Thread(target=_send_all, daemon=True).start())

        # 9) Flash messages
        created_ct = len(created_enrollments)
        if created_ct and not duplicates_count and not full_msgs:
            messages.success(request, f"Successfully enrolled {created_ct} student-subject pair(s).")
        else:
            if created_ct:
                messages.success(request, f"Created {created_ct} enrollment(s).")
            if duplicates_count:
                messages.warning(request, f"Skipped {duplicates_count} duplicate enrollment(s).")
            if full_msgs:
                messages.error(request, "Enrollment blocked: " + ", ".join(sorted(full_msgs)))

        if retakes_msgs:
            messages.info(request, f"Retakes detected: {len(retakes_msgs)}.")

        return redirect('enrollment-list')


@login_required
@permission_required('course.view_subjectenrollment', raise_exception=True)
def enrollment_list(request):
    user = request.user
    selected_semester_id = request.GET.get('semester', None)  # Get the selected semester from the query parameters
    selected_subject_id = request.GET.get('subject', None)  # Get the selected subject from the query parameters
    selected_teacher_id = request.GET.get('teacher', None)  # Get the selected teacher from the query parameters

    current_semester = Semester.current()

    if selected_semester_id:
        selected_semester = get_object_or_404(Semester, id=selected_semester_id)
    else:
        # If no semester is selected and there's no active semester, show all terms
        selected_semester = current_semester if current_semester else None

    if user.is_teacher:
        enrollments = SubjectEnrollment.objects.select_related('subject', 'semester', 'student').filter(subject__assign_teacher=user)
    else:
        enrollments = SubjectEnrollment.objects.select_related('subject', 'semester', 'student')

    if selected_semester:
        enrollments = enrollments.filter(semester=selected_semester)

    if selected_teacher_id:
        selected_teacher = get_object_or_404(CustomUser, id=selected_teacher_id)
        enrollments = enrollments.filter(subject__assign_teacher=selected_teacher)
    else:
        selected_teacher = None

    if selected_subject_id:
        selected_subject = get_object_or_404(Subject, id=selected_subject_id)
        enrollments = enrollments.filter(subject=selected_subject)
    else:
        selected_subject = None

    # Sort enrollments by enrollment_date in descending order (latest first)
    enrollments = enrollments.order_by('-enrollment_date')

    subjects = {}
    for enrollment in enrollments:
        if enrollment.subject not in subjects:
            subjects[enrollment.subject] = []
        subjects[enrollment.subject].append(enrollment)

    # Get per_page parameter from request, default to 10
    per_page = request.GET.get('per_page', '10')
    try:
        per_page = int(per_page)
        if per_page not in [10, 25, 50, 100]:
            per_page = 10
    except (ValueError, TypeError):
        per_page = 10

    # Paginate the accordion items (subjects)
    subjects_list = list(subjects.items())
    page_num = request.GET.get('page', 1)
    paginator = Paginator(subjects_list, per_page)
    try:
        page = paginator.page(page_num)
    except (PageNotAnInteger, EmptyPage):
        page = paginator.page(1)

    semesters = Semester.objects.all()  # Get all semesters for the dropdown
    available_subjects = Subject.objects.filter(subjectenrollment__semester=selected_semester).distinct() if selected_semester else Subject.objects.all()
    
    # Get all teachers who have subjects with enrollments
    available_teachers = CustomUser.objects.filter(
        primary_teacher__subjectenrollment__isnull=False
    ).distinct().order_by('first_name', 'last_name')

    return render(request, 'course/subjectEnrollment/enrollment-list.html', {
        'subjects': page,
        'semesters': semesters,
        'selected_semester': selected_semester,
        'available_subjects': available_subjects,
        'selected_subject': selected_subject,
        'available_teachers': available_teachers,
        'selected_teacher': selected_teacher,
        'current_semester': current_semester,
        'per_page': per_page,
        'MEDIA_URL': settings.MEDIA_URL,
    })

@login_required
@permission_required('course.delete_subjectenrollment', raise_exception=True)
def drop_student_from_subject(request, enrollment_id):
    enrollment = get_object_or_404(SubjectEnrollment, id=enrollment_id)
    
    if enrollment.subject and enrollment.student:
        for sdg in enrollment.subject.target_sdgs.all():
            StudentSDG.objects.filter(
                student=enrollment.student,
                sdg=sdg,
                count__gt=0
            ).update(count=F('count') - 1)
            
    enrollment.status = 'dropped'
    enrollment.drop_date = timezone.now().date()
    enrollment.save()
    messages.success(request, f"{enrollment.student.get_full_name()} has been dropped from {enrollment.subject.subject_name}.")
    return redirect('enrollment-list')

@login_required
@permission_required('course.change_subjectenrollment', raise_exception=True)
def restore_student_from_subject(request, enrollment_id):
    enrollment = get_object_or_404(SubjectEnrollment, id=enrollment_id)
    enrollment.status = 'enrolled'
    enrollment.drop_date = None
    enrollment.save()
    messages.success(request, f"{enrollment.student.get_full_name()} has been enrolled again in {enrollment.subject.subject_name}.")
    return redirect('enrollment-list')

@login_required
@permission_required('course.delete_subjectenrollment', raise_exception=True)
def delete_student_from_subject(request, enrollment_id):
    enrollment = get_object_or_404(SubjectEnrollment, id=enrollment_id)
    enrollment.delete()
    if enrollment.student:
        messages.success(request, f"{enrollment.student.get_full_name()} has been delete from {enrollment.subject.subject_name}.")
    else:
        messages.success(request, f"Data has been delete from {enrollment.subject.subject_name}.")
    return redirect('enrollment-list')


def _drop_enrollments(enrollments_qs):
    today = timezone.now().date()
    dropped = 0
    for enrollment in enrollments_qs:
        if enrollment.status == 'dropped':
            continue
        if enrollment.subject and enrollment.student:
            for sdg in enrollment.subject.target_sdgs.all():
                StudentSDG.objects.filter(
                    student=enrollment.student,
                    sdg=sdg,
                    count__gt=0,
                ).update(count=F('count') - 1)
        enrollment.status = 'dropped'
        enrollment.drop_date = today
        enrollment.save(update_fields=['status', 'drop_date'])
        dropped += 1
    return dropped


@login_required
@permission_required('course.delete_subjectenrollment', raise_exception=True)
@require_POST
@transaction.atomic
def bulk_drop_enrollments(request):
    raw_ids = request.POST.getlist('enrollment_ids') or request.POST.getlist('enrollment_ids[]')
    try:
        enrollment_ids = [int(x) for x in raw_ids if str(x).strip()]
    except (TypeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'Invalid enrollment ids.'}, status=400)

    if not enrollment_ids:
        return JsonResponse({'status': 'error', 'message': 'No enrollments selected.'}, status=400)

    enrollments = (
        SubjectEnrollment.objects
        .select_related('subject', 'student')
        .filter(id__in=enrollment_ids)
        .exclude(status='dropped')
    )
    dropped = _drop_enrollments(enrollments)
    return JsonResponse({'status': 'success', 'dropped': dropped})


@login_required
@permission_required('course.delete_subjectenrollment', raise_exception=True)
@require_POST
@transaction.atomic
def drop_all_in_subject(request, subject_id, semester_id):
    subject = get_object_or_404(Subject, id=subject_id)
    semester = get_object_or_404(Semester, id=semester_id)
    enrollments = (
        SubjectEnrollment.objects
        .select_related('subject', 'student')
        .filter(subject=subject, semester=semester, student__isnull=False)
        .exclude(status='dropped')
    )
    dropped = _drop_enrollments(enrollments)
    return JsonResponse({
        'status': 'success',
        'dropped': dropped,
        'subject': subject.subject_name,
    })


@login_required
@permission_required('course.delete_subjectenrollment', raise_exception=True)
@require_POST
@transaction.atomic
def bulk_remove_enrollments(request):
    raw_ids = request.POST.getlist('enrollment_ids') or request.POST.getlist('enrollment_ids[]')
    try:
        enrollment_ids = [int(x) for x in raw_ids if str(x).strip()]
    except (TypeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'Invalid enrollment ids.'}, status=400)

    if not enrollment_ids:
        return JsonResponse({'status': 'error', 'message': 'No enrollments selected.'}, status=400)

    qs = SubjectEnrollment.objects.filter(id__in=enrollment_ids)
    removed, _ = qs.delete()
    return JsonResponse({'status': 'success', 'removed': removed})


@login_required
@permission_required('course.delete_subjectenrollment', raise_exception=True)
@require_POST
@transaction.atomic
def remove_all_in_subject(request, subject_id, semester_id):
    subject = get_object_or_404(Subject, id=subject_id)
    semester = get_object_or_404(Semester, id=semester_id)
    qs = SubjectEnrollment.objects.filter(subject=subject, semester=semester, student__isnull=False)
    removed, _ = qs.delete()
    return JsonResponse({
        'status': 'success',
        'removed': removed,
        'subject': subject.subject_name,
    })


@login_required
@permission_required('course.view_subjectenrollment', raise_exception=True)
def import_and_export_enrollment_page(request):
    from accounts.utils.pagination_utils import (
        paginate_queryset,
        search_queryset,
        get_pagination_context,
    )

    search_query = request.GET.get('search', '').strip()

    enrollment_qs = SubjectEnrollment.objects.all().select_related(
        'student',
        'subject',
        'subject__assign_teacher',
        'semester',
    )

    # Search
    search_fields = [
        'student__first_name',
        'student__last_name',
        'student__email',
        'student__id_number',
        'subject__subject_name',
        'subject__subject_code',
        'subject__subject_short_name',
        'subject__assign_teacher__first_name',
        'subject__assign_teacher__last_name',
        'semester__semester_name',
    ]
    enrollment_qs = search_queryset(enrollment_qs, search_query, search_fields)

    # Pagination
    page_obj, paginator = paginate_queryset(enrollment_qs, request, items_per_page=10)
    pagination_context = get_pagination_context(page_obj, request)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    context.update(pagination_context)

    return render(request, 'course/subjectEnrollment/import_and_export_enrollement_page.html', context)


