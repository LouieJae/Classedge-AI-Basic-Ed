from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.core.files.storage import default_storage
from io import TextIOWrapper
import csv
import os
import uuid
from activity.models import (Activity, ActivityQuestion, QuestionChoice, QuizType, StudentActivity, StudentQuestion, Rubrics, RubricsItem, get_upload_path)
from accounts.models import CustomUser
from subject.models import Subject
from activity.send_email_utils import send_activity_assignment_emails

# Add question to quiz
@method_decorator(login_required, name='dispatch')
class AddQuestionView(View):
    def get(self, request, activity_id, quiz_type_id):
        session_data = request.session.get('questions', {})
        try:
            activity = get_object_or_404(Activity, pk=activity_id)
            quiz_type = get_object_or_404(QuizType, id=quiz_type_id)

            current_semester = None
            if quiz_type.name == 'Participation':
                current_semester = activity.term.semester if activity.term else None
                students = CustomUser.objects.filter(
                    subjectenrollment__subject=activity.subject,
                    subjectenrollment__semester=current_semester,
                    subjectenrollment__status='enrolled'
                ).distinct()
                return render(request, 'course/participation/addParticipation.html', {
                    'activity': activity,
                    'quiz_type': quiz_type,
                    'students': students
                })

            # Handle other quiz types
            return render(request, 'activity/question/create_question.html', {
                'activity': activity,
                'quiz_type': quiz_type,
            })

        except Exception:
            messages.error(request, 'An error occurred while loading the question form.')
            return redirect('error')

    def post(self, request, activity_id, quiz_type_id):
        try:
            try:
                activity = Activity.objects.get(pk=activity_id)
            except Activity.DoesNotExist:
                messages.error(request, "The selected activity does not exist.")
                return redirect('error')
            quiz_type = get_object_or_404(QuizType, id=quiz_type_id)

        except Activity.DoesNotExist:
            messages.error(request, 'Activity does not exist.')
            return redirect('error')
        except QuizType.DoesNotExist:
            messages.error(request, 'Quiz type does not exist.')
            return redirect('error')
        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {str(e)}")
            return redirect('error')

        matching_left = []
        matching_right = []
        extra_right = []

        # Participation / Direct Score — direct-score persistence.
        # Skip the session/save_all_questions detour: write StudentQuestion +
        # StudentActivity rows immediately and land back on the assessment list.
        if quiz_type.name in ('Participation', 'Direct Score'):
            max_score = request.POST.get('max_score')
            if not max_score:
                messages.error(request, "Max score is required.")
                return self.get(request, activity_id, quiz_type_id)
            try:
                max_score = float(max_score)
                if max_score <= 0:
                    raise ValueError("Max score must be greater than 0.")
            except ValueError:
                messages.error(request, "Invalid max score provided.")
                return self.get(request, activity_id, quiz_type_id)

            students = CustomUser.objects.filter(
                subjectenrollment__subject=activity.subject,
                subjectenrollment__status='enrolled'
            ).distinct()

            with transaction.atomic():
                activity.max_score = max_score
                activity.save(update_fields=['max_score'])

                # Replace any prior participation rows for this activity so
                # re-saving from the roster overwrites instead of duplicating.
                StudentQuestion.objects.filter(activity=activity, is_participation=True).delete()

                new_rows = []
                touched_student_activities = []
                for student in students:
                    raw = request.POST.get(f'score_{student.id}', 0)
                    try:
                        score = float(raw or 0)
                    except (TypeError, ValueError):
                        score = 0
                    if score < 0:
                        score = 0
                    if score > max_score:
                        messages.error(request, f"Score for {student.get_full_name()} exceeds maximum score")
                        return self.get(request, activity_id, quiz_type_id)

                    new_rows.append(
                        StudentQuestion(
                            student=student,
                            activity=activity,
                            activity_question=None,
                            score=score,
                            student_answer=None,
                            uploaded_file=None,
                            is_participation=True,
                        )
                    )
                    sa, _created = StudentActivity.objects.get_or_create(
                        student=student,
                        activity=activity,
                        defaults={'subject': activity.subject, 'total_score': score},
                    )
                    sa.total_score = score
                    sa.subject = activity.subject
                    sa.end_time = timezone.now()
                    if (sa.retake_count or 0) < 1:
                        sa.retake_count = 1
                    touched_student_activities.append(sa)

                if new_rows:
                    StudentQuestion.objects.bulk_create(new_rows, batch_size=200)
                if touched_student_activities:
                    StudentActivity.objects.bulk_update(
                        touched_student_activities,
                        ['total_score', 'subject', 'end_time', 'retake_count'],
                    )

            # Drop any stale session draft for this activity so the global
            # "Save All" flow can't double-write the same scores later.
            session_questions = request.session.get('questions', {}) or {}
            if str(activity_id) in session_questions:
                session_questions.pop(str(activity_id), None)
                request.session['questions'] = session_questions
                request.session.modified = True

            messages.success(request, "Major Assessment scores saved.")
            return redirect('assessment-list')

        # MC CSV Import
        if quiz_type.name == 'Multiple Choice' and 'csv_file' in request.FILES:
            csv_file = request.FILES['csv_file']
            csv_data = TextIOWrapper(csv_file.file, encoding='utf-8')
            reader = csv.reader(csv_data)

            questions = request.session.get('questions', {})
            if str(activity_id) not in questions:
                questions[str(activity_id)] = []

            imported_score = 0
            for row in reader:
                if len(row) >= 2:
                    question_text = row[0].strip().replace('"', '')
                    points = float(row[1].strip().replace('"', ''))
                    choices = [choice.strip().replace('"', '') for choice in row[2:-1]]
                    correct_answer_text = row[-1].strip().replace('"', '')

                    print(
                        f"[MC CSV Import] Question='{question_text}', Points={points}, Choices={choices}, Correct='{correct_answer_text}'"
                    )

                    if correct_answer_text in choices:
                        correct_answer_index = choices.index(correct_answer_text)
                        print(f"[MC CSV Import] Storing correct_answer as index: {correct_answer_index}")
                    else:
                        messages.error(request, f"Correct answer '{correct_answer_text}' not found in choices for question: {question_text}")
                        return redirect('add_quiz_type', activity_id=activity.id)

                    question = {
                        'question_text': question_text,
                        'correct_answer': correct_answer_index,
                        'quiz_type': quiz_type.name,
                        'score': points,
                        'choices': choices
                    }
                    questions[str(activity_id)].append(question)
                    imported_score += points

            request.session['questions'] = questions
            # One-shot flag: the next render of the editor will treat the
            # session questions as a fresh import (auto-render, no
            # autosave "Restore" prompt).
            request.session[f'qc_skip_restore_{activity_id}'] = True
            request.session.modified = True

            total_score = sum(q['score'] for q in questions[str(activity_id)])
            if total_score > 0:
                activity.max_score = total_score
                activity.save(update_fields=['max_score'])

            return redirect('add_quiz_type', activity_id=activity.id)

        # Normal question submission
        question_text = request.POST.get('question_text', '')
        correct_answer = ''
        score = float(request.POST.get('score', 0))

        if quiz_type.name == 'Document':
            uploaded_file = request.FILES.get('document_file')
            if uploaded_file:
                file_path = default_storage.save(get_upload_path(None, uploaded_file.name), uploaded_file)
                correct_answer = file_path

        choices = []
        choice_images = []
        if quiz_type.name == 'Multiple Choice':
            choices = request.POST.getlist('choices')
            raw_answer = request.POST.get('correct_answer')
            if not raw_answer and raw_answer != '0':
                messages.error(request, "Please select a correct answer for the Multiple Choice question.")
                return self.get(request, activity_id, quiz_type_id)
            correct_answer_index = int(raw_answer)
            if correct_answer_index < len(choices):
                correct_answer = correct_answer_index
            for i in range(len(choices)):
                img_file = request.FILES.get(f'choice_image_{i}')
                if img_file:
                    ext = os.path.splitext(img_file.name)[1]
                    img_path = default_storage.save(f'choiceImage/{uuid.uuid4()}{ext}', img_file)
                    choice_images.append(img_path)
                else:
                    choice_images.append(None)
        elif quiz_type.name == 'Matching Type':
            matching_left = request.POST.getlist('matching_left')
            matching_right = request.POST.getlist('matching_right')
            extra_right = request.POST.getlist('extra_right')
            correct_answer = ", ".join([f"{left} -> {right}" for left, right in zip(matching_left, matching_right)])
            _ = matching_right + extra_right
        elif quiz_type.name in ['True/False', 'Calculated Numeric', 'Fill in the Blank']:
            correct_answer = request.POST.get('correct_answer', '')

        rubric_items = []
        if quiz_type.name in ['Essay', 'Document']:
            rubric_id_list = request.POST.getlist('rubric_id')
            points_list = request.POST.getlist('rubric_points')

            if not rubric_id_list or not points_list or len(rubric_id_list) != len(points_list):
                messages.error(request, "Please add rubric criteria and points; they must total 100%.")
                return self.get(request, activity_id, quiz_type_id)

            total_percentage = 0
            for rubric_id, points in zip(rubric_id_list, points_list):
                if rubric_id.strip() and points.strip():
                    try:
                        point_value = float(points)
                        rubric_items.append({'rubric_id': rubric_id.strip(), 'point': point_value})
                    except ValueError:
                        messages.error(request, f"Invalid point value for rubric '{rubric_id}'")
                        return self.get(request, activity_id, quiz_type_id)

            total_percentage = sum(item['point'] for item in rubric_items)
            if total_percentage != 100:
                messages.error(request, f"Total rubric percentage is {total_percentage}%. It should be 100%.")
                return redirect('add_quiz_type', activity_id=activity.id)

        question_instruction = None
        uploaded_instruction = request.FILES.get('question_instruction')
        if uploaded_instruction:
            file_path = default_storage.save(get_upload_path(None, uploaded_instruction.name), uploaded_instruction)
            question_instruction = file_path

        question = {
            'question_text': question_text,
            'question_instruction': question_instruction,
            'correct_answer': correct_answer,
            'quiz_type': quiz_type.name,
            'score': score,
            'matching_left': matching_left,
            'matching_right': matching_right,
            'extra_right': extra_right,
            'choices': choices,
            'choice_images': choice_images,
            'rubric_items': rubric_items
        }

        questions = request.session.get('questions', {})
        if str(activity_id) not in questions:
            questions[str(activity_id)] = []

        existing_question = next((q for q in questions[str(activity_id)] if q['question_text'] == question_text), None)
        if not existing_question:
            questions[str(activity_id)].append(question)

        total_score = sum(q['score'] for q in questions[str(activity_id)])
        activity.max_score = total_score
        activity.save(update_fields=['max_score'])

        request.session['questions'] = questions
        request.session.modified = True
        return redirect('add_quiz_type', activity_id=activity.id)


