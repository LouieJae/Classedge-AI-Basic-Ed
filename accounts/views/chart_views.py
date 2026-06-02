from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, F
from course.models import Semester
from subject.models import Subject
from accounts.models import Profile
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from course.models import SubjectEnrollment
from activity.models import Activity


@login_required
def studentPerCourse(request):
    user = request.user
    selected_semester_id = request.GET.get("semester")
    cache_key = f"student_per_course_{user.id}_{selected_semester_id or 'current'}"

    data = cache.get(cache_key)
    if data:
        return JsonResponse(data, safe=False)

    selected_semester = None
    if selected_semester_id and selected_semester_id != "None":
        selected_semester = get_object_or_404(Semester, id=selected_semester_id)
    else:
        now = timezone.localtime(timezone.now())
        selected_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if not selected_semester:
        return JsonResponse([], safe=False)

    # Filter students based on role (Teacher sees only their students)
    if hasattr(user, "profile") and user.is_teacher:
        teacher_subjects = Subject.objects.filter(assign_teacher=user)
        student_enrollments = SubjectEnrollment.objects.filter(
            subject__in=teacher_subjects, semester=selected_semester
        )
    else:
        student_enrollments = SubjectEnrollment.objects.filter(semester=selected_semester)

    # Group by Course and Year Level
    student_counts = Profile.objects.filter(
        id__in=student_enrollments.values("student"),
        course__isnull=False,
        grade_year_level__isnull=False
    ).values(
        course_name=F("course__name"),
        course_short_name=F("course__short_name"),
        year_level=F("grade_year_level"),
    ).annotate(
        student_count=Count("id")
    ).order_by("course__name", "year_level")

    # Format the response to be grouped by course
    grouped_data = {}
    for entry in student_counts:
        course = entry["course_name"]
        year_level = entry["year_level"]
        count = entry["student_count"]

        if course not in grouped_data:
            grouped_data[course] = {"short_name": entry["course_short_name"], "year_levels": {}}
        
        grouped_data[course]["year_levels"][year_level] = count

    cache.set(cache_key, grouped_data, timeout=600)
    return JsonResponse(grouped_data)

@login_required
def studentPerSubject(request):
    user = request.user
    selected_semester_id = request.GET.get("semester")
    teacher_id = request.GET.get("teacher_id")  # Get teacher filter from request

    cache_key = f"student_per_subject_{user.id}_{selected_semester_id or 'current'}_{teacher_id or 'all'}"
    data = cache.get(cache_key)
    if data:
        return JsonResponse(data, safe=False)

    selected_semester = None
    if selected_semester_id:
        selected_semester = get_object_or_404(Semester, id=selected_semester_id)
    else:
        now = timezone.localtime(timezone.now())
        selected_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if not selected_semester:
        return JsonResponse([], safe=False)

    role_name = user.role_name
    is_teacher = role_name == "teacher"
    is_student = role_name == "student"
    is_registrar = role_name == "registrar"

    if not teacher_id and is_teacher:
        teacher_id = user.id

    if is_registrar and teacher_id:
        teacher = get_object_or_404(User, id=teacher_id)
        student_enrollments = SubjectEnrollment.objects.filter(
            subject__assign_teacher=teacher, semester=selected_semester
        )
    elif is_teacher:
        student_enrollments = SubjectEnrollment.objects.filter(
            subject__assign_teacher=user, semester=selected_semester
        )
    elif is_student:
        student_subjects = SubjectEnrollment.objects.filter(
            student=user, semester=selected_semester
        ).values_list("subject", flat=True)
        student_enrollments = SubjectEnrollment.objects.filter(
            subject_id__in=student_subjects, semester=selected_semester
        )
    else:
        student_enrollments = SubjectEnrollment.objects.filter(semester=selected_semester)

    student_counts = student_enrollments.values(
        subject_short_name=F("subject__subject_short_name")
    ).annotate(
        student_count=Count("student")
    ).order_by("subject__subject_short_name")

    data = {
        "subjects": [entry["subject_short_name"] for entry in student_counts],
        "student_counts": [entry["student_count"] for entry in student_counts]
    }

    cache.set(cache_key, data, timeout=600)
    return JsonResponse(data)

@login_required
def student_activities_json(request):
    """API endpoint to fetch activities per subject for the logged-in student."""
    user = request.user

    if not hasattr(user, "profile") or not user.profile.role:
        return JsonResponse({"error": "Invalid user profile"}, status=400)

    role_name = user.role_name
    
    if role_name != "student":
        return JsonResponse({"error": "Only students can access this data"}, status=403)

    enrolled_subjects = SubjectEnrollment.objects.filter(student=user).values_list("subject", flat=True)

    activities_per_subject = Activity.objects.filter(subject__in=enrolled_subjects).values('subject__subject_name').annotate(
        activity_count=Count('id')
    ).order_by('-activity_count')

    return JsonResponse(list(activities_per_subject), safe=False)

