from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from datetime import date, datetime, timedelta
from django.db.models import Q, Count
from django.db.models.deletion import ProtectedError
from accounts.models import CustomUser
from roles.models import Role
from course.models import Semester, SubjectEnrollment
from calendars.models import Holiday, Event, Announcement
from subject.forms import subjectForm, subjectPhotoForm, CoilSubjectForm
from subject.models import Subject
from subject.serializers import SubjectSerializer
from rest_framework.viewsets import ModelViewSet
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from subject.models import Subject
from django.utils import timezone
from rest_framework.permissions import DjangoModelPermissions
from accounts.utils import paginate_queryset, get_pagination_context
from accounts.utils import CustomPagination
from activity.models import Activity
from gradebookcomponent.services.queue import get_needs_grading_for_teacher
from activity.models import StudentActivity

class SubjectViewSet(ModelViewSet):
    serializer_class = SubjectSerializer
    filter_backends = [SearchFilter]
    search_fields = [
        'subject_name',
        'subject_short_name',
        'assign_teacher__first_name',
        'assign_teacher__last_name',
        'room_number'
    ]
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    pagination_class = CustomPagination

    def get_queryset(self):
        today = date.today()

        # Use ?semester=ID if provided, otherwise fallback to current semester
        semester_id = self.request.query_params.get("semester")
        if semester_id:
            current_semester = Semester.objects.filter(id=semester_id).first()
        else:
            current_semester = Semester.objects.filter(
                start_date__lte=today, end_date__gte=today
            ).first()

        user = self.request.user
        queryset = Subject.objects.none()  # default empty

        if not current_semester:
            return queryset

        # Subjects offered in this semester (via SubjectEnrollment)
        subject_ids = SubjectEnrollment.objects.filter(
            semester=current_semester
        ).values_list('subject_id', flat=True)

        queryset = Subject.objects.filter(id__in=subject_ids).distinct()

        # Role-based restrictions
        if hasattr(user, 'profile') and user.profile.role:
            role = user.role_name

            if role == 'teacher':
                queryset = queryset.filter(
                    Q(assign_teacher=user) |
                    Q(substitute_teacher=user, allow_substitute_teacher=True) |
                    Q(collaborators=user)
                ).distinct()

            elif role == 'student':
                enrolled_ids = SubjectEnrollment.objects.filter(
                    student=user,
                    semester=current_semester
                ).values_list('subject_id', flat=True)
                queryset = queryset.filter(id__in=enrolled_ids)

        # Optional filter: only subjects that have a gradebook set up
        # (used by the grade-finalization page so empty subjects are hidden).
        has_gradebook = self.request.query_params.get('has_gradebook')
        if has_gradebook and has_gradebook.lower() == 'true':
            queryset = queryset.filter(gradebook_components__isnull=False).distinct()

        return queryset