# Add question to quiz (Classroom Mode)
@method_decorator(login_required, name='dispatch')
class AddQuestionViewCM(View):
    def get(self, request, activity_id, quiz_type_id):
        session_data = request.session.get('questions', {})
        try:
            activity = get_object_or_404(Activity, pk=activity_id)
            quiz_type = get_object_or_404(QuizType, id=quiz_type_id)

            current_semester = activity.term.semester if activity.term else None

            if quiz_type.name in ['Participation', 'Direct Score']:
                students = CustomUser.objects.filter(
                    subjectenrollment__subject=activity.subject,
                    subjectenrollment__semester=current_semester,
                    subjectenrollment__status='enrolled'
                ).distinct()
                return render(request, 'course/participation/addParticipation.html', {
                    'activity': activity,
                    'quiz_type': quiz_type,
                    'students': students
                })

            return render(request, 'activity/question/create_question_CM.html', {
                'activity': activity,
                'quiz_type': quiz_type,
            })

        except Exception:
            messages.error(request, 'An error occurred while loading the question form.')
            return redirect('error')

    def post(self, request, activity_id, quiz_type_id):
        try:
            try:
                activity = Activity.objects.get(pk=activity_id)
            except Activity.DoesNotExist:
                messages.error(request, "The selected activity does not exist.")
                return redirect('error')
            quiz_type = get_object_or_404(QuizType, id=quiz_type_id)

        except Activity.DoesNotExist:
            messages.error(request, 'Activity does not exist.')
            return redirect('error')
        except QuizType.DoesNotExist:
            messages.error(request, 'Quiz type does not exist.')
            return redirect('error')
        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {str(e)}")
            return redirect('error')

        matching_left = []
        matching_right = []
        extra_right = []

        # Direct-score persistence for Major Assessment / Direct Score in CM mode.
        if quiz_type.name in ['Participation', 'Direct Score']:
            max_score = request.POST.get('max_score')
            if not max_score:
                messages.error(request, "Max score is required.")
                return self.get(request, activity_id, quiz_type_id)
            try:
                max_score = float(max_score)
                if max_score <= 0:
                    raise ValueError("Max score must be greater than 0.")
            except ValueError:
                messages.error(request, "Invalid max score provided.")
                return self.get(request, activity_id, quiz_type_id)

            students = CustomUser.objects.filter(
                subjectenrollment__subject=activity.subject,
                subjectenrollment__status='enrolled'
            ).distinct()

            with transaction.atomic():
                activity.max_score = max_score
                activity.save(update_fields=['max_score'])
                StudentQuestion.objects.filter(activity=activity, is_participation=True).delete()

                new_rows = []
                touched_student_activities = []
                for student in students:
                    raw = request.POST.get(f'score_{student.id}', 0)
                    try:
                        score = float(raw or 0)
                    except (TypeError, ValueError):
                        score = 0
                    if score < 0:
                        score = 0
                    if score > max_score:
                        messages.error(request, f"Score for {student.get_full_name()} exceeds maximum score")
                        return self.get(request, activity_id, quiz_type_id)

                    new_rows.append(
                        StudentQuestion(
                            student=student,
                            activity=activity,
                            activity_question=None,
                            score=score,
                            student_answer=None,
                            uploaded_file=None,
                            is_participation=True,
                        )
                    )
                    sa, _created = StudentActivity.objects.get_or_create(
                        student=student,
                        activity=activity,
                        defaults={'subject': activity.subject, 'total_score': score},
                    )
                    sa.total_score = score
                    sa.subject = activity.subject
                    sa.end_time = timezone.now()
                    if (sa.retake_count or 0) < 1:
                        sa.retake_count = 1
                    touched_student_activities.append(sa)

                if new_rows:
                    StudentQuestion.objects.bulk_create(new_rows, batch_size=200)
                if touched_student_activities:
                    StudentActivity.objects.bulk_update(
                        touched_student_activities,
                        ['total_score', 'subject', 'end_time', 'retake_count'],
                    )

            session_questions = request.session.get('questions', {}) or {}
            if str(activity_id) in session_questions:
                session_questions.pop(str(activity_id), None)
                request.session['questions'] = session_questions
                request.session.modified = True

            messages.success(request, "Major Assessment scores saved.")
            return redirect('classroom_mode', pk=activity.subject.id)

        if quiz_type.name == 'Multiple Choice' and 'csv_file' in request.FILES:
            csv_file = request.FILES['csv_file']
            csv_data = TextIOWrapper(csv_file.file, encoding='utf-8')
            reader = csv.reader(csv_data)

            questions = request.session.get('questions', {})
            if str(activity_id) not in questions:
                questions[str(activity_id)] = []

            imported_score = 0
            for row in reader:
                if len(row) >= 2:
                    question_text = row[0].strip().replace('"', '')
                    points = float(row[1].strip().replace('"', ''))
                    choices = [choice.strip().replace('"', '') for choice in row[2:-1]]
                    correct_answer_text = row[-1].strip().replace('"', '')

                    print(
                        f"[MC CSV Import CM] Question='{question_text}', Points={points}, Choices={choices}, Correct='{correct_answer_text}'"
                    )

                    if correct_answer_text in choices:
                        correct_answer_index = choices.index(correct_answer_text)
                        print(f"[MC CSV Import CM] Storing correct_answer as index: {correct_answer_index}")
                    else:
                        messages.error(request, f"Correct answer '{correct_answer_text}' not found in choices for question: {question_text}")
                        return redirect('add_quiz_typeCM', activity_id=activity.id)

                    question = {
                        'question_text': question_text,
                        'correct_answer': correct_answer_index,
                        'quiz_type': quiz_type.name,
                        'score': points,
                        'choices': choices
                    }
                    questions[str(activity_id)].append(question)
                    imported_score += points

            request.session['questions'] = questions
            request.session[f'qc_skip_restore_{activity_id}'] = True
            request.session.modified = True

            total_score = sum(q['score'] for q in questions[str(activity_id)])
            if total_score > 0:
                activity.max_score = total_score
                activity.save(update_fields=['max_score'])

            return redirect('add_quiz_typeCM', activity_id=activity.id)

        # Normal question
        question_text = request.POST.get('question_text', '')
        correct_answer = ''
        score = float(request.POST.get('score', 0))

        if quiz_type.name == 'Document':
            uploaded_file = request.FILES.get('document_file')
            if uploaded_file:
                file_path = default_storage.save(get_upload_path(None, uploaded_file.name), uploaded_file)
                correct_answer = file_path

        choices = []
        choice_images = []
        if quiz_type.name == 'Multiple Choice':
            choices = request.POST.getlist('choices')
            raw_answer = request.POST.get('correct_answer')
            if not raw_answer and raw_answer != '0':
                messages.error(request, "Please select a correct answer for the Multiple Choice question.")
                return self.get(request, activity_id, quiz_type_id)
            correct_answer_index = int(raw_answer)
            if correct_answer_index < len(choices):
                correct_answer = correct_answer_index
            for i in range(len(choices)):
                img_file = request.FILES.get(f'choice_image_{i}')
                if img_file:
                    ext = os.path.splitext(img_file.name)[1]
                    img_path = default_storage.save(f'choiceImage/{uuid.uuid4()}{ext}', img_file)
                    choice_images.append(img_path)
                else:
                    choice_images.append(None)
        elif quiz_type.name == 'Matching Type':
            matching_left = request.POST.getlist('matching_left')
            matching_right = request.POST.getlist('matching_right')
            extra_right = request.POST.getlist('extra_right')
            correct_answer = ", ".join([f"{left} -> {right}" for left, right in zip(matching_left, matching_right)])
        elif quiz_type.name in ['True/False', 'Calculated Numeric', 'Fill in the Blank']:
            correct_answer = request.POST.get('correct_answer', '')

        question_instruction = None
        uploaded_instruction = request.FILES.get('question_instruction')
        if uploaded_instruction:
            file_path = default_storage.save(get_upload_path(None, uploaded_instruction.name), uploaded_instruction)
            question_instruction = file_path

        question = {
            'question_text': question_text,
            'question_instruction': question_instruction,
            'correct_answer': correct_answer,
            'quiz_type': quiz_type.name,
            'score': score,
            'matching_left': locals().get('matching_left', []),
            'matching_right': locals().get('matching_right', []),
            'extra_right': locals().get('extra_right', []),
            'choices': choices,
            'choice_images': choice_images,
        }

        questions = request.session.get('questions', {})
        if str(activity_id) not in questions:
            questions[str(activity_id)] = []

        existing_question = next((q for q in questions[str(activity_id)] if q['question_text'] == question_text), None)
        if not existing_question:
            questions[str(activity_id)].append(question)

        total_score = sum(q['score'] for q in questions[str(activity_id)])
        activity.max_score = total_score
        activity.save(update_fields=['max_score'])

        request.session['questions'] = questions
        request.session.modified = True
        return redirect('add_quiz_typeCM', activity_id=activity.id)


