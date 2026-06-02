from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.contrib import messages
from django.core.files.storage import default_storage
from activity.models import (
    Activity, ActivityQuestion, QuestionChoice, Rubrics, RubricsItem,
    StudentActivity, StudentQuestion,
)
from activity.models import get_upload_file_instruction
from activity.utils.authorization import activity_has_submissions
from accounts.models import CustomUser


@login_required
@permission_required('activity.view_activityquestion', raise_exception=True)
def list_assessment_questions(request, activity_id):
    """Fetch and display questions for a specific activity, including choices for Multiple Choice questions."""
    activity = get_object_or_404(Activity, local_id=activity_id)
    questions = ActivityQuestion.objects.filter(activity=activity).prefetch_related('choices', 'quiz_type')
    choices = QuestionChoice.objects.filter(question__in=questions)

    try:
        role_name = request.user.role_name
    except AttributeError:
        role_name = ""
    is_student_role = role_name == 'student'

    is_direct_score = (
        not questions.exists()
        and StudentQuestion.objects.filter(activity=activity, is_participation=True).exists()
    )

    direct_score_rows = []
    if is_direct_score:
        sa_map = {
            sa.student_id: sa for sa in StudentActivity.objects.filter(activity=activity)
        }
        sq_score_map = {
            sq.student_id: sq.score
            for sq in StudentQuestion.objects.filter(activity=activity, is_participation=True)
        }
        if is_student_role:
            student_iter = [request.user]
        else:
            student_iter = CustomUser.objects.filter(
                subjectenrollment__subject=activity.subject,
                subjectenrollment__status='enrolled',
            ).distinct().order_by('last_name', 'first_name')

        for student in student_iter:
            sa = sa_map.get(student.id)
            score = sq_score_map.get(student.id)
            if score is None and sa:
                score = sa.total_score
            direct_score_rows.append({
                'student': student,
                'score': score,
                'max_score': activity.max_score,
                'submission_date': sa.end_time if sa else None,
                'is_submitted': bool(sa and (sa.retake_count or 0) >= 1),
                'feedback': sa.feedback if sa else '',
            })

    return render(request, 'activity/question/list_question.html', {
        'activity': activity,
        'questions': questions,
        'choices': choices,
        'is_student_role': is_student_role,
        'has_submissions': activity_has_submissions(activity),
        'is_direct_score': is_direct_score,
        'direct_score_rows': direct_score_rows,
    })


