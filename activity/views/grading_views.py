from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from activity.models import Activity, StudentActivity, RetakeRecordDetail
from subject.models import Subject
from activity.utils.authorization import check_activity_access
from activity.services.auto_grader import (
    recompute_retake_record_score,
    recompute_student_activity_total,
)


def _ungraded_essay_details(activity):
    return RetakeRecordDetail.objects.filter(
        activity_question__activity=activity,
        activity_question__quiz_type__name__in=['Essay', 'Document'],
        score=0,
    ).exclude(
        student_answer__isnull=True, uploaded_file=''
    ).exclude(
        student_answer='', uploaded_file=''
    ).select_related('student', 'activity_question', 'retake_record')


# Teacher grade essay
@method_decorator(login_required, name='dispatch')
class GradeEssayView(View):
    def get(self, request, activity_id):
        activity = get_object_or_404(Activity, pk=activity_id)

        has_access, redirect_response = check_activity_access(request, activity, require_teacher=True)
        if not has_access:
            return redirect_response

        submission_details = _ungraded_essay_details(activity)
        return render(request, 'activity/grade/grade_essay.html', {
            'activity': activity,
            'submission_details': submission_details,
        })


@method_decorator(login_required, name='dispatch')
class GradeEssayViewCM(View):
    def get(self, request, activity_id):
        activity = get_object_or_404(Activity, pk=activity_id)

        has_access, redirect_response = check_activity_access(request, activity, require_teacher=True)
        if not has_access:
            return redirect_response

        subject = get_object_or_404(Subject, id=activity.subject.id)
        submission_details = _ungraded_essay_details(activity)
        return render(request, 'activity/grade/grade_essay_CM.html', {
            'activity': activity,
            'submission_details': submission_details,
            'subject': subject,
        })


# Grade student individual essay
@method_decorator(login_required, name='dispatch')
class GradeIndividualEssayView(View):
    def get(self, request, activity_id, detail_local_id):
        activity = get_object_or_404(Activity, pk=activity_id)

        has_access, redirect_response = check_activity_access(request, activity, require_teacher=True)
        if not has_access:
            return redirect_response

        detail = get_object_or_404(RetakeRecordDetail, local_id=detail_local_id)

        return render(request, 'activity/grade/grade_individual_essay.html', {
            'activity': activity,
            'detail': detail,
        })

    def post(self, request, activity_id, detail_local_id):
        activity = get_object_or_404(Activity, pk=activity_id)

        has_access, redirect_response = check_activity_access(request, activity, require_teacher=True)
        if not has_access:
            return redirect_response

        detail = get_object_or_404(RetakeRecordDetail, local_id=detail_local_id)

        score = request.POST.get('score')
        max_score = detail.activity_question.score

        if score:
            score = float(score)
            if score < 0:
                return render(request, 'activity/grade/grade_individual_essay.html', {
                    'activity': activity,
                    'detail': detail,
                    'error': "Score cannot be negative",
                })

            if score > max_score:
                return render(request, 'activity/grade/grade_individual_essay.html', {
                    'activity': activity,
                    'detail': detail,
                    'error': f"Score cannot exceed {max_score}",
                })

            detail.score = score
            detail.save(update_fields=['score'])

            if detail.retake_record_id:
                recompute_retake_record_score(detail.retake_record)
                sa = detail.retake_record.student_activity
                if sa:
                    recompute_student_activity_total(sa)

        messages.success(request, 'Successfully graded.')
        return redirect('grade_essays', activity_id=activity_id)


@method_decorator(login_required, name='dispatch')
class GradeIndividualEssayViewCM(View):
    def get(self, request, activity_id, detail_local_id):
        activity = get_object_or_404(Activity, pk=activity_id)

        has_access, redirect_response = check_activity_access(request, activity, require_teacher=True)
        if not has_access:
            return redirect_response

        detail = get_object_or_404(RetakeRecordDetail, local_id=detail_local_id)
        subject = get_object_or_404(Subject, id=activity.subject.id)

        return render(request, 'activity/grade/grade_individual_essay_CM.html', {
            'activity': activity,
            'detail': detail,
            'subject': subject,
        })

    def post(self, request, activity_id, detail_local_id):
        activity = get_object_or_404(Activity, pk=activity_id)

        has_access, redirect_response = check_activity_access(request, activity, require_teacher=True)
        if not has_access:
            return redirect_response

        detail = get_object_or_404(RetakeRecordDetail, local_id=detail_local_id)
        subject = get_object_or_404(Subject, id=activity.subject.id)

        score = request.POST.get('score')
        max_score = detail.activity_question.score

        if score:
            score = float(score)
            if score < 0:
                return render(request, 'activity/grade/grade_individual_essay_CM.html', {
                    'activity': activity,
                    'detail': detail,
                    'subject': subject,
                    'error': "Score cannot be negative",
                })

            if score > max_score:
                return render(request, 'activity/grade/grade_individual_essay_CM.html', {
                    'activity': activity,
                    'detail': detail,
                    'subject': subject,
                    'error': f"Score cannot exceed {max_score}",
                })

            detail.score = score
            detail.save(update_fields=['score'])

            if detail.retake_record_id:
                recompute_retake_record_score(detail.retake_record)
                sa = detail.retake_record.student_activity
                if sa:
                    recompute_student_activity_total(sa)

        messages.success(request, 'Successfully graded.')
        return redirect('grade_essays_CM', activity_id=activity_id)