# Delete temporary question
@method_decorator(login_required, name='dispatch')
class DeleteTempQuestionView(View):
    def post(self, request, activity_id, index):
        questions = request.session.get('questions', {})
        activity_questions = questions.get(str(activity_id), [])

        if index < len(activity_questions):
            del activity_questions[index]

        questions[str(activity_id)] = activity_questions
        request.session['questions'] = questions

        return redirect('add_quiz_type', activity_id=activity_id)


# edit temporary question
# edit temporary question
@method_decorator(login_required, name='dispatch')
class UpdateQuestionView(View):
    def get(self, request, activity_id, index):
        questions = request.session.get('questions', {}).get(str(activity_id), [])
        activity = get_object_or_404(Activity, pk=activity_id)


        if index >= len(questions):
            return redirect('add_quiz_type', activity_id=activity_id)  # Redirect if index is out of range

        question = questions[index]

        question.setdefault('correct_answer', '')

    # Ensure matching pairs are properly structured
        question.setdefault('matching_left', [])
        question.setdefault('matching_right', [])
        question.setdefault('extra_right', [])

        matching_pairs = list(zip(question['matching_left'], question['matching_right']))

        # Initialize rubric items if not present
        question.setdefault('rubric_items', [])
        
        # Ensure each rubric item has complete rubric information
        for rubric_item in question.get('rubric_items', []):
            if 'rubric_id' in rubric_item and ('rubric' not in rubric_item or 'rubric_name' not in rubric_item.get('rubric', {})):
                try:
                    rubric = Rubrics.objects.get(id=rubric_item['rubric_id'])
                    # Add or update the rubric information
                    rubric_item['rubric'] = {
                        'id': rubric.id,
                        'rubric_name': rubric.rubric_name
                    }
                except Rubrics.DoesNotExist:
                    # If rubric doesn't exist, provide a placeholder
                    rubric_item['rubric'] = {
                        'id': rubric_item['rubric_id'],
                        'rubric_name': 'Unknown Rubric'
                    }
                
        # Calculate total rubric percentage
        total_rubric_percentage = 0
        for rubric_item in question.get('rubric_items', []):
            total_rubric_percentage += float(rubric_item.get('point', 0))

        # Get rubrics filtered by subject
        rubrics_queryset = Rubrics.objects.filter(subject=activity.subject)
        rubrics_data = [{'id': r.id, 'rubric_name': r.rubric_name} for r in rubrics_queryset]
        
        return render(request, 'activity/question/update_question.html', {
            'activity_id': activity_id,
            'activity': activity,
            'subject': activity.subject,
            'index': index,
            'question': question,
            'matching_pairs': matching_pairs,  # Pass zipped pairs directly
            'extra_right': question['extra_right'],
            'rubric_items': question.get('rubric_items', []),
            'total_rubric_percentage': total_rubric_percentage,
            'rubrics': rubrics_data,
        })

    def post(self, request, activity_id, index):
        questions = request.session.get('questions', {}).get(str(activity_id), [])
        if index >= len(questions):
            return redirect('add_quiz_type', activity_id=activity_id)  # Redirect if index is out of range

        question = questions[index]
        question['question_text'] = request.POST.get('question_text', '')
        question['score'] = float(request.POST.get('score', 0))

        # Handle Multiple Choice (correct answer should be the index of the selected choice)
        if 'choices' in request.POST:
            question['choices'] = request.POST.getlist('choices')
            
            # Fetch the correct answer index from the form
            correct_answer_index = request.POST.get('correct_answer', None)
            if correct_answer_index is not None:
                correct_answer_index = int(correct_answer_index) 
                if 0 <= correct_answer_index <= len(question['choices']):
                    question['correct_answer'] = correct_answer_index

        # For other types, handle correct answer normally
        elif question['quiz_type'] == 'Matching Type':
            matching_left = request.POST.getlist('matching_left')
            matching_right = request.POST.getlist('matching_right')
            extra_right = request.POST.getlist('extra_right', [])
            
            # Update the matching pairs and extra options
            question['correct_answer'] = ", ".join([f"{left} -> {right}" for left, right in zip(matching_left, matching_right)])
            question['matching_left'] = matching_left
            question['matching_right'] = matching_right
            question['extra_right'] = extra_right

        # Handle True/False questions
        elif question['quiz_type'] == 'True/False':
            question['correct_answer'] = request.POST.get('correct_answer', '')

        # Handle Calculated Numeric or Fill in the Blank questions
        elif question['quiz_type'] in ['Calculated Numeric', 'Fill in the Blank']:
            question['correct_answer'] = request.POST.get('correct_answer', '')

        # Handle Document questions
        elif question['quiz_type'] == 'Document':
            if 'document_file' in request.FILES:
                uploaded_file = request.FILES.get('document_file')
                file_path = default_storage.save(get_upload_path(None, uploaded_file.name), uploaded_file)
                question['correct_answer'] = file_path

        # Handle rubric items for Essay and Document question types
        if question['quiz_type'] in ['Essay', 'Document']:
            rubric_ids = request.POST.getlist('rubric_id')
            rubric_points = request.POST.getlist('rubric_points')
            
            # Create rubric items list
            rubric_items = []
            total_points = 0
            
            for i in range(len(rubric_ids)):
                if i < len(rubric_points) and rubric_ids[i]:
                    point = float(rubric_points[i])
                    total_points += point
                    
                    # Get rubric details
                    try:
                        rubric = Rubrics.objects.get(id=rubric_ids[i])
                        rubric_items.append({
                            'rubric_id': rubric_ids[i],
                            'rubric': {
                                'id': rubric.id,
                                'rubric_name': rubric.rubric_name
                            },
                            'point': point
                        })
                    except Rubrics.DoesNotExist:
                        continue
            
            # Validate total points
            if abs(total_points - 100) > 0.01:
                messages.error(request, "Total rubric points must equal 100%")
                # Re-render the form with error
                return self.get(request, activity_id, index)
                
            # Save rubric items to question
            question['rubric_items'] = rubric_items

        # Update the specific question in the list
        questions[index] = question

        # Update the session
        request.session['questions'][str(activity_id)] = questions

        # Ensure the session is saved
        request.session.modified = True

        return redirect('add_quiz_type', activity_id=activity_id)


