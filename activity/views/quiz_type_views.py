import json
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required
from django.views import View
from django.conf import settings
from django.urls import reverse
from activity.models import Activity, QuizType, Rubrics
from subject.models import Subject
from activity.utils.authorization import check_activity_access

logger = logging.getLogger(__name__)

# Add quiz type
@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('quiztype.add_quiztype', raise_exception=True), name='dispatch')
class AddQuizTypeView(View):
    def get(self, request, activity_id):
        try:
            # ===== SESSION VALIDATION =====
            # Check if there's a current activity in session (from create activity flow)
            session_activity_id = request.session.get('current_activity_id')
            if session_activity_id and session_activity_id != activity_id:
                # URL was manipulated - redirect to correct activity ID
                messages.warning(request, "Redirected to your current activity.")
                return redirect(reverse('add_quiz_type', kwargs={'activity_id': session_activity_id}))
            # ===== END SESSION VALIDATION =====
            
            activity = get_object_or_404(Activity, pk=activity_id)

            # ===== AUTHORIZATION CHECK =====
            has_access, redirect_response = check_activity_access(request, activity, require_teacher=True)
            if not has_access:
                return redirect_response
            # ===== END AUTHORIZATION CHECK =====

            quiz_types = QuizType.objects.all()

            is_participation = activity.activity_type.name == 'Participation'

            # Major Assessment is direct-scoring — bypass the question/picker UI
            # and land on the student-score roster directly. Applies even when
            # the page is reached after creation (e.g. from the activity list).
            if is_participation:
                participation_qt = QuizType.objects.filter(name='Participation').first()
                if participation_qt:
                    return redirect(reverse('add_question', kwargs={
                        'activity_id': activity.id,
                        'quiz_type_id': participation_qt.id,
                    }))

            questions = request.session.get('questions', {}).get(str(activity_id), [])
            questions_json = json.dumps(questions)
            total_points = sum(question.get('score', 0) for question in questions)
            show_exact_badge = activity.passing_score_type == "number"

            last_qt_id = request.session.get(f'last_quiz_type_{activity_id}')
            last_used_quiz_type = None
            if last_qt_id:
                try:
                    last_used_quiz_type = QuizType.objects.get(id=last_qt_id)
                except QuizType.DoesNotExist:
                    pass

            default_question_points = request.session.get(f'default_points_{activity_id}')

            rubrics = Rubrics.objects.filter(subject=activity.subject).values('id', 'rubric_name')
            rubrics_json = json.dumps(list(rubrics))

            # One-shot flag set by the bulk-import POST. When present, the
            # editor should render imported questions immediately without
            # showing the autosave "Restore" banner.
            skip_restore_banner = bool(
                request.session.pop(f'qc_skip_restore_{activity_id}', False)
            )
            if skip_restore_banner:
                request.session.modified = True

            return render(request, 'activity/question/create_quiz_type.html', {
                'activity': activity,
                'subject': activity.subject,
                'MEDIA_URL': settings.MEDIA_URL,
                'quiz_types': quiz_types,
                'questions': questions,
                'questions_json': questions_json,
                'rubrics_json': rubrics_json,
                'total_points': total_points,
                'is_participation': is_participation,
                'last_used_quiz_type': last_used_quiz_type,
                'default_question_points': default_question_points,
                'show_exact_badge': show_exact_badge,
                'expected_total': float(activity.passing_score) if show_exact_badge else None,
                'skip_restore_banner': skip_restore_banner,
            })
        except Exception:
            logger.exception("AddQuizTypeView.get failed for activity_id=%s", activity_id)
            messages.error(request, "An error occurred while loading the quiz types.")
            return redirect('error')

    def post(self, request, activity_id):
        try:
            # ===== SESSION VALIDATION =====
            # Check if there's a current activity in session (from create activity flow)
            session_activity_id = request.session.get('current_activity_id')
            if session_activity_id and session_activity_id != activity_id:
                # URL was manipulated - redirect to correct activity ID
                messages.warning(request, "Redirected to your current activity.")
                return redirect(reverse('add_quiz_type', kwargs={'activity_id': session_activity_id}))
            # ===== END SESSION VALIDATION =====
            
            activity = get_object_or_404(Activity, pk=activity_id)
            
            # ===== AUTHORIZATION CHECK =====
            has_access, redirect_response = check_activity_access(request, activity, require_teacher=True)
            if not has_access:
                return redirect_response
            # ===== END AUTHORIZATION CHECK =====
            
            quiz_type_id = request.POST.get('quiz_type')

            if not quiz_type_id or int(quiz_type_id) == 0:
                messages.error(request, "Quiz type not selected.")
                return self.get(request, activity_id)
            else:
                pass

            return redirect(reverse('add_question', kwargs={'activity_id': activity.id, 'quiz_type_id': quiz_type_id}))
        except Activity.DoesNotExist:
            messages.error(request, "The specified activity does not exist.")
            return redirect('error')
        except Exception:
            messages.error(request, "An error occurred while selecting the quiz type.")
            return redirect('error')