@login_required
@permission_required('activity.change_activityquestion', raise_exception=True)
def edit_assessment_question(request, activity_id, question_id):
    """Fetch and edit a specific question for an activity."""
    activity = get_object_or_404(Activity, local_id=activity_id)
    question = get_object_or_404(ActivityQuestion, local_id=question_id, activity=activity)

    if activity_has_submissions(activity):
        messages.error(
            request,
            "This question can no longer be edited because at least one student has already submitted an attempt."
        )
        return redirect('list-assessment-questions', activity_id=activity.id)

    left_choices = list(QuestionChoice.objects.filter(question=question, is_left_side=True))
    right_choices = list(QuestionChoice.objects.filter(question=question, is_left_side=False))

    matching_pairs = list(zip(left_choices, right_choices[:len(left_choices)]))
    extra_right_choices = right_choices[len(left_choices):]
    
    rubric_items = []
    total_rubric_percentage = 0
    if question.quiz_type.name in ['Essay', 'Document']:
        rubric_items = RubricsItem.objects.filter(activity_question=question)
        total_rubric_percentage = sum(float(item.point) for item in rubric_items)

    if request.method == "POST":
        question.question_text = request.POST.get('question_text', '')
        question.score = float(request.POST.get('score', 0))
        
        # Handle instruction file removal
        remove_instruction = request.POST.get('remove_instruction', '0') == '1'
        if remove_instruction and question.question_instruction:
            try:
                default_storage.delete(question.question_instruction.name)
            except Exception:
                pass
            question.question_instruction = None
        
        # Handle instruction file upload
        uploaded_instruction = request.FILES.get('question_instruction')
        if uploaded_instruction:
            # Delete old instruction file if it exists
            if question.question_instruction:
                try:
                    default_storage.delete(question.question_instruction.name)
                except Exception:
                    pass
            # Save new instruction file
            file_path = default_storage.save(get_upload_file_instruction(None, uploaded_instruction.name), uploaded_instruction)
            question.question_instruction = file_path

        if 'choices' in request.POST:
            # Multiple Choice editing supports text, image, or both per choice.
            # Form fields per choice index <idx>:
            #   choices                  — text (may be empty if image-only)
            #   choice_image_<idx>       — uploaded file (optional)
            #   keep_image_<idx>=1       — preserve existing image when no new upload
            # Update existing rows in place to preserve PKs (StudentQuestion
            # answers reference choice IDs).
            choices_text = request.POST.getlist('choices')
            correct_choice_text = request.POST.get('correct_answer', '')

            existing = list(
                QuestionChoice.objects.filter(question=question, is_left_side=False)
                .order_by('id')
            )

            for idx, text in enumerate(choices_text):
                new_image = request.FILES.get(f'choice_image_{idx}')
                keep_existing = request.POST.get(f'keep_image_{idx}') == '1'

                if idx < len(existing):
                    choice = existing[idx]
                    choice.choice_text = text or ''
                    if new_image:
                        choice.choice_image = new_image
                    elif not keep_existing:
                        choice.choice_image = None
                    choice.save()
                else:
                    choice = QuestionChoice(question=question, choice_text=text or '')
                    if new_image:
                        choice.choice_image = new_image
                    choice.save()

            for stale in existing[len(choices_text):]:
                stale.delete()

            question.correct_answer = correct_choice_text

        elif question.quiz_type.name == 'Matching Type':
            left_texts = request.POST.getlist('matching_left', [])
            right_texts = request.POST.getlist('matching_right', [])
            extra_rights = request.POST.getlist('extra_right', [])

            QuestionChoice.objects.filter(question=question).delete()

            for left in left_texts:
                QuestionChoice.objects.create(question=question, choice_text=left, is_left_side=True)

            for right in right_texts:
                QuestionChoice.objects.create(question=question, choice_text=right, is_left_side=False)

            for extra in extra_rights:
                QuestionChoice.objects.create(question=question, choice_text=extra, is_left_side=False)

            question.correct_answer = ", ".join([f"{left} -> {right}" for left, right in zip(left_texts, right_texts)])

        elif question.quiz_type.name == 'True/False':
            question.correct_answer = request.POST.get('correct_answer', '')

        elif question.quiz_type.name in ['Calculated Numeric', 'Fill in the Blank']:
            question.correct_answer = request.POST.get('correct_answer', '')
            
        elif question.quiz_type.name in ['Essay', 'Document']:
            rubric_id_list = request.POST.getlist('rubric_id')
            rubric_points = request.POST.getlist('rubric_points')
            
            total_percentage = sum(float(point) for point in rubric_points if point)
            if abs(total_percentage - 100) > 0.01:
                messages.error(request, "Total rubric percentage must equal 100%. Current total: {}%".format(total_percentage))
                return redirect('edit-assessment-question', activity_id=activity_id, question_id=question_id)
            
            RubricsItem.objects.filter(activity_question=question).delete()
            
            for rubric_id, point in zip(rubric_id_list, rubric_points):
                if rubric_id and point:
                    try:
                        rubric = Rubrics.objects.get(local_id=rubric_id)
                        RubricsItem.objects.create(
                            activity_question=question,
                            rubric=rubric,
                            point=float(point)
                        )
                    except Rubrics.DoesNotExist:
                        messages.error(request, f"Rubric with ID {rubric_id} does not exist.")
                    except Exception as e:
                        messages.error(request, f"Error saving rubric item: {str(e)}")

        question.save()
        messages.success(request, "Question updated successfully.")
        return redirect('list-assessment-questions', activity_id=activity_id)

    return render(request, 'activity/question/edit_question.html', {
        'activity': activity,
        'subject': activity.subject,
        'question': question,
        'matching_pairs': matching_pairs,
        'extra_right_choices': extra_right_choices,
        'rubric_items': rubric_items,
        'total_rubric_percentage': total_rubric_percentage
    })


@login_required
@permission_required('activity.delete_activityquestion', raise_exception=True)
def delete_assessment_question(request, activity_id, question_id):
    """Delete a specific question from an activity."""
    if request.method == "POST":
        question = get_object_or_404(ActivityQuestion, local_id=question_id, activity_id=activity_id)
        if activity_has_submissions(question.activity):
            return JsonResponse(
                {"error": "Cannot delete: a student has already submitted an attempt for this activity."},
                status=409,
            )
        question.delete()
        return JsonResponse({"message": "Question deleted successfully"}, status=200)

    return JsonResponse({"error": "Invalid request"}, status=400)