# edit temporary question (Classroom Mode)
@method_decorator(login_required, name='dispatch')
class UpdateQuestionViewCM(View):
    def get(self, request, activity_id, index):
        activity = get_object_or_404(Activity, pk=activity_id)
        subject = activity.subject
        subject_id = activity.subject.id
        subject = get_object_or_404(Subject, id=subject_id)
        questions = request.session.get('questions', {}).get(str(activity_id), [])
        if index >= len(questions):
            return redirect('add_quiz_type', activity_id=activity_id)

        question = questions[index]
        question.setdefault('correct_answer', '')
        question.setdefault('matching_left', [])
        question.setdefault('matching_right', [])
        question.setdefault('extra_right', [])

        matching_pairs = list(zip(question['matching_left'], question['matching_right']))
        question.setdefault('rubric_items', [])

        total_rubric_percentage = 0
        for rubric_item in question.get('rubric_items', []):
            total_rubric_percentage += float(rubric_item.get('point', 0))

        # Filter rubrics by subject
        rubrics = Rubrics.objects.filter(subject=activity.subject)

        return render(request, 'activity/question/update_question_CM.html', {
            'activity_id': activity_id,
            'activity': activity,
            'index': index,
            'subject': subject,
            'question': question,
            'matching_pairs': matching_pairs,
            'extra_right': question['extra_right'],
            'rubric_items': question.get('rubric_items', []),
            'total_rubric_percentage': total_rubric_percentage,
            'rubrics': rubrics,
        })

    def post(self, request, activity_id, index):
        questions = request.session.get('questions', {}).get(str(activity_id), [])
        if index >= len(questions):
            return redirect('add_quiz_typeCM', activity_id=activity_id)

        question = questions[index]
        question['question_text'] = request.POST.get('question_text', '')
        question['score'] = float(request.POST.get('score', 0))

        if 'choices' in request.POST:
            question['choices'] = request.POST.getlist('choices')
            correct_answer_index = request.POST.get('correct_answer', None)
            if correct_answer_index is not None:
                correct_answer_index = int(correct_answer_index) + 1
                if 0 <= correct_answer_index <= len(question['choices']):
                    question['correct_answer'] = correct_answer_index

        elif question['quiz_type'] == 'Matching Type':
            matching_left = request.POST.getlist('matching_left')
            matching_right = request.POST.getlist('matching_right')
            extra_right = request.POST.getlist('extra_right', [])
            question['correct_answer'] = ", ".join([f"{left} -> {right}" for left, right in zip(matching_left, matching_right)])
            question['matching_left'] = matching_left
            question['matching_right'] = matching_right
            question['extra_right'] = extra_right

        elif question['quiz_type'] == 'True/False':
            question['correct_answer'] = request.POST.get('correct_answer', '')

        elif question['quiz_type'] in ['Calculated Numeric', 'Fill in the Blank']:
            question['correct_answer'] = request.POST.get('correct_answer', '')

        elif question['quiz_type'] == 'Document':
            if 'document_file' in request.FILES:
                uploaded_file = request.FILES.get('document_file')
                file_path = default_storage.save(get_upload_path(None, uploaded_file.name), uploaded_file)
                question['correct_answer'] = file_path

        if question['quiz_type'] in ['Essay', 'Document']:
            rubric_ids = request.POST.getlist('rubric_id')
            rubric_points = request.POST.getlist('rubric_points')
            rubric_items = []
            total_points = 0
            for i in range(len(rubric_ids)):
                if i < len(rubric_points) and rubric_ids[i]:
                    point = float(rubric_points[i])
                    total_points += point
                    try:
                        rubric = Rubrics.objects.get(id=rubric_ids[i])
                        rubric_items.append({
                            'rubric_id': rubric_ids[i],
                            'rubric': {
                                'id': rubric.id,
                                'rubric_name': rubric.rubric_name
                            },
                            'point': point
                        })
                    except Rubrics.DoesNotExist:
                        continue

            if abs(total_points - 100) > 0.01:
                messages.error(request, "Total rubric points must equal 100%")
                return self.get(request, activity_id, index)

            question['rubric_items'] = rubric_items

        questions[index] = question
        request.session['questions'][str(activity_id)] = questions
        request.session.modified = True
        return redirect('add_quiz_typeCM', activity_id=activity_id)


