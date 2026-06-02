from django.shortcuts import redirect

from activity.models import RetakeRecordDetail, StudentQuestion


def _resolve_detail_from_sq(student_question_id):
    sq = StudentQuestion.objects.filter(pk=student_question_id).first()
    if not sq:
        return None
    return RetakeRecordDetail.objects.filter(
        student=sq.student, activity_question=sq.activity_question,
    ).order_by('-submission_time').first()


def legacy_grade_individual_redirect(request, activity_id, student_question_id):
    detail = _resolve_detail_from_sq(student_question_id)
    if not detail:
        return redirect('grade_essays', activity_id=activity_id)
    return redirect('grade_individual_essay', activity_id=activity_id,
                    detail_local_id=detail.local_id)


def legacy_grade_individual_redirect_cm(request, activity_id, student_question_id):
    detail = _resolve_detail_from_sq(student_question_id)
    if not detail:
        return redirect('grade_essaysCM', activity_id=activity_id)
    return redirect('grade_individual_essayCM', activity_id=activity_id,
                    detail_local_id=detail.local_id)
