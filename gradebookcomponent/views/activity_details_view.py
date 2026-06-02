from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Max
from django.utils import timezone
from activity.models import Activity, StudentActivity, RetakeRecordDetail
from activity.services.retake_resolver import select_canonical_details
from accounts.models import CustomUser

# Teacher (see all student scores for an activity)
@login_required
def score_sheet(request, activity_id):
    activity = get_object_or_404(Activity, local_id=activity_id)
    student_activities = StudentActivity.objects.filter(activity=activity).select_related('student')

    student_scores_with_names = []
    max_score = activity.max_score

    if activity.passing_score_type == 'percentage':
        passing_score_value = (activity.passing_score / 100) * max_score
    else:
        passing_score_value = activity.passing_score

    activity_ended = bool(activity.end_time and activity.end_time < timezone.now())

    from django.db.models import Q
    for sa in student_activities:
        student = sa.student
        if not student:
            continue
        sq_submission = RetakeRecordDetail.objects.filter(
            activity_question__activity=activity,
            student=student,
        ).aggregate(last_submission=Max('submission_time'))['last_submission']
        submission_date = sa.end_time or sq_submission

        is_submitted = (sa.retake_count or 0) >= 1
        student_scores_with_names.append({
            'student': student,
            'total_score': sa.total_score or 0,
            'max_score': max_score,
            'submission_date': submission_date,
            'passing_score_value': passing_score_value,
            'is_submitted': is_submitted,
            'attendance_mode': sa.attendance_mode,
            'feedback': sa.feedback,
        })

    return render(request, 'gradebookcomponent/activityGrade/score-sheet.html', {
        'activity': activity,
        'passing_points': passing_score_value,
        'student_scores': student_scores_with_names,
        'activity_ended': activity_ended,
    })


@login_required
def teacherActivityViewCM(request, activity_id):
    activity = get_object_or_404(Activity, local_id=activity_id)
    student_scores = StudentActivity.objects.filter(activity=activity).values('student').annotate(total_score=Sum('total_score'))

    student_scores_with_names = []
    max_score = activity.max_score

    if activity.passing_score_type == 'percentage':
        passing_score_value = (activity.passing_score / 100) * max_score
    else:
        passing_score_value = activity.passing_score

    for entry in student_scores:
        student = get_object_or_404(CustomUser, local_id=entry['student'])
        submission_date = RetakeRecordDetail.objects.filter(
            activity_question__activity=activity,
            student=student
        ).aggregate(last_submission=Max('submission_time'))['last_submission']

        student_scores_with_names.append({
            'student': student,
            'total_score': entry['total_score'] or 0,
            'max_score': max_score,
            'submission_date': submission_date,
            'passing_score_value': passing_score_value,
        })

    return render(request, 'gradebookcomponent/activityGrade/teacherGradedActivityCM.html', {
        'activity': activity,
        'student_scores': student_scores_with_names,
        'passing_points': passing_score_value,
        'subject': activity.subject,
    })


# Student (see all scores for his activity)