@method_decorator(login_required, name='dispatch')
class GradeAssessmentView(View):
    def get(self, request, activity_id):
        # Fetch the activity
        activity = get_object_or_404(Activity, pk=activity_id)

        # Ensure user has access to this activity
        has_access, redirect_response = check_activity_access(request, activity, require_teacher=True)
        if not has_access:
            return redirect_response

        # Fetch all student activities for the selected activity
        student_activities = StudentActivity.objects.filter(activity=activity)

        # Separate students into those with scores and those without scores
        students_with_scores = student_activities.filter(total_score__gt=0)
        students_without_scores = student_activities.filter(total_score=0)

        return render(request, 'activity/assessments/assessment-to-be-graded.html', {
            'activity': activity,
            'students_with_scores': students_with_scores,
            'students_without_scores': students_without_scores
        })

    def post(self, request, activity_id):
        # Fetch the activity
        activity = get_object_or_404(Activity, pk=activity_id)

        # Ensure user has access to this activity
        has_access, redirect_response = check_activity_access(request, activity, require_teacher=True)
        if not has_access:
            return redirect_response

        # Fetch student grades from the form submission
        for key, value in request.POST.items():
            if key.startswith('student_'):  # Expecting input names like 'student_<id>'
                student_id = int(key.split('_')[1])
                try:
                    score = float(value) if value else 0

                    # Validate the score against the activity's max_score
                    if score > activity.max_score:
                        messages.error(request, f"Score for student ID {student_id} exceeds the maximum score of {activity.max_score}.")
                        return redirect('grade-assessment', activity_id=activity_id)

                    # Update the score for the student activity
                    student_activity = StudentActivity.objects.get(activity=activity, student_id=student_id)
                    student_activity.total_score = score
                    student_activity.save()

                except ValueError:
                    messages.error(request, f"Invalid score input for student ID {student_id}.")
                    return redirect('grade-assessment', activity_id=activity_id)

        # Add a success message and redirect after saving all scores
        messages.success(request, "Scores updated successfully.")
        return redirect('grade-assessment', activity_id=activity_id)


@method_decorator(login_required, name='dispatch')
class GradeAssessmentViewCM(View):
    def get(self, request, activity_id):
        # Fetch the activity
        activity = get_object_or_404(Activity, pk=activity_id)

        # Ensure user has access to this activity
        has_access, redirect_response = check_activity_access(request, activity, require_teacher=True)
        if not has_access:
            return redirect_response

        subject = activity.subject
        subject = subject_id = activity.subject.id
        subject = get_object_or_404(Subject, id=subject_id)

        # Fetch all student activities for the selected activity
        student_activities = StudentActivity.objects.filter(activity=activity)

        # Separate students into those with scores and those without scores
        students_with_scores = student_activities.filter(total_score__gt=0)
        students_without_scores = student_activities.filter(total_score=0)

        return render(request, 'activity/assessments/assessment-to-be-graded-cm.html', {
            'activity': activity,
            'subject': subject,
            'students_with_scores': students_with_scores,
            'students_without_scores': students_without_scores
        })

    def post(self, request, activity_id):
        # Fetch the activity
        activity = get_object_or_404(Activity, pk=activity_id)

        # Ensure user has access to this activity
        has_access, redirect_response = check_activity_access(request, activity, require_teacher=True)
        if not has_access:
            return redirect_response

        # Fetch student grades from the form submission
        for key, value in request.POST.items():
            if key.startswith('student_'):  # Expecting input names like 'student_<id>'
                student_id = int(key.split('_')[1])
                try:
                    score = float(value) if value else 0

                    # Validate the score against the activity's max_score
                    if score > activity.max_score:
                        messages.error(request, f"Score for student ID {student_id} exceeds the maximum score of {activity.max_score}.")
                        return redirect('assessment-list-cm', subject_id=activity.subject.id)

                    # Update the score for the student activity
                    student_activity = StudentActivity.objects.get(activity=activity, student_id=student_id)
                    student_activity.total_score = score
                    student_activity.save()

                except ValueError:
                    messages.error(request, f"Invalid score input for student ID {student_id}.")
                    return redirect('assessment-list-cm', activity_id=activity_id)

        # Add a success message and redirect after saving all scores
        messages.success(request, "Scores updated successfully.")
        # Redirect to the first module if any exists, otherwise to activity detail
        if activity.additional_modules.exists():
            first_module = activity.additional_modules.first()
            return redirect('view-subject-module', pk=first_module.id)
        return redirect('assessment-list-cm', subject_id=activity.subject.id)