# Add quiz type (Classroom Mode)
@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('quiztype.add_quiztype', raise_exception=True), name='dispatch')
class AddQuizTypeViewCM(View):
    def get(self, request, activity_id):
        try:
            # ===== SESSION VALIDATION =====
            # Check if there's a current activity in session (from create activity flow)
            session_activity_id = request.session.get('current_activity_id')
            if session_activity_id and session_activity_id != activity_id:
                # URL was manipulated - redirect to correct activity ID
                messages.warning(request, "Redirected to your current activity.")
                return redirect(reverse('add_quiz_typeCM', kwargs={'activity_id': session_activity_id}))
            # ===== END SESSION VALIDATION =====
            
            activity = get_object_or_404(Activity, pk=activity_id)

            # ===== AUTHORIZATION CHECK =====
            has_access, redirect_response = check_activity_access(request, activity, require_teacher=True)
            if not has_access:
                return redirect_response
            # ===== END AUTHORIZATION CHECK =====

            quiz_types = QuizType.objects.all()
            subject = activity.subject
            subject_id = activity.subject.id
            subject = get_object_or_404(Subject, id=subject_id)

            is_participation = activity.activity_type.name == 'Participation'

            # Major Assessment is direct-scoring — go straight to the
            # student-score roster, even when reached outside the create flow.
            if is_participation:
                participation_qt = QuizType.objects.filter(name='Participation').first()
                if participation_qt:
                    return redirect(reverse('add_questionCM', kwargs={
                        'activity_id': activity.id,
                        'quiz_type_id': participation_qt.id,
                    }))

            questions = request.session.get('questions', {}).get(str(activity_id), [])
            total_points = sum(question.get('score', 0) for question in questions)

            skip_restore_banner = bool(
                request.session.pop(f'qc_skip_restore_{activity_id}', False)
            )
            if skip_restore_banner:
                request.session.modified = True

            return render(request, 'activity/question/create_quiz_type_CM.html', {
                'activity': activity,
                'MEDIA_URL': settings.MEDIA_URL,
                'quiz_types': quiz_types,
                'questions': questions,
                'total_points': total_points,
                'is_participation': is_participation,
                'subject': subject,
                'skip_restore_banner': skip_restore_banner,
            })
        except Exception:
            logger.exception("AddQuizTypeView.get failed for activity_id=%s", activity_id)
            messages.error(request, "An error occurred while loading the quiz types.")
            return redirect('error')

    def post(self, request, activity_id):
        try:
            # ===== SESSION VALIDATION =====
            # Check if there's a current activity in session (from create activity flow)
            session_activity_id = request.session.get('current_activity_id')
            if session_activity_id and session_activity_id != activity_id:
                # URL was manipulated - redirect to correct activity ID
                messages.warning(request, "Redirected to your current activity.")
                return redirect(reverse('add_quiz_typeCM', kwargs={'activity_id': session_activity_id}))
            # ===== END SESSION VALIDATION =====
            
            activity = get_object_or_404(Activity, pk=activity_id)
            
            # ===== AUTHORIZATION CHECK =====
            has_access, redirect_response = check_activity_access(request, activity, require_teacher=True)
            if not has_access:
                return redirect_response
            # ===== END AUTHORIZATION CHECK =====
            
            quiz_type_id = request.POST.get('quiz_type')

            if not quiz_type_id or int(quiz_type_id) == 0:
                messages.error(request, "Quiz type not selected.")
                return self.get(request, activity_id)
            else:
                pass

            return redirect(reverse('add_questionCM', kwargs={'activity_id': activity.id, 'quiz_type_id': quiz_type_id}))
        except Activity.DoesNotExist:
            messages.error(request, "The specified activity does not exist.")
            return redirect('error')
        except Exception:
            messages.error(request, "An error occurred while selecting the quiz type.")
            return redirect('error')