# Student (see all scores for his activity)
@login_required
def my_assessment_score(request, activity_id):
    activity = get_object_or_404(Activity, local_id=activity_id)
    user = request.user

    # Query based on whether the user is a student or teacher
    if user.is_student:
        student_activities = StudentActivity.objects.filter(activity=activity, student=user)
    else:  # Assume the user is a teacher
        student_activities = StudentActivity.objects.filter(activity=activity)

    detailed_scores = []

    for student_activity in student_activities:
        student = student_activity.student

        # Always use the total score from StudentActivity
        selected_score = student_activity.total_score
        max_score = activity.max_score

        # Calculate the correct passing score
        if activity.passing_score_type == 'percentage':
            passing_score_value = (activity.passing_score / 100) * max_score
        else:
            passing_score_value = activity.passing_score

        question_details = []
        latest_submission_time = None

        # Get all StudentQuestions related to this activity and student
        student_questions = select_canonical_details(student_activity)

        for i, detail in enumerate(student_questions, start=1):
            question = detail.activity_question
            if question is None:
                continue

            def _img_html(url, alt):
                return (
                    f'<img src="{url}" alt="{alt}" '
                    f'class="answer-thumb" '
                    f'onclick="window.open(this.src,\'_blank\')" />'
                )

            # --- Resolve the correct-answer display (text + image when available) ---
            display_correct_answer = question.correct_answer

            if question.quiz_type.name == 'Multiple Choice':
                choices = list(question.choices.all())
                correct_choice = None
                # Correct answer is stored as the choice index (string).
                try:
                    correct_index = int(question.correct_answer)
                    if 0 <= correct_index < len(choices):
                        correct_choice = choices[correct_index]
                except (ValueError, TypeError):
                    # Fall back to matching by text in case index isn't stored.
                    correct_choice = next(
                        (c for c in choices if c.choice_text and c.choice_text == question.correct_answer),
                        None,
                    )
                if correct_choice is not None:
                    parts = []
                    if correct_choice.choice_image:
                        parts.append(_img_html(correct_choice.choice_image.url, "Correct answer image"))
                    if correct_choice.choice_text:
                        parts.append(f"<span>{correct_choice.choice_text}</span>")
                    if parts:
                        display_correct_answer = "".join(parts)

            elif question.quiz_type.name == 'Matching Type':
                display_correct_answer = question.correct_answer.replace("->", "→")

            # --- Resolve the student-answer display (text + image when available) ---
            qtype = detail.activity_question.quiz_type.name

            if qtype == 'Document' and detail.uploaded_file:
                ext = (detail.uploaded_file.name or '').rsplit('.', 1)[-1].lower()
                if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'):
                    student_answer_display = (
                        _img_html(detail.uploaded_file.url, "Submitted document")
                        + f"<a href='{detail.uploaded_file.url}' target='_blank'>"
                          f"<i class='fas fa-up-right-from-square'></i> Open file</a>"
                    )
                else:
                    student_answer_display = (
                        f"<a href='{detail.uploaded_file.url}' target='_blank'>"
                        f"<i class='fas fa-file-arrow-down'></i> Download document</a>"
                    )
            elif qtype == 'Multiple Choice':
                ans_raw = (detail.student_answer or '').strip()
                if ans_raw:
                    choices = list(question.choices.all())
                    chosen = None
                    # Stored answer is normally "cid:<choice_id>" — the canonical
                    # form. Legacy attempts may have stored the choice text or a
                    # positional index, so fall back to those.
                    if ans_raw.lower().startswith('cid:'):
                        try:
                            cid = int(ans_raw.split(':', 1)[1])
                            chosen = next((c for c in choices if c.id == cid), None)
                        except (ValueError, TypeError):
                            pass
                    if chosen is None:
                        chosen = next(
                            (c for c in choices if c.choice_text and c.choice_text == ans_raw),
                            None,
                        )
                    if chosen is None:
                        try:
                            idx = int(ans_raw)
                            if 0 <= idx < len(choices):
                                chosen = choices[idx]
                        except (ValueError, TypeError):
                            pass
                    parts = []
                    if chosen and chosen.choice_image:
                        parts.append(_img_html(chosen.choice_image.url, "Selected choice image"))
                    if chosen and chosen.choice_text:
                        parts.append(f"<span>{chosen.choice_text}</span>")
                    elif chosen is None:
                        parts.append(f"<span>{ans_raw}</span>")
                    student_answer_display = "".join(parts) if parts else "No answer provided"
                else:
                    student_answer_display = "No answer provided"
            else:
                student_answer_display = detail.student_answer or "No answer provided"

            if activity.show_score:
                question_details.append({
                    'number': i,
                    'question_text': question.question_text,
                    'correct_answer': display_correct_answer, # Use the resolved answer
                    'student_answer': student_answer_display,
                    'score': detail.score,
                })
            else:
                question_details.append({
                    'number': i,
                    'question_text': detail.activity_question.question_text,
                    'student_answer': student_answer_display,
                    'score': 'Score hidden',
                    'correct_answer': 'Answer hidden',
                })

            if latest_submission_time is None or (detail.submission_time and detail.submission_time > latest_submission_time):
                latest_submission_time = detail.submission_time

        failed = passing_score_value > 0 and selected_score < passing_score_value
        # Classroom-mode activities are scored manually, so the failed-state
        # study prompt is suppressed for them in the template.
        related_lessons = list(activity.additional_modules.all()) if failed and not activity.classroom_mode else []

        detailed_scores.append({
            'student': student,
            'total_score': selected_score,
            'max_score': max_score,
            'passing_score_value': passing_score_value,
            'questions': question_details,
            'submission_time': latest_submission_time,
            'failed': failed,
            'related_lessons': related_lessons,
        })

    is_student_role = user.is_student
    subject = getattr(activity, 'subject', None)

    return render(request, 'gradebookcomponent/activityGrade/my-assessment-score.html', {
        'activity': activity,
        'detailed_scores': detailed_scores,
        'is_teacher_view': not is_student_role,
        'is_student_role': is_student_role,
        'subject': subject,
    })