@login_required
@permission_required('subject.view_subject', raise_exception=True)
def course_list(request):
    today = date.today()
    current_semester = Semester.objects.filter(start_date__lte=today, end_date__gte=today).first()

    selected_semester_id = request.GET.get('semester')
    search_query = request.GET.get('search', '').strip()
    if selected_semester_id:
        selected_semester = get_object_or_404(Semester, id=selected_semester_id)
    else:
        selected_semester = current_semester

    user = request.user
    user_role = user.role_name  # kept in context for templates that still read it
    current_day = datetime.now().strftime('%a')

    is_audit = (
        user.is_admin
        or user.is_program_head
        or user.is_academic_director
        or user.is_time_keeper
        or user.is_dean
        or getattr(user, 'is_superuser', False)
        or getattr(user, 'is_staff', False)
    )

    orbit_q = Q(is_coil=True) | Q(is_hali=True) | Q(is_cte=True)

    if user.is_teacher:
        if selected_semester:
            subjects = (
                Subject.objects
                .filter(assign_teacher=user)
                .filter(
                    Q(schedules__semester=selected_semester) |
                    Q(subjectenrollment__semester=selected_semester)
                )
                .exclude(orbit_q)
                .distinct()
            )
        else:
            subjects = (
                Subject.objects
                .filter(assign_teacher=user)
                .exclude(orbit_q)
                .distinct()
            )

    elif user.is_registrar:
        subjects = Subject.objects.exclude(orbit_q)
    elif user.is_program_head:
        profile = getattr(user, "profile", None)
        my_department = getattr(profile, "department_fields", None) if profile else None
        if my_department is None:
            subjects = Subject.objects.none()
        else:
            base = Subject.objects.filter(
                assign_teacher__profile__department_fields=my_department,
            ).exclude(orbit_q).distinct()
            if selected_semester:
                base = base.filter(
                    id__in=SubjectEnrollment.objects.filter(
                        semester=selected_semester,
                    ).values_list("subject_id", flat=True)
                ).distinct()
            subjects = base
    elif is_audit:
        if selected_semester:
            subjects = Subject.objects.filter(
                id__in=SubjectEnrollment.objects.filter(semester=selected_semester).values_list('subject_id', flat=True)
            ).exclude(orbit_q).distinct()
        else:
            subjects = Subject.objects.exclude(orbit_q).distinct()
    elif user.is_student:
        enrollment_qs = SubjectEnrollment.objects.filter(
            student=user, status='enrolled',
        )
        if selected_semester:
            enrollment_qs = enrollment_qs.filter(semester=selected_semester)
        subjects = Subject.objects.filter(
            id__in=enrollment_qs.values_list('subject_id', flat=True)
        ).distinct()
    else:
        if selected_semester:
            subjects = Subject.objects.filter(
                id__in=SubjectEnrollment.objects.filter(semester=selected_semester).values_list('subject_id', flat=True)
            ).exclude(orbit_q)
        else:
            subjects = Subject.objects.exclude(orbit_q)

    semesters = Semester.objects.all()
    form = subjectForm()

    if search_query:
        subjects = subjects.filter(
            Q(subject_name__icontains=search_query)
            | Q(subject_short_name__icontains=search_query)
            | Q(subject_code__icontains=search_query)
            | Q(assign_teacher__first_name__icontains=search_query)
            | Q(assign_teacher__last_name__icontains=search_query)
            | Q(substitute_teacher__first_name__icontains=search_query)
            | Q(substitute_teacher__last_name__icontains=search_query)
            | Q(room_number__icontains=search_query)
        ).distinct()

    # Server-side pagination (default 12 per page — fills 3- and 4-col grids cleanly)
    page_obj, paginator = paginate_queryset(subjects, request, items_per_page=12)
    pagination_context = get_pagination_context(page_obj, request)

    if user.is_teacher or is_audit:
        page_subject_ids = [s.id for s in page_obj]
        enrollment_filter = Q(student__isnull=False, status='enrolled', subject_id__in=page_subject_ids)
        if selected_semester:
            enrollment_filter &= Q(semester=selected_semester)
        enrollment_counts = dict(
            SubjectEnrollment.objects
            .filter(enrollment_filter)
            .values('subject_id')
            .annotate(c=Count('id'))
            .values_list('subject_id', 'c')
        )
        for subject in page_obj:
            subject.enrolled_count = enrollment_counts.get(subject.id, 0)

    if user.is_student:
        # Flag subjects whose self-check-in form should be hidden because
        # the student already has an attendance record for today. Saves
        # the "you're already marked" round-trip.
        from course.models.attendance_model import Attendance

        page_subject_ids = [s.id for s in page_obj]
        marked_subject_ids = set(
            Attendance.objects.filter(
                student=user,
                subject_id__in=page_subject_ids,
                date=today,
            ).values_list('subject_id', flat=True)
        )
        for subject in page_obj:
            subject.self_attended_today = subject.id in marked_subject_ids

    context = {
        'page_obj': page_obj,
        'semesters': semesters,
        'selected_semester': selected_semester,
        'current_semester': current_semester,
        'current_day': current_day,
        'MEDIA_URL': settings.MEDIA_URL,
        'form': form,
        'user_role': user_role,
        'search_query': search_query,
    }
    context.update(pagination_context)

    if user.is_teacher or is_audit:
        # ---- Upcoming assessments — activities in the teacher's subjects
        # whose end_time falls AFTER today (excluding today, which is
        # handled by the "Due today" card below) and within the next
        # 14 days. Sorted soonest-first so the closest deadline sits
        # at the top of the sidebar. ----
        today_date = date.today()
        now_dt = timezone.now()
        teacher_subject_ids_for_upcoming = list(subjects.values_list('id', flat=True))
        # Activity-type → FontAwesome glyph so each row carries its
        # type at a glance. Falls back to a generic clipboard icon.
        ACTIVITY_ICON_MAP = {
            'quiz': 'question-circle',
            'exam': 'file-alt',
            'assignment': 'pencil-alt',
            'special': 'star',
            'special activity': 'star',
            'coding': 'code',
            'participation': 'users',
        }
        upcoming_items = []
        if teacher_subject_ids_for_upcoming:
            tomorrow_start = (now_dt + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0,
            )
            window_end = tomorrow_start + timedelta(days=14)
            upcoming_qs = (
                Activity.objects
                .filter(
                    subject_id__in=teacher_subject_ids_for_upcoming,
                    status=True,
                    end_time__gte=tomorrow_start,
                    end_time__lt=window_end,
                )
                .exclude(studentquestion__is_participation=True)
                .select_related('subject', 'activity_type')
                .order_by('end_time')[:6]
            )
            for a in upcoming_qs:
                type_name = (a.activity_type.name if a.activity_type else '').lower()
                upcoming_items.append({
                    'id': a.id,
                    'title': a.activity_name,
                    'date': a.end_time,
                    'subject_short': a.subject.subject_short_name or a.subject.subject_name if a.subject else '',
                    'type_name': a.activity_type.name if a.activity_type else 'Assessment',
                    'icon': ACTIVITY_ICON_MAP.get(type_name, 'clipboard-list'),
                })

        # ---- Teacher To-do: only Essay / Document submissions awaiting manual grading ----
        now_dt = timezone.now()
        teacher_subject_ids = list(subjects.values_list('id', flat=True))

        todo_items = []
        todo_total = 0
        if teacher_subject_ids:
            ungraded_qs = (
                get_needs_grading_for_teacher(request.user)
                .filter(activity__subject_id__in=teacher_subject_ids)
            )
            todo_total = ungraded_qs.count()
            for sa in ungraded_qs[:5]:
                if not sa.activity or not sa.student:
                    continue
                name = sa.student.get_full_name() or sa.student.username
                todo_items.append({
                    'student_name': name,
                    'initial': (sa.student.first_name or sa.student.username or '?')[:1].upper(),
                    'activity_name': sa.activity.activity_name,
                    'activity_id': sa.activity_id,
                    'type_name': sa.activity.activity_type.name if sa.activity.activity_type else '',
                    'end_time': sa.activity.end_time,
                })

        # ---- Due today: activities in teacher's subjects with end_time today ----
        due_today_items = []
        if teacher_subject_ids:
            day_start = now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            due_today_qs = (
                Activity.objects
                .filter(
                    subject_id__in=teacher_subject_ids,
                    status=True,
                    end_time__gte=day_start,
                    end_time__lt=day_end,
                )
                .exclude(studentquestion__is_participation=True)
                .select_related('subject', 'activity_type')
                .order_by('end_time')[:6]
            )
            due_today_items = list(due_today_qs)

        context['upcoming_items'] = upcoming_items
        context['todo_items'] = todo_items
        context['todo_total'] = todo_total
        context['due_today_items'] = due_today_items

    if user.is_student:
        now_dt = timezone.now()
        student_subject_ids = list(subjects.values_list('id', flat=True))

        completed_activity_ids = set(
            StudentActivity.objects.filter(
                student=user,
                activity__subject_id__in=student_subject_ids,
                retake_count__gte=1,
            ).values_list('activity_id', flat=True)
        )

        student_base_qs = (
            Activity.objects
            .filter(subject_id__in=student_subject_ids, status=True)
            .filter(Q(remedial=False) | Q(remedial_students=user))
            .exclude(activity_type__name__iexact='Participation')
            .select_related('subject', 'activity_type')
            .distinct()
        )

        soon_cutoff = now_dt + timedelta(days=3)
        due_activities = list(
            student_base_qs.filter(
                end_time__gte=now_dt,
                end_time__lte=soon_cutoff,
            ).exclude(local_id__in=completed_activity_ids)
            .order_by('end_time')[:6]
        )
        due_ids = {a.local_id for a in due_activities}

        todo_activities = list(
            student_base_qs.filter(
                Q(start_time__isnull=True) | Q(start_time__lte=now_dt)
            ).filter(
                Q(end_time__isnull=True) | Q(end_time__gte=now_dt)
            ).exclude(local_id__in=completed_activity_ids)
            .exclude(local_id__in=due_ids)
            .order_by('end_time', '-local_id')[:6]
        )

        upcoming_activities = list(
            student_base_qs.filter(
                start_time__gt=now_dt,
            ).exclude(local_id__in=completed_activity_ids)
            .order_by('start_time')[:6]
        )

        context['due_activities'] = due_activities
        context['todo_activities'] = todo_activities
        context['upcoming_activities'] = upcoming_activities
        context['now'] = now_dt

        template = 'student/course-list.html'
    elif user.is_teacher or is_audit:
        template = 'teacher/course-list.html'
    else:
        template = 'subject/course-list.html'
    return render(request, template, context)


