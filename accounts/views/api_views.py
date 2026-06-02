from django.contrib.auth import get_user_model
from course.models import Semester, SubjectEnrollment
from subject.models import Subject
from django.db.models import Count,  F
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from accounts.models import Profile
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils.timezone import localtime
from datetime import timedelta
from django.db.models.functions import TruncDate
from django.db.models import Q

User = get_user_model()

def get_user_subject_count(user, semester_id=None):
    cache_key = f"user_subject_count_{user.id}_{semester_id or 'current'}"
    subjects = cache.get(cache_key)
    if subjects is not None:
        return subjects
    
    today = now().date()
    current_semester = None
    if semester_id:
        current_semester = get_object_or_404(Semester, id=semester_id)
    else:
        current_semester = Semester.objects.filter(start_date__lte=today, end_date__gte=today).first()

    if not current_semester:
        return Subject.objects.none()


    role_name = user.role_name
    is_teacher = role_name == 'teacher'
    is_student = role_name == 'student'

    if is_teacher:
        subjects = Subject.objects.filter(assign_teacher=user, subjectenrollment__semester=current_semester).distinct()
    elif is_student:
        subjects = Subject.objects.filter(subjectenrollment__student=user, subjectenrollment__semester=current_semester).distinct()
    else:
        subjects = Subject.objects.filter(subjectenrollment__semester=current_semester).distinct()

    cache.set(cache_key, subjects, timeout=600) 
    return subjects


def get_student_count_per_course(user, semester_id=None):
    cache_key = f"student_count_per_course_{user.id}_{semester_id or 'current'}"
    student_counts = cache.get(cache_key)
    if student_counts is not None:
        return student_counts

    today = now().date()
    current_semester = None
    if semester_id:
        current_semester = get_object_or_404(Semester, id=semester_id)
    else:
        current_semester = Semester.objects.filter(start_date__lte=today, end_date__gte=today).first()

    if not current_semester:
        return []

    role_name = user.role_name
    is_teacher = role_name == 'teacher'

    if is_teacher:
        teacher_subjects = Subject.objects.filter(assign_teacher=user)
        student_enrollments = SubjectEnrollment.objects.filter(
            subject__in=teacher_subjects, semester=current_semester
        )
    else:
        student_enrollments = SubjectEnrollment.objects.filter(semester=current_semester)

    student_counts = Profile.objects.filter(
        id__in=student_enrollments.values('student'),
        course__isnull=False 
    ).values(
        course_name=F('course__name') 
    ).annotate(
        student_count=Count('id')  
    ).order_by('course__name')

    student_counts = list(student_counts)
    cache.set(cache_key, student_counts, timeout=600)
    return student_counts


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_active_count(request):
    """Fetch all students, categorize them, and count daily logins."""
    
    user = request.user
    now_local = localtime(now())  # Get local time
    one_week_ago = now_local - timedelta(days=7)  # Get time 7 days ago
    
    # Determine user role
    role_name = user.role_name
    is_teacher = role_name == 'teacher'
    is_student = role_name == 'student'
    
    # Base query for students with login data
    student_query = User.objects.filter(
        profile__role__name__iexact='student',
        last_login__date__gte=one_week_ago  # Only count logins in the last 7 days
    )
    
    # Filter based on user role
    if is_teacher:
        # For teachers, only show students enrolled in their subjects
        teacher_subjects = Subject.objects.filter(
            Q(assign_teacher=user) | Q(substitute_teacher=user) | Q(collaborators=user)
        ).distinct()
        
        # Get IDs of students enrolled in teacher's subjects
        enrolled_student_ids = SubjectEnrollment.objects.filter(
            subject__in=teacher_subjects,
            status='enrolled'
        ).values_list('student', flat=True).distinct()
        
        # Filter student query to only include enrolled students
        student_query = student_query.filter(id__in=enrolled_student_ids)
    elif is_student:
        # For students, show only students in the same subjects
        student_subjects = SubjectEnrollment.objects.filter(
            student=user,
            status='enrolled'
        ).values_list('subject', flat=True)
        
        # Get IDs of students enrolled in the same subjects
        classmate_ids = SubjectEnrollment.objects.filter(
            subject__in=student_subjects,
            status='enrolled'
        ).values_list('student', flat=True).distinct()
        
        # Filter student query to only include classmates
        student_query = student_query.filter(id__in=classmate_ids)
    # For other roles (admin, registrar, etc.), show all active students (no additional filtering)
    
    # Get daily login counts
    daily_logins = (
        student_query
        .annotate(login_date=TruncDate('last_login'))  # Group by day
        .values('login_date')
        .annotate(count=Count('id'))  # Count logins per day
        .order_by('login_date')  # Order from oldest to newest
    )

    # Convert queryset to a structured format
    login_counts = {entry["login_date"].strftime("%b %d"): entry["count"] for entry in daily_logins}

    # Ensure all days in the last 7 days are present in the data (fill missing days with 0)
    daily_labels = [(now_local - timedelta(days=i)).strftime("%b %d") for i in range(6, -1, -1)]
    daily_data = [login_counts.get(date, 0) for date in daily_labels]

    return Response({
        "daily_logins": {
            "labels": daily_labels,  # Dates of the last 7 days
            "data": daily_data,  # Number of students who logged in each day
        }
    })