# Save all created questions
@method_decorator(login_required, name='dispatch')
class SaveAllQuestionsView(View):
    @transaction.atomic
    def post(self, request, activity_id):
        activity = get_object_or_404(Activity, pk=activity_id)
        questions = request.session.get('questions', {}).get(str(activity_id), [])

        if not questions:
            messages.error(request, "No questions were saved. Please add at least one question and click Save All again.")
            return redirect('add_quiz_type', activity_id=activity_id)

        total_score = 0
        current_semester = activity.term.semester if activity.term else None

        try:
            if activity.remedial:
                students = list(StudentActivity.objects.filter(activity=activity).select_related('student').values_list('student', flat=True))
                students = CustomUser.objects.filter(id__in=students)
            else:
                students = CustomUser.objects.filter(
                    profile__role__name__iexact='Student',
                    subjectenrollment__subject=activity.subject,
                    subjectenrollment__semester=current_semester,
                    subjectenrollment__status='enrolled'
                ).distinct()

            student_list = list(students)
            student_questions = []
            student_activities_to_update = []

            for question_data in questions:
                quiz_type = get_object_or_404(QuizType, name=question_data['quiz_type'])

                if quiz_type.name == 'Participation':
                    participation_data = question_data.get('participation_data', [])
                    for participation in participation_data:
                        student = CustomUser.objects.get(id=participation['student_id'])
                        student_questions.append(
                            StudentQuestion(
                                student=student,
                                activity=activity,
                                activity_question=None,
                                score=participation['score'],
                                student_answer=None,
                                uploaded_file=None,
                                is_participation=True
                            )
                        )

                        student_activity, created = StudentActivity.objects.get_or_create(
                            student=student,
                            activity=activity,
                            defaults={'total_score': participation['score'], 'subject': activity.subject}
                        )
                        if not created:
                            student_activity.total_score += participation['score']
                            student_activities_to_update.append(student_activity)
                else:
                    question = ActivityQuestion.objects.create(
                        activity=activity,
                        subject=activity.subject,
                        question_text=question_data['question_text'],
                        correct_answer=question_data['correct_answer'],
                        quiz_type=quiz_type,
                        score=question_data.get('score', 0),
                        question_instruction=question_data.get('question_instruction')
                    )

                    if quiz_type.name == 'Multiple Choice':
                        choices_list = question_data.get('choices', [])
                        images_list = question_data.get('choice_images', [None] * len(choices_list))
                        choices = [
                            QuestionChoice(
                                question=question,
                                choice_text=text,
                                choice_image=img_path,
                                subject=activity.subject,
                            )
                            for text, img_path in zip(choices_list, images_list)
                        ]
                        QuestionChoice.objects.bulk_create(choices)

                    if quiz_type.name == 'Matching Type':
                        choices = []
                        matching_left = question_data.get('matching_left', [])
                        matching_right = question_data.get('matching_right', [])
                        extra_right = question_data.get('extra_right', [])

                        for left, right in zip(matching_left, matching_right):
                            choices.extend([
                                QuestionChoice(question=question, choice_text=left, is_left_side=True, subject=activity.subject),
                                QuestionChoice(question=question, choice_text=right, is_left_side=False, subject=activity.subject)
                            ])

                        for right in extra_right:
                            choices.append(QuestionChoice(question=question, choice_text=right, is_left_side=False, subject=activity.subject))

                        if choices:
                            QuestionChoice.objects.bulk_create(choices)

                    if quiz_type.name in ['Essay', 'Document']:
                        rubric_items = question_data.get('rubric_items', [])
                        rubric_objects = []
                        for rubric_item in rubric_items:
                            rubric_id = rubric_item.get('rubric_id')
                            point = rubric_item.get('point')
                            if rubric_id and point is not None:
                                rubric = get_object_or_404(Rubrics, id=rubric_id)
                                rubric_objects.append(
                                    RubricsItem(
                                        activity_question=question,
                                        rubric=rubric,
                                        point=point
                                    )
                                )
                        if rubric_objects:
                            RubricsItem.objects.bulk_create(rubric_objects)

                    total_score += question_data.get('score', 0)

            if student_questions:
                StudentQuestion.objects.bulk_create(student_questions, batch_size=100)

            if student_activities_to_update:
                StudentActivity.objects.bulk_update(student_activities_to_update, ['total_score'])

            if total_score > 0:
                activity.max_score = total_score
                activity.save(update_fields=['max_score'])

            request.session.pop('questions', None)
            request.session.modified = True
            
            send_activity_assignment_emails(students, activity)

        except Exception as e:
            messages.error(request, f"Couldn't save questions: {e}. Your work is still here — try Save All again.")
            return redirect('add_quiz_type', activity_id=activity_id)

        subject_id = activity.subject.id if activity.subject else 1
        return redirect(f'/material/list/{subject_id}/?view=assessments')