@login_required
def filter_substitute_teacher(request, assign_teacher_id):
    teacher_role = Role.objects.get(name__iexact='teacher')
    substitute_teachers = CustomUser.objects.filter(profile__role=teacher_role).exclude(id=assign_teacher_id)

    data = {
        "teachers": [{"id": teacher.id, "name": teacher.get_full_name()} for teacher in substitute_teachers]
    }
    return JsonResponse(data)


@login_required
@permission_required('subject.add_subject', raise_exception=True)
def create_course(request):
    if request.method == 'POST':
        form = subjectForm(request.POST, request.FILES)

        # Extract field values from the form
        subject_name = request.POST.get('subject_name')
        subject_short_name = request.POST.get('subject_short_name')
        subject_code = request.POST.get('subject_code')
        assign_teacher_id = request.POST.get('assign_teacher')
        substitute_teacher_id = request.POST.get('substitute_teacher')
        allow_substitute_teacher = request.POST.get('allow_substitute_teacher')
        subject_description = request.POST.get('subject_description')
        room_number = request.POST.get('room_number')
        subject_photo = request.FILES.get('subject_photo')
        is_coil = request.POST.get('is_coil') == 'on'
        is_hali = request.POST.get('is_hali') == 'on'
        is_cte = request.POST.get('is_cte') == 'on'
        raw_enrollees = request.POST.get('max_number_of_enrollees')
        try:
            max_number_of_enrollees = int(raw_enrollees) if raw_enrollees.strip() != '' else None
        except ValueError:
            max_number_of_enrollees = None
        duration = request.POST.get('duration')
        industry_partners = request.POST.get('industry_partners')
        highlight = request.POST.get('highlight')
        status = request.POST.get('status')
        target_sdgs = request.POST.getlist('target_sdgs')  # Use getlist for many-to-many
        country = request.POST.get('country')

        allow_substitute_teacher = True if allow_substitute_teacher == "on" else False

        # Validate required fields
        if not subject_name or not assign_teacher_id or not room_number:
            messages.error(request, "All required fields must be filled in.")
            return redirect('course-list')
        
        if not status:
            messages.error(request, "Please select a status for the course.")
            return redirect('course-list')

        # Fetch teacher
        assign_teacher = CustomUser.objects.filter(id=assign_teacher_id).first()
        substitute_teacher = CustomUser.objects.filter(id=substitute_teacher_id).first() if substitute_teacher_id else None

        if not assign_teacher:
            messages.error(request, "Selected teacher does not exist.")
            return redirect('course-list')

        # Prevent duplicate subjects for the same teacher
        existing_subject = Subject.objects.filter(
            subject_name=subject_name,
            assign_teacher=assign_teacher
        ).first()

        if existing_subject:
            messages.error(request, f"Teacher '{assign_teacher.get_full_name()}' is already assigned to subject '{subject_name}'. Please assign a different subject.")
            return redirect('course-list')
        
        if Subject.objects.filter(room_number=room_number, subject_name=subject_name, assign_teacher=assign_teacher).exists():
            messages.error(request, f"Course '{subject_name}' is already assigned to teacher '{assign_teacher.get_full_name()}' in room '{room_number}'. Please choose a different room or subject.")
            return redirect('course-list')

        # Create the subject
        subject = Subject.objects.create(
            subject_name=subject_name,
            subject_short_name=subject_short_name,
            subject_code=subject_code,
            assign_teacher=assign_teacher,
            substitute_teacher=substitute_teacher,
            allow_substitute_teacher=allow_substitute_teacher,
            subject_description=subject_description,
            room_number=room_number,
            subject_photo=subject_photo,
            is_coil=is_coil,
            is_hali=is_hali,
            is_cte=is_cte,
            max_number_of_enrollees=max_number_of_enrollees,
            duration=duration,
            industry_partners=industry_partners,
            highlight=highlight,
            status=status,
            country=country,
        )
        
        # Set many-to-many field after creation
        if target_sdgs:
            subject.target_sdgs.set(target_sdgs if isinstance(target_sdgs, list) else [target_sdgs])

        messages.success(request, f"Course '{subject_name}' assigned to {assign_teacher.get_full_name()} successfully!")
        return redirect('course-list')

    else:
        form = subjectForm()
        teachers = CustomUser.objects.filter(profile__role=Role.objects.get(name__iexact='teacher'))

    return render(request, 'subject/create-course.html', {'form': form, 'teachers': teachers})


