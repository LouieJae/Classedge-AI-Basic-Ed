from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from activity.models import StudentActivity, Activity, ScoreChangeLog

@login_required
def scoreChangeLogs(request, activity_id):
    activity = get_object_or_404(Activity, local_id=activity_id)
    score_change_logs = ScoreChangeLog.objects.filter(student_activity__activity=activity).select_related('student_activity', 'changed_by', 'student_activity__student').order_by('-change_date')
    student_activities = StudentActivity.objects.filter(activity=activity)
    return render(request, 'activity/activities/score_change_logs.html', {'activity': activity, 'score_change_logs': score_change_logs, 'student_activities': student_activities})


@login_required
def edit_student_score(request):
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if is_ajax:
            student_activity_id = request.POST.get('student_activity_id')
            new_score = request.POST.get('score')
            
            try:
                student_activity = StudentActivity.objects.get(pk=student_activity_id)
                
                # Check permissions
                is_staff = request.user.is_staff
                is_teacher = hasattr(request.user, 'profile') and request.user.profile.role and request.user.is_teacher
                
                # Only staff can edit locked scores, teachers can only edit if is_editable is True
                if not is_staff and (not is_teacher or not student_activity.is_editable):
                    return JsonResponse({
                        'success': False,
                        'error': 'You do not have permission to edit this score.'
                    })
                
                # Store the previous score before updating
                previous_score = student_activity.total_score
                
                # Update the score
                student_activity.total_score = float(new_score)
                student_activity.save()
                
                # Create a log entry for this score change
                ScoreChangeLog.objects.create(
                    student_activity=student_activity,
                    changed_by=request.user,
                    previous_score=previous_score,
                    new_score=float(new_score)
                )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Score updated successfully'
                })
                
            except StudentActivity.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Student activity not found'
                })
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid score value'
                })
        
        return JsonResponse({
            'success': False,
            'error': 'Invalid request'
        })


@login_required
def toggle_student_assessment_editable(request):
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if is_ajax:
            student_activity_id = request.POST.get('student_activity_id')
            is_editable = request.POST.get('is_editable') == 'true'
            
            try:
                student_activity = StudentActivity.objects.get(pk=student_activity_id)
                
                # Only staff can change editable status
                if not request.user.is_staff:
                    return JsonResponse({'success': False, 'error': 'You do not have permission to change editable status.'})
                
                student_activity.is_editable = is_editable
                student_activity.save()
                
                return JsonResponse({'success': True, 'message': 'Editable status updated successfully'})
            except StudentActivity.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Student activity not found'})
        return JsonResponse({'success': False, 'error': 'Invalid request'})
    return JsonResponse({'success': False, 'error': 'Invalid method'})