# Save all created questions (Classroom Mode)
@method_decorator(login_required, name='dispatch')
class SaveAllQuestionsViewCM(View):
    def post(self, request, activity_id):
        activity = get_object_or_404(Activity, pk=activity_id)
        questions = request.session.get('questions', {}).get(str(activity_id), [])

        if not questions:
            messages.error(request, "No questions found in session.")
            return redirect('error')

        total_score = 0
        current_semester = activity.term.semester if activity.term else None

        try:
            if activity.remedial:
                students = StudentActivity.objects.filter(activity=activity).select_related('student')
                students = [sa.student for sa in students]
            else:
                students = CustomUser.objects.filter(
                    profile__role__name__iexact='Student',
                    subjectenrollment__subject=activity.subject,
                    subjectenrollment__semester=current_semester,
                    subjectenrollment__status='enrolled'
                ).distinct()

            for question_data in questions:
                quiz_type = get_object_or_404(QuizType, name=question_data['quiz_type'])

                if quiz_type.name in ['Participation', 'Direct Score']:
                    participation_data = question_data.get('participation_data', [])
                    for participation in participation_data:
                        student = CustomUser.objects.get(id=participation['student_id'])
                        StudentQuestion.objects.create(
                            student=student,
                            activity=activity,
                            activity_question=None,
                            score=participation['score'],
                            student_answer=None,
                            uploaded_file=None,
                            is_participation=True if quiz_type.name == 'Participation' else False
                        )
                        student_activity, created = StudentActivity.objects.get_or_create(
                            student=student,
                            activity=activity,
                            defaults={'total_score': 0, 'subject': activity.subject}
                        )
                        student_activity.total_score += participation['score']
                        file_path = participation.get('file_path')
                        if file_path:
                            student_activity.file = file_path
                        student_activity.save()
                else:
                    question = ActivityQuestion.objects.create(
                        activity=activity,
                        subject=activity.subject,
                        question_text=question_data['question_text'],
                        correct_answer=question_data['correct_answer'],
                        quiz_type=quiz_type,
                        score=question_data.get('score', 0),
                        question_instruction=question_data.get('question_instruction')
                    )

                    if quiz_type.name == 'Multiple Choice':
                        choices_list = question_data.get('choices', [])
                        images_list = question_data.get('choice_images', [None] * len(choices_list))
                        for text, img_path in zip(choices_list, images_list):
                            QuestionChoice.objects.create(question=question, choice_text=text, choice_image=img_path)

                    if quiz_type.name == 'Matching Type':
                        matching_left = question_data.get('matching_left', [])
                        matching_right = question_data.get('matching_right', [])
                        extra_right = question_data.get('extra_right', [])
                        for left, right in zip(matching_left, matching_right):
                            QuestionChoice.objects.create(question=question, choice_text=left, is_left_side=True)
                            QuestionChoice.objects.create(question=question, choice_text=right, is_left_side=False)
                        for right in extra_right:
                            QuestionChoice.objects.create(question=question, choice_text=right, is_left_side=False)

                    total_score += question_data.get('score', 0)

            if total_score > 0:
                activity.max_score = total_score
                activity.save(update_fields=['max_score'])

            request.session.pop('questions', None)
            request.session.modified = True

        except Exception as e:
            messages.error(request, f"An error occurred: {e}")
            return redirect('error')

        return redirect('classroom_mode', pk=activity.subject.id)