@login_required
@permission_required('subject.change_subject', raise_exception=True)
def update_course(request, pk):
    subject = get_object_or_404(Subject, pk=pk)

    if request.method == 'POST':
        form = subjectForm(request.POST, request.FILES, instance=subject)

        # Extract field values from the form
        subject_name = request.POST.get('subject_name')
        subject_short_name = request.POST.get('subject_short_name')
        subject_code = request.POST.get('subject_code')
        assign_teacher_id = request.POST.get('assign_teacher')
        subject_description = request.POST.get('subject_description')
        room_number = request.POST.get('room_number')
        substitute_teacher_id = request.POST.get('substitute_teacher')
        allow_substitute_teacher = request.POST.get('allow_substitute_teacher')
        subject_photo = request.FILES.get('subject_photo')
        clear_subject_photo = request.POST.get('subject_photo-clear') == 'on'
        is_coil = request.POST.get('is_coil') == 'on'
        is_hali = request.POST.get('is_hali') == 'on'
        is_cte = request.POST.get('is_cte') == 'on'
        raw_enrollees = request.POST.get('max_number_of_enrollees')
        try:
            max_number_of_enrollees = int(raw_enrollees) if raw_enrollees.strip() != '' else None
        except ValueError:
            max_number_of_enrollees = None
        duration = request.POST.get('duration')
        industry_partners = request.POST.get('industry_partners')
        highlight = request.POST.get('highlight')
        status = request.POST.get('status')
        target_sdgs = request.POST.getlist('target_sdgs')  # Use getlist for many-to-many
        country = request.POST.get('country')

        # Convert checkbox value to boolean
        allow_substitute_teacher = True if allow_substitute_teacher == "on" else False

        # Validate required fields
        if not subject_name or not assign_teacher_id or not room_number:
            messages.error(request, "All required fields must be filled in.")
            return redirect('course-list')
        
        if not status:
            messages.error(request, "Please select a status for the subject.")
            return redirect('course-list')

        # Fetch primary and substitute teachers
        assign_teacher = CustomUser.objects.filter(id=assign_teacher_id).first()
        substitute_teacher = CustomUser.objects.filter(id=substitute_teacher_id).first() if substitute_teacher_id else None

        if not assign_teacher:
            messages.error(request, "Selected teacher does not exist.")
            return redirect('course-list')

        # Prevent the same teacher from having duplicate subject names (excluding the current subject)
        existing_subject = Subject.objects.filter(
            subject_name=subject_name,
            assign_teacher=assign_teacher
        ).exclude(pk=subject.pk).first()

        if existing_subject:
            messages.error(request, f"Teacher '{assign_teacher.get_full_name()}' is already assigned to subject '{subject_name}'.")
            return redirect('subject')

        # Prevent duplicate subject & teacher assignments in the same room
        if Subject.objects.filter(room_number=room_number, subject_name=subject_name, assign_teacher=assign_teacher).exclude(pk=subject.pk).exists():
            messages.error(request, f"Course '{subject_name}' is already assigned to teacher '{assign_teacher.get_full_name()}' in room '{room_number}'. Please choose a different room or subject.")
            return redirect('subject')

        # Assign values
        subject.subject_name = subject_name
        subject.subject_short_name = subject_short_name
        subject.subject_code = subject_code
        subject.assign_teacher = assign_teacher
        subject.room_number = room_number
        subject.substitute_teacher = substitute_teacher
        subject.allow_substitute_teacher = allow_substitute_teacher
        subject.subject_description = subject_description
        if subject_photo:
            subject.subject_photo = subject_photo
        elif clear_subject_photo:
            if subject.subject_photo:
                subject.subject_photo.delete(save=False)
            subject.subject_photo = None
        subject.is_coil = is_coil
        subject.is_hali = is_hali
        subject.is_cte = is_cte
        subject.max_number_of_enrollees = max_number_of_enrollees
        subject.duration = duration
        subject.industry_partners = industry_partners
        subject.highlight = highlight
        subject.status = status
        subject.country = country

        subject.save()
        
        # Set many-to-many field after save
        if target_sdgs:
            subject.target_sdgs.set(target_sdgs if isinstance(target_sdgs, list) else [target_sdgs])
        else:
            subject.target_sdgs.clear()

        messages.success(request, 'Course updated successfully!')
        return redirect('course-list')

    else:
        form = subjectForm(instance=subject)

    return render(request, 'subject/update-course.html', {'form': form, 'subject': subject})


