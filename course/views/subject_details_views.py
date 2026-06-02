from django.shortcuts import render, redirect, get_object_or_404
from course.models import SubjectEnrollment, Semester, Term, Attendance
from accounts.models import Profile
from subject.models import Subject, EvaluationAssignment, Schedule
from module.models import Module
from activity.models import Activity ,StudentQuestion, ActivityQuestion, ActivityType, RetakeRecordDetail
from accounts.models import CustomUser
from django.utils import timezone
from course.forms import *
from django.db.models import Q, Prefetch
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from module.forms.module_form import moduleForm
from django.contrib import messages
from datetime import datetime, timedelta
from django.db.models import Avg
from module.models import StudentProgress
from django.db.models import Count
from classroom.models import Teacher_Attendance ,Classroom_mode
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from activity.utils.authorization import check_subject_access
from django.http import JsonResponse
from course.models import Attendance, AttendanceStatus


@login_required
def update_attendance_status(request, attendance_id):
    
    if request.method == 'POST':
        try:
            attendance = get_object_or_404(Attendance, id=attendance_id)
            status_id = request.POST.get('status_id')
            remark = request.POST.get('remark', '')
            
            if not status_id:
                return JsonResponse({'success': False, 'error': 'Status is required'}, status=400)
            
            status = get_object_or_404(AttendanceStatus, id=status_id)
            attendance.status = status
            attendance.remark = remark
            attendance.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Attendance updated successfully',
                'status': status.status
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


@login_required
def delete_attendance(request, attendance_id):
    from django.http import JsonResponse
    from course.models import Attendance
    
    if request.method == 'POST':    
        try:
            attendance = get_object_or_404(Attendance, id=attendance_id)
            attendance.delete()
            return JsonResponse({'success': True, 'message': 'Attendance deleted successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


@login_required
def get_attendance_statuses(request):
    from django.http import JsonResponse
    from course.models import AttendanceStatus
    
    statuses = AttendanceStatus.objects.all().values('id', 'status')
    return JsonResponse({'statuses': list(statuses)})


@login_required
def subjectStudentListCM(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    user = request.user
    
    # ===== AUTHORIZATION CHECK =====
    # Only teachers assigned to the subject or admins can view student list

    # Ensure user has access to this module's subject
    has_access, redirect_response = check_subject_access(request, subject)
    if not has_access:
        return redirect_response

    is_teacher = user.is_authenticated and user.is_teacher
    is_assigned_teacher = subject.assign_teacher == user
    is_collaborator = user in subject.collaborators.all()
    
    has_access = False
    if is_teacher and (is_assigned_teacher or is_collaborator):
        has_access = True
    elif user.has_perm('subject.view_subject') or user.role_name in ['admin', 'program head', 'dean']:
        has_access = True
    else:
        messages.error(request, "You do not have permission to view the student list for this subject.")
    
    if not has_access:
        return redirect('SubjectList')

    
    # ===== END AUTHORIZATION CHECK =====
    
    selected_semester_id = request.GET.get('semester')
    selected_semester = None

    if selected_semester_id and selected_semester_id.strip() and selected_semester_id != 'None':
        try:
            selected_semester = Semester.objects.get(id=selected_semester_id)
        except Semester.DoesNotExist:
            selected_semester = None

    if not selected_semester:
        now = timezone.localtime(timezone.now())
        selected_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if not selected_semester:
        return HttpResponse("No active semester found.", status=404)

    students = CustomUser.objects.filter(
        subjectenrollment__subject=subject,
        subjectenrollment__semester=selected_semester
    ).distinct()

    return render(request, 'course/view_student_roster_CM.html', {
        'subject': subject,
        'students': students,
        'selected_semester': selected_semester,
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_subject_students_api(request, subject_id):
    """
    API endpoint to get list of students enrolled in a specific subject.
    
    Query Parameters:
    - semester: Optional semester ID to filter by specific semester
    - status: Optional enrollment status filter (enrolled, dropped, etc.)
    - search: Optional search term for student name or ID
    
    Returns:
    - List of students with their enrollment details
    """
    try:
        subject = Subject.objects.get(id=subject_id)
    except Subject.DoesNotExist:
        return Response(
            {'error': 'Subject not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if user has permission to view this subject's students
    user = request.user
    user_role = user.role_name
    
    # Only teachers, admins, program heads, and deans can view student lists
    if user_role not in ['teacher', 'admin', 'program head', 'academic dean', 'academic director']:
        # Check if user is the assigned teacher or substitute
        if subject.assign_teacher != user and subject.substitute_teacher != user:
            return Response(
                {'error': 'You do not have permission to view this subject\'s students'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    # Get query parameters
    semester_id = request.GET.get('semester')
    enrollment_status = request.GET.get('status', 'enrolled')
    search_query = request.GET.get('search', '')
    
    # Build the query
    enrollments = SubjectEnrollment.objects.filter(subject=subject)
    
    # Filter by semester if provided
    if semester_id:
        try:
            semester = Semester.objects.get(id=semester_id)
            enrollments = enrollments.filter(semester=semester)
        except Semester.DoesNotExist:
            pass
    else:
        # Default to current semester
        now = timezone.now().date()
        current_semester = Semester.objects.filter(
            start_date__lte=now, 
            end_date__gte=now
        ).first()
        if current_semester:
            enrollments = enrollments.filter(semester=current_semester)
    
    # Filter by enrollment status
    if enrollment_status:
        enrollments = enrollments.filter(status=enrollment_status)
    
    # Search by student name or ID
    if search_query:
        enrollments = enrollments.filter(
            Q(student__first_name__icontains=search_query) |
            Q(student__last_name__icontains=search_query) |
            Q(student__profile__id_number__icontains=search_query) |
            Q(student__email__icontains=search_query)
        )
    
    # Select related data to optimize queries
    enrollments = enrollments.select_related(
        'student', 
        'student__profile',
        'semester'
    ).order_by('student__last_name', 'student__first_name')
    
    # Build response data
    students_data = []
    for enrollment in enrollments:
        student = enrollment.student
        profile = student.profile
        
        student_data = {
            'id': student.id,
            'student_id': profile.id_number if profile else None,
            'first_name': student.first_name,
            'last_name': student.last_name,
            'full_name': f"{student.first_name} {student.last_name}",
            'email': student.email,
            'enrollment_status': enrollment.status,
            'enrollment_date': enrollment.enrollment_date.isoformat() if enrollment.enrollment_date else None,
            'semester': {
                'id': enrollment.semester.id,
                'name': enrollment.semester.semester_name
            } if enrollment.semester else None,
            'profile': {
                'year_level': profile.grade_year_level if profile else None,
                'course': profile.course if profile else None,
                'contact_number': profile.phone_number if profile else None,
            }
        }
        students_data.append(student_data)
    
    return Response({
        'subject': {
            'id': subject.id,
            'name': subject.subject_name,
            'code': subject.subject_short_name
        },
        'total_students': len(students_data),
        'students': students_data
    }, status=status.HTTP_200_OK)

