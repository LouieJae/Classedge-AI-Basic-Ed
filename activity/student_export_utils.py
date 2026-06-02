import csv
import io
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Prefetch
from .models import StudentActivity, StudentQuestion, ActivityQuestion

@login_required
def export_student_data_csv(request):
    """
    Export student activity data including scores, responses, and performance metrics
    Format: Comprehensive student performance data - Optimized for large datasets
    """
    subject_id = request.GET.get('subject_id')
    activity_id = request.GET.get('activity_id')
    
    # Build optimized queryset with all necessary related data
    student_activities = StudentActivity.objects.select_related(
        'student', 'activity', 'activity__subject', 'activity__activity_type'
    ).prefetch_related(
        Prefetch(
            'activity__activityquestion_set',
            queryset=ActivityQuestion.objects.all(),
            to_attr='cached_questions'
        )
    )
    
    if subject_id:
        student_activities = student_activities.filter(activity__subject_id=subject_id)
    if activity_id:
        student_activities = student_activities.filter(activity_id=activity_id)
    
    # Create CSV response with streaming for large datasets
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_data_export.csv"'
    
    writer = csv.writer(response)
    
    # Write headers
    headers = [
        'student_email', 'student_name', 'subject_name', 'activity_name', 'activity_type',
        'total_score', 'max_score', 'percentage_score', 'retake_count', 'start_time',
        'end_time', 'attendance_mode', 'is_editable', 'question_order', 'question_text',
        'student_answer', 'question_score', 'max_question_score', 'submission_time',
        'status', 'is_participation'
    ]
    writer.writerow(headers)
    
    # Batch process to manage memory
    batch_size = 1000
    student_activities = student_activities.iterator(chunk_size=batch_size)
    
    # Cache frequently accessed data
    for student_activity in student_activities:
        # Pre-calculate common values to avoid repeated lookups
        student_name = f"{student_activity.student.first_name} {student_activity.student.last_name}".strip()
        subject_name = student_activity.activity.subject.subject_name
        activity_name = student_activity.activity.activity_name
        activity_type = student_activity.activity.activity_type.name if student_activity.activity.activity_type else ''
        max_score = student_activity.activity.max_score or 100
        percentage_score = round((student_activity.total_score / max_score) * 100, 2) if max_score else 0
        
        start_time = student_activity.start_time.strftime('%Y-%m-%d %H:%M:%S') if student_activity.start_time else ''
        end_time = student_activity.end_time.strftime('%Y-%m-%d %H:%M:%S') if student_activity.end_time else ''
        attendance_mode = student_activity.attendance_mode or ''
        
        # Get all questions for this student and activity in one query
        questions = StudentQuestion.objects.filter(
            student=student_activity.student,
            activity=student_activity.activity
        ).select_related('activity_question')
        
        if not questions.exists():
            # Write activity row without questions
            writer.writerow([
                student_activity.student.email,
                student_name,
                subject_name,
                activity_name,
                activity_type,
                student_activity.total_score,
                max_score,
                percentage_score,
                student_activity.retake_count,
                start_time,
                end_time,
                attendance_mode,
                student_activity.is_editable,
                '', '', '', '', '', '', '', ''
            ])
        else:
            # Write activity with questions and responses
            for question_order, student_question in enumerate(questions, 1):
                question_text = student_question.activity_question.question_text if student_question.activity_question else ''
                max_question_score = student_question.activity_question.score if student_question.activity_question else 0
                submission_time = student_question.submission_time.strftime('%Y-%m-%d %H:%M:%S') if student_question.submission_time else ''
                
                writer.writerow([
                    student_activity.student.email,
                    student_name,
                    subject_name,
                    activity_name,
                    activity_type,
                    student_activity.total_score,
                    max_score,
                    percentage_score,
                    student_activity.retake_count,
                    start_time,
                    end_time,
                    attendance_mode,
                    student_activity.is_editable,
                    question_order,
                    question_text,
                    student_question.student_answer or '',
                    student_question.score,
                    max_question_score,
                    submission_time,
                    'Completed' if student_question.status else 'Pending',
                    student_question.is_participation
                ])
    
    return response