@login_required
@permission_required('subject.view_subject', raise_exception=True)
def update_course_photo(request, pk):
    """ Allows teachers to update only the subject photo """
    subject = get_object_or_404(Subject, pk=pk)

    if request.method == 'POST':
        form = subjectPhotoForm(request.POST, request.FILES, instance=subject)

        if form.is_valid():
            form.save()
            messages.success(request, 'Course photo updated successfully!')
            return redirect('course-list')
        else:
            messages.error(request, 'There was an error updating the photo. Please try again.')

    else:
        form = subjectPhotoForm(instance=subject)

    return render(request, 'subject/update-course-photo.html', {'form': form, 'subject': subject})


@login_required
@permission_required('subject.view_subject', raise_exception=True)
def clear_subject_photo(request, pk):
    """ Allows teachers to clear/remove the subject photo """
    subject = get_object_or_404(Subject, pk=pk)
    
    # Check if there's a photo to clear
    if subject.subject_photo:
        # Delete the file from storage
        subject.subject_photo.delete(save=False)
        
        # Set the field to None
        subject.subject_photo = None
        subject.save()
        
        messages.success(request, 'Course photo has been removed successfully!')
    else:
        messages.info(request, 'No photo to remove.')
        
    return redirect('update-course-photo', pk=pk)


