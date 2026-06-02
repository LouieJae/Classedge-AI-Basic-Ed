from django.shortcuts import render, redirect, get_object_or_404
from course.models import Semester, Term
from subject.models import Subject, EvaluationAssignment, Schedule
from module.models import Module
from activity.models import Activity ,StudentQuestion, ActivityQuestion, ActivityType, RetakeRecordDetail
from django.utils import timezone
from course.forms import *
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from module.forms.module_form import moduleForm
from datetime import timedelta
from django.db.models import Count
from django.contrib import messages
from course.models import SubjectEnrollment
from subject.utils import get_file_type
import os

@login_required
def classroom_mode(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    user = request.user

    selected_semester_id = request.GET.get('semester')
    selected_semester = None

    if selected_semester_id and selected_semester_id != 'None':
        selected_semester = get_object_or_404(Semester, id=selected_semester_id)
        terms = Term.objects.filter(semester=selected_semester)
    else:
        now = timezone.localtime(timezone.now())
        selected_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()
        terms = Term.objects.filter(semester=selected_semester)

    is_student = user.is_authenticated and user.is_student
    is_teacher = user.is_authenticated and user.is_teacher
    
    # ===== AUTHORIZATION CHECK =====
    # Check if user has permission to access this subject
    has_access = False
    
    if is_student:
        # Students must be enrolled in the subject for the selected semester
        is_enrolled = SubjectEnrollment.objects.filter(
            student=user,
            subject=subject,
            semester=selected_semester,
            status='enrolled'
        ).exists()
        
        if is_enrolled:
            has_access = True
        else:
            messages.error(request, "You are not enrolled in this subject for this semester.")
    
    elif is_teacher:
        # Teachers must be assigned as teacher or collaborator
        is_assigned_teacher = subject.assign_teacher == user
        is_collaborator = user in subject.collaborators.all()
        is_substitute_teacher = subject.substitute_teacher == user
        
        if is_assigned_teacher or is_collaborator or is_substitute_teacher:
            has_access = True
        else:
            messages.error(request, "You are not assigned to that subject.")
    
    else:
        # Admin or other roles - check if they have specific permissions
        # For now, allow admins and program heads/deans
        if user.has_perm('subject.view_subject') or user.role_name in ['admin', 'program head', 'dean']:
            has_access = True
        else:
            messages.error(request, "You do not have permission to access this subject.")
    
    # If no access, redirect back to subject list
    if not has_access:
        return redirect('SubjectList')
    # ===== END AUTHORIZATION CHECK =====

    assignment_activity_type = ActivityType.objects.filter(name="Assignment").first()
    quiz_activity_type = ActivityType.objects.filter(name="Quiz").first()
    exam_activity_type = ActivityType.objects.filter(name="Exam").first()
    participation_activity_type = ActivityType.objects.filter(name="Participation").first()
    special_activity_type = ActivityType.objects.filter(name="Special Activity").first()

    # Ensure that IDs are assigned only when activity types are found
    assignment_activity_type_id = assignment_activity_type.id if assignment_activity_type else None
    quiz_activity_type_id = quiz_activity_type.id if quiz_activity_type else None
    exam_activity_type_id = exam_activity_type.id if exam_activity_type else None
    participation_activity_type_id = participation_activity_type.id if participation_activity_type else None
    special_activity_type_id = special_activity_type.id if special_activity_type else None

    selected_semester_id = request.GET.get('semester')
    selected_semester = None

    if selected_semester_id and selected_semester_id != 'None':
        selected_semester = get_object_or_404(Semester, id=selected_semester_id)
        terms = Term.objects.filter(semester=selected_semester)
    else:
        now = timezone.localtime(timezone.now())
        selected_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()
        terms = Term.objects.filter(semester=selected_semester)

    is_student = user.is_authenticated and user.is_student
    is_teacher = user.is_authenticated and user.is_teacher
    
    answered_activity_ids = []
    
    
    if is_student:
        completed_activities = RetakeRecordDetail.objects.filter(
            student=user,
            activity_question__activity__term__in=terms,  # Filter by terms within the selected semester
            score__gt=0
        ).values_list('activity_question__activity_id', flat=True).distinct()

        answered_essays = RetakeRecordDetail.objects.filter(
            student=user,
            activity_question__quiz_type__name='Essay',
            activity_question__activity__term__in=terms,  # Filter by terms within the selected semester
            student_answer__isnull=False
        ).values_list('activity_question__activity_id', flat=True).distinct()

        answered_documents = RetakeRecordDetail.objects.filter(
            student=user,
            activity_question__quiz_type__name='Document',
            activity_question__activity__term__in=terms,  # Filter by terms within the selected semester
            uploaded_file__isnull=False,
        ).exclude(student_answer__isnull=True, uploaded_file='').exclude(student_answer='', uploaded_file='').values_list('activity_question__activity_id', flat=True).distinct()

        answered_activity_ids = set(completed_activities).union(answered_essays, answered_documents)
        
        activities = Activity.objects.filter(
            Q(subject=subject) & Q(term__in=terms) & 
            (Q(remedial=False) | Q(remedial=True, studentactivity__student=user)),
            status=True
        ).filter(
            # Only include activities that have questions or are marked for direct score entry
            Q(activityquestion__isnull=False) | Q(classroom_mode=True, max_score__isnull=False)
        ).distinct()
        
        finished_activities = activities.filter(
            end_time__lte=timezone.localtime(timezone.now()), 
            pk__in=answered_activity_ids
        )
        ongoing_activities = activities.filter(
            start_time__lte=timezone.localtime(timezone.now()), 
            end_time__gte=timezone.localtime(timezone.now())
        ).exclude(
            # LEGACY: participation rows still on StudentQuestion; pending Task 8 follow-up.
            pk__in=StudentQuestion.objects.filter(
                is_participation=True
            ).values_list('activity_id', flat=True)
        )
        upcoming_activities = activities.filter(start_time__gt=timezone.localtime(timezone.now())).exclude(
            pk__in=StudentQuestion.objects.filter(
                is_participation=True
            ).values_list('activity_id', flat=True)
        ).exclude(
            studentquestion__is_participation=True
        ).values('activity_type__name').annotate(count=Count('pk'))

        # Adjusted module visibility logic
        modules = Module.objects.filter(subject=subject, term__semester=selected_semester).exclude(
            Q(term__isnull=True) | Q(start_date__isnull=True) | Q(end_date__isnull=True)
            )
        visible_modules = []

        for module in modules:
            if not module.display_lesson_for_selected_users.exists() or user in module.display_lesson_for_selected_users.all():
                visible_modules.append(module)

        
    else:
        modules = Module.objects.filter( Q(term__semester=selected_semester) |
        Q(term__isnull=True, start_date__isnull=True, end_date__isnull=True),
        subject=subject)

        activities = Activity.objects.filter(subject=subject, term__in=terms, status=True).filter(
            # Only include activities that have questions or are marked for direct score entry
            Q(activityquestion__isnull=False) | Q(classroom_mode=True, max_score__isnull=False)
        ).distinct()

        finished_activities = activities.filter(
            end_time__lte=timezone.localtime(timezone.now())
        )
        ongoing_activities = activities.filter(
            start_time__lte=timezone.localtime(timezone.now()), 
            end_time__gte=timezone.localtime(timezone.now())
        ).exclude(
            pk__in=StudentQuestion.objects.filter(
                is_participation=True
            ).values_list('activity_id', flat=True)  # Exclude participation activities
        )

        upcoming_activities = activities.filter(start_time__gt=timezone.localtime(timezone.now())).exclude(
            pk__in=StudentQuestion.objects.filter(
                is_participation=True
            ).values_list('activity_id', flat=True)  # Exclude participation activities
        ).exclude(
            studentquestion__is_participation=True
        )

    # Group ongoing activities by type and count each type
    ongoing_activities_grouped = (
        ongoing_activities
        .values('activity_type__name')
        .annotate(count=Count('pk'))
        .order_by('activity_type__name')
    )

    ongoing_activities_links = [
        {'name': activity.activity_type.name, 'link': f"/activity_detail/{activity.id}"}
        for activity in ongoing_activities
    ]

    activities_with_grading_needed = []
    ungraded_items_count = 0
    if is_teacher:
        for activity in activities:
            questions_requiring_grading = ActivityQuestion.objects.filter(
                activity=activity,
                quiz_type__name__in=['Essay', 'Document']
            )
            ungraded_items = RetakeRecordDetail.objects.filter(
                Q(activity_question__in=questions_requiring_grading),
                Q(student_answer__isnull=False) | Q(uploaded_file__isnull=False),
                score=0
            ).exclude(student_answer__isnull=True, uploaded_file='').exclude(student_answer='', uploaded_file='')
            if ungraded_items.exists():
                activities_with_grading_needed.append((activity, ungraded_items.count()))
                ungraded_items_count += ungraded_items.count()

    # Attach activities to each module directly in the context
    for module in modules:
        # Get activities linked via the additional_modules ManyToMany field
        module.activities = activities.filter(additional_modules=module)
        module.red_flag = not module.term or not module.start_date or not module.end_date

    
    available_evaluations = None
    if is_student:
        available_evaluations = EvaluationAssignment.objects.filter(
            subject=subject,
            semester=selected_semester,
            is_visible=True
        ).exclude(
            evaluations__student=user
        ).select_related('teacher', 'subject').distinct()


    form = moduleForm()

    months_in_semester = []
    semester_start = selected_semester.start_date
    semester_end = selected_semester.end_date

    current_date = semester_start
    while current_date <= semester_end:
        month_name = current_date.strftime('%B')
        if month_name not in months_in_semester:
            months_in_semester.append(month_name)
        current_date = current_date.replace(day=28) + timedelta(days=4)

    # ===== BUILD CURRENT WEEK SCHEDULE (server-side) =====
    today = timezone.localdate()

    # Find Sunday of current week
    current_week_start = today
    while current_week_start.weekday() != 6:  # 6 = Sunday
        current_week_start -= timedelta(days=1)
    current_week_end = current_week_start + timedelta(days=6)

    schedules = Schedule.objects.filter(subject=subject)
    schedule_modules = Module.objects.filter(
        subject=subject,
        start_date__lte=semester_end,
        end_date__gte=semester_start
    )

    current_week_dates = []
    for day_offset in range(7):
        date = current_week_start + timedelta(days=day_offset)
        formatted_date = date.strftime("%Y-%m-%d")
        day_name = date.strftime("%A")
        short_date = date.strftime("%b %d")  # e.g. "Mar 29"

        lessons_for_date = []
        unique_modules = set()
        schedule_time = None

        for schedule in schedules:
            if date.strftime("%a") in schedule.days_of_week:
                if schedule.schedule_start_time and schedule.schedule_end_time:
                    start_t = schedule.schedule_start_time.strftime("%I:%M %p").lstrip("0")
                    end_t = schedule.schedule_end_time.strftime("%I:%M %p").lstrip("0")
                    schedule_time = f"{start_t} to {end_t}"

                for module in schedule_modules:
                    module_start_date = timezone.localtime(module.start_date).date()
                    module_end_date = timezone.localtime(module.end_date).date()

                    if module_start_date <= current_week_end and module_end_date >= current_week_start:
                        if module.id not in unique_modules:
                            unique_modules.add(module.id)
                            module_activities = Activity.objects.filter(
                                additional_modules=module, status=True
                            ).exclude(
                                activity_type__name__iexact="participation"
                            ).distinct()

                            file_type = get_file_type(module)
                            file_ext = None
                            if module.file:
                                file_ext = os.path.splitext(module.file.name)[1].lower()

                            lessons_for_date.append({
                                'module_id': module.id,
                                'lesson': module.file_name,
                                'description': module.description or '',
                                'file_url': module.file.url if module.file else None,
                                'embed': module.iframe_code if module.iframe_code else None,
                                'file_extension': file_ext,
                                'url': module.url if module.url else None,
                                'allow_download': module.allow_download,
                                'type': file_type,
                                'activities': module_activities,
                                'activity_count': module_activities.count(),
                            })

        current_week_dates.append({
            'date': formatted_date,
            'day': day_name,
            'short_date': short_date,
            'time': schedule_time,
            'lessons': lessons_for_date,
        })

    week_label = f"Week - {current_week_start.strftime('%B %d')} to {current_week_end.strftime('%B %d')}"
    # ===== END BUILD CURRENT WEEK SCHEDULE =====

    return render(request, 'course/classroom_mode.html', {
        'subject': subject,
        'modules': modules,
        'ongoing_activities': ongoing_activities,
        'upcoming_activities': upcoming_activities,
        'finished_activities': finished_activities,
        'activities_with_grading_needed': activities_with_grading_needed,
        'available_evaluations': available_evaluations,
        'is_student': is_student,
        'is_teacher': is_teacher,
        'ungraded_items_count': ungraded_items_count,
        'selected_semester_id': selected_semester_id,
        'selected_semester': selected_semester,
        'answered_activity_ids': answered_activity_ids,
        'form': form,
        'assignment_activity_type_id': assignment_activity_type_id,
        'quiz_activity_type_id': quiz_activity_type_id, 
        'exam_activity_type_id': exam_activity_type_id,
        'participation_activity_type_id': participation_activity_type_id,
        'special_activity_type_id': special_activity_type_id,
        'ongoing_activities_grouped': ongoing_activities_grouped,
        'ongoing_activities_links': ongoing_activities_links,
        'semester_months': months_in_semester,
        'current_week_dates': current_week_dates,
        'week_label': week_label,
    })
   