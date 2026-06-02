from datetime import timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from activity.models import Activity, ActivityType, StudentActivity
from subject.models import Subject
from course.models import Semester, SubjectEnrollment
from accounts.models import CustomUser
from activity.utils.authorization import check_activity_access, activity_has_submissions
from django.contrib import messages


@login_required
def subject_assessment_list(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    now = timezone.now()

    # Get the current semester based on the current date
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    from django.db.models import Exists, OuterRef
    submitted_subq = StudentActivity.objects.filter(activity=OuterRef('pk'), retake_count__gte=1)

    # Get activities with a term that belongs to the current semester
    activities_with_term = Activity.objects.filter(subject=subject, term__semester=current_semester, status=True).exclude(activity_type__name__iexact="Participation").annotate(has_submissions=Exists(submitted_subq))

    # Get activities that do not have any term (copied activities)
    activities_without_term = Activity.objects.filter(subject=subject, term__isnull=True, status=True).exclude(activity_type__name__iexact="Participation").annotate(has_submissions=Exists(submitted_subq))

    # Combine both querysets into a list
    activities = list(activities_with_term) + list(activities_without_term)

    user_role = ''
    try:
        user_role = request.user.role_name
    except (AttributeError, ObjectDoesNotExist):
        pass

    # Students no longer have their own per-subject assessment list — the
    # material-list page now hosts an Assessments tab with the same content.
    if user_role == 'student':
        return redirect(f"{reverse('material-list', args=[subject_id])}?view=assessments")

    activity_types = ActivityType.objects.all().order_by('name')
    selected_type_id = request.GET.get('type') or ''

    return render(request, 'activity/assessments/assessment-list.html', {
        'subject': subject,
        'activities': activities,
        'current_semester': current_semester,
        'activity_types': activity_types,
        'selected_type_id': selected_type_id,
    })


@login_required
def viewStudentScore(request, activity_id):
    activity = get_object_or_404(Activity, local_id=activity_id)
    
    # ===== AUTHORIZATION CHECK =====
    has_access, redirect_response = check_activity_access(request, activity, require_teacher=True)
    if not has_access:
        return redirect_response
    # ===== END AUTHORIZATION CHECK =====
    
    student_activities = StudentActivity.objects.filter(activity=activity).select_related('student').order_by('student__last_name', 'student__first_name')
    return render(request, 'activity/assessments/view_student_score.html', {'activity': activity, 'student_activities': student_activities})


@login_required
def assessment_list_cm(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    now = timezone.now()

    # Get the current semester based on the current date
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    # Get activities with a term that belongs to the current semester
    activities_with_term = Activity.objects.filter(subject=subject, term__semester=current_semester, status=True)

    # Get activities that do not have any term (copied activities)
    activities_without_term = Activity.objects.filter(subject=subject, term__isnull=True, status=True)

    # Combine both querysets into a list
    activities = list(activities_with_term) + list(activities_without_term)

    return render(request, 'activity/assessments/assessment-list-cm.html', {
        'subject': subject,
        'activities': activities,
        'current_semester': current_semester,
    })


@login_required
@require_POST
def toggleShowScore(request, activity_id):
    activity = get_object_or_404(Activity, local_id=activity_id)
    
    # ===== AUTHORIZATION CHECK =====
    has_access, redirect_response = check_activity_access(request, activity, require_teacher=True)
    if not has_access:
        return JsonResponse({'success': False, 'error': 'Unauthorized access'})
    # ===== END AUTHORIZATION CHECK =====
    
    activity.show_score = not activity.show_score
    activity.save()
    return JsonResponse({'success': True, 'show_score': activity.show_score})


@login_required
def delete_assessment(request, activity_id):
    activity = get_object_or_404(Activity, local_id=activity_id)
    
    # ===== AUTHORIZATION CHECK =====
    has_access, redirect_response = check_activity_access(request, activity, require_teacher=True)
    if not has_access:
        return redirect_response
    # ===== END AUTHORIZATION CHECK =====
    
    if activity_has_submissions(activity):
        messages.error(
            request,
            "This assessment cannot be deleted because at least one student has already submitted an attempt."
        )
        return redirect('assessment-list')

    subject_id = activity.subject.id
    activity.status = False
    activity.save()
    return redirect('assessment-list')


@login_required
def participation_scores(request, activity_id):
    students = CustomUser.objects.filter(
        subjectenrollment__subject__activity=activity_id,
        subjectenrollment__status='enrolled'
    ).distinct()

    student_data = [{'id': student.id, 'name': student.get_full_name()} for student in students]
    return JsonResponse({'students': student_data})

@login_required
def assessment_list_registrar(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    activities = Activity.objects.filter(subject=subject)
    return render(request, 'activity/assessments/assessment-list-registrar.html', {'subject': subject, 'activities': activities})