# Delete Subject
@login_required
@permission_required('subject.delete_subject', raise_exception=True)
def delete_course(request, pk):

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=400)

    subject = get_object_or_404(Subject, pk=pk)

    try:
        subject.delete()
        messages.success(request, 'Subject deleted successfully!')
        return JsonResponse({'status': 'success'})
    except ProtectedError:
        return JsonResponse({
            'status': 'error',
            'error_type': 'ProtectedError',
            'message': 'This course cannot be deleted because it is referenced by other records.'
        }, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
def check_duplicate_subject(request):
    if request.method == 'POST':
        subject_name = request.POST.get('subject_name')
        is_duplicate = Subject.objects.filter(subject_name=subject_name).exists()
        return JsonResponse({'is_duplicate': is_duplicate})


@login_required
@permission_required('subject.add_subject', raise_exception=True)
def create_coil_subject(request):
    if request.method == 'POST':
        form = CoilSubjectForm(request.POST)
        if form.is_valid():
            subject = form.save(commit=False)
            subject.is_coil = True
            subject.status = 'Available'
            subject.save()
            form.save_m2m()
            messages.success(request, 'COIL Subject created successfully!')
            return redirect('coil_subjectList')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CoilSubjectForm()

    return render(request, 'course/create_coil_subject.html', {'form': form})

# ─── Click-to-edit endpoint ───────────────────────────────────────────
# Thin PATCH handler for cl-edit-inline. Accepts a single allowed field
# in the JSON body and updates it on the Subject.
import json
from django.views.decorators.http import require_http_methods

# Whitelist — only these short-text fields can be patched via this
# endpoint. Anything else (relations, dates, booleans) goes through the
# full update flow so business rules still apply.
_SUBJECT_PATCHABLE_FIELDS = {
    'subject_name':       {'min': 2, 'max': 200, 'label': 'Course name'},
    'subject_short_name': {'min': 1, 'max': 30,  'label': 'Short name'},
    'room_number':        {'min': 0, 'max': 30,  'label': 'Room number'},
}


@login_required
@permission_required('subject.change_subject', raise_exception=True)
@require_http_methods(["PATCH"])
def rename_subject(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Malformed request body.'}, status=400)

    field = next((k for k in payload.keys() if k in _SUBJECT_PATCHABLE_FIELDS), None)
    if not field:
        return JsonResponse({'ok': False, 'error': 'Field is not editable here.'}, status=400)

    rules = _SUBJECT_PATCHABLE_FIELDS[field]
    value = (payload.get(field) or '').strip()
    label = rules['label']

    if len(value) < rules['min']:
        msg = ('%s cannot be empty.' % label) if rules['min'] > 0 \
              else ('%s must be at least %d character%s.' % (label, rules['min'], 's' if rules['min'] > 1 else ''))
        return JsonResponse({'ok': False, 'error': msg}, status=400)
    if len(value) > rules['max']:
        return JsonResponse({
            'ok': False,
            'error': '%s must be at most %d characters.' % (label, rules['max']),
        }, status=400)

    setattr(subject, field, value)
    subject.save(update_fields=[field])
    return JsonResponse({'ok': True, 'value': value})