@method_decorator(login_required, name='dispatch')
class ApplyDefaultPointsView(View):
    def post(self, request, activity_id):
        activity = get_object_or_404(Activity, pk=activity_id)
        default = request.session.get(f'default_points_{activity_id}')
        if default is None:
            messages.info(request, "No default points set on this assessment.")
            return redirect('add_quiz_type', activity_id=activity.id)

        questions = request.session.get('questions', {})
        bucket = questions.get(str(activity_id), [])
        for q in bucket:
            if q.get('quiz_type') != 'Participation':
                q['score'] = float(default)
        questions[str(activity_id)] = bucket
        request.session['questions'] = questions
        request.session.modified = True
        messages.success(request, f"Applied default {default} to {len(bucket)} question(s).")
        return redirect('add_quiz_type', activity_id=activity.id)


@method_decorator(login_required, name='dispatch')
class SetDefaultPointsView(View):
    def post(self, request, activity_id):
        raw = request.POST.get('default_points', '').strip()
        if raw:
            try:
                request.session[f'default_points_{activity_id}'] = float(raw)
            except ValueError:
                messages.error(request, "Invalid points value.")
                return redirect('add_quiz_type', activity_id=activity_id)
        else:
            request.session.pop(f'default_points_{activity_id}', None)
        request.session.modified = True
        return redirect('add_quiz_type', activity_id=activity_id)
