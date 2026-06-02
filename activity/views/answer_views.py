from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from random import shuffle
from django.db.models import Max, Avg, Sum
import re
from activity.models import (Activity, ActivityQuestion, QuestionChoice, StudentQuestion, StudentActivity, RetakeRecord, RetakeRecordDetail, RubricsItem)
from subject.models import Subject
from module.models.student_progress import StudentProgress
from activity.utils.authorization import check_activity_access
from activity.services.auto_grader import grade_detail, recompute_retake_record_score, recompute_student_activity_total


def _normalize_text(text):
    return re.sub(r'\W+', '', text or '').lower()


def _effective_deadline(activity):
    """Return the latest moment a student is allowed to submit for this
    activity, factoring in any late-submission grace days configured by the
    teacher. Returns ``None`` when the activity has no end_time set.
    """
    if not getattr(activity, 'end_time', None):
        return None
    if not getattr(activity, 'allow_late_submission', False):
        return activity.end_time
    days = int(getattr(activity, 'late_submission_days', 0) or 0)
    if days <= 0:
        return activity.end_time
    return activity.end_time + timedelta(days=days)


def _grade_existing_attempt(student_activity):
    """Finalize an in-progress attempt using only the answers the student
    autosaved before the deadline. Used when the per-attempt timer ran out
    while the student was offline.
    """
    activity = student_activity.activity
    student = student_activity.student
    if (student_activity.retake_count or 0) == 0:
        student_activity.retake_count = 1
        student_activity.save(update_fields=['retake_count'])
    attempt_number = student_activity.retake_count
    retake_record, _ = RetakeRecord.objects.update_or_create(
        student_activity=student_activity,
        retake_number=attempt_number,
        defaults={
            'student': student,
            'activity': activity,
            'duration': activity.time_duration or 0,
            'started_at': student_activity.start_time,
            'will_end_at': student_activity.end_time,
            'status': 'submitted',
        },
    )
    questions = ActivityQuestion.objects.filter(activity=activity).select_related('quiz_type')
    now = timezone.now()
    for question in questions:
        detail, _ = RetakeRecordDetail.objects.update_or_create(
            retake_record=retake_record,
            student=student,
            activity_question=question,
            defaults={'submission_time': now},
        )
        ans = (detail.student_answer or '').strip()
        score = 0
        if ans and question.quiz_type:
            qt = question.quiz_type.name
            if qt == 'Multiple Choice':
                s_idx, c_idx = _resolve_mc_indices(question, ans)
                if s_idx is not None and c_idx is not None and s_idx == c_idx:
                    score = question.score or 0
            elif qt in ('True/False', 'Fill in the Blank', 'Calculated Numeric'):
                if _normalize_text(ans) == _normalize_text(question.correct_answer):
                    score = question.score or 0
        detail.score = score
        detail.submission_time = now
        detail.save(update_fields=['score', 'submission_time'])

    if (
        activity.allow_late_submission
        and activity.late_submission_penalty_percent
        and activity.end_time
        and timezone.now() > activity.end_time
    ):
        retake_record.late_penalty_percent = max(
            0, min(int(activity.late_submission_penalty_percent), 100)
        )
        retake_record.save(update_fields=['late_penalty_percent'])

    recompute_retake_record_score(retake_record)
    recompute_student_activity_total(student_activity)
    return retake_record.score or 0


def _resolve_mc_indices(question, answer):
    """Return (student_idx, correct_idx) as integers for a Multiple Choice
    question, resolving the inputs to the same shape so they can be compared.

    The student form submits either the choice text or, for image-only
    choices, the choice's display index. The DB stores ``correct_answer`` as
    the index. This helper normalises both sides to the index space.
    Returns ``(None, None)`` when the answer is missing.
    """
    if answer is None or str(answer).strip() == '':
        return None, None

    choices = list(question.choices.all().order_by('id'))
    if not choices:
        return None, None

    raw = str(answer).strip()
    student_idx = None

    # 1) submitted as "cid:<choice_id>" — the canonical form. Stable across
    # shuffled rendering and image-only choices, where text-match isn't
    # possible.
    if raw.lower().startswith('cid:'):
        try:
            cid = int(raw.split(':', 1)[1])
            for i, c in enumerate(choices):
                if c.id == cid:
                    student_idx = i
                    break
        except (TypeError, ValueError):
            pass

    # 2) legacy: submitted as numeric index into id-ordered choices
    if student_idx is None:
        try:
            idx = int(raw)
            if 0 <= idx < len(choices):
                student_idx = idx
        except (TypeError, ValueError):
            pass

    # 3) legacy: submitted as choice text — match against stored choice_text
    if student_idx is None:
        norm = _normalize_text(raw)
        for i, c in enumerate(choices):
            if c.choice_text and _normalize_text(c.choice_text) == norm:
                student_idx = i
                break

    # Resolve the correct index the same way (handles both index-stored and
    # legacy text-stored correct_answer values).
    correct_idx = None
    correct_raw = (question.correct_answer or '').strip()
    try:
        ci = int(correct_raw)
        if 0 <= ci < len(choices):
            correct_idx = ci
    except (TypeError, ValueError):
        pass
    if correct_idx is None and correct_raw:
        norm_c = _normalize_text(correct_raw)
        for i, c in enumerate(choices):
            if c.choice_text and _normalize_text(c.choice_text) == norm_c:
                correct_idx = i
                break

    return student_idx, correct_idx


@method_decorator(login_required, name='dispatch')
class DisplayQuestionsView(View):
    def get(self, request, activity_id):
        activity = get_object_or_404(Activity, pk=activity_id)
        user = request.user
        
        # ===== AUTHORIZATION CHECK =====
        has_access, redirect_response = check_activity_access(request, activity)
        if not has_access:
            return redirect_response
        # ===== END AUTHORIZATION CHECK =====

        is_teacher = user.is_authenticated and user.is_teacher
        is_student = user.is_authenticated and user.is_student
        is_time_keeper = user.is_authenticated and user.is_time_keeper

        now = timezone.now()
        deadline = _effective_deadline(activity)
        if deadline and deadline < now:
            if is_student:
                return redirect('my-assessment-score', activity_id=activity.id)
            else:
                return redirect('score-sheet', activity_id=activity.id)

        student_activity = None
        can_retake = False
        has_answered = False
        time_remaining = None

        if is_student:
            student_activity, created = StudentActivity.objects.get_or_create(student=user, activity=activity, defaults={'subject': activity.subject})

            can_retake = student_activity.retake_count < activity.max_retake

            if student_activity.retake_count >= activity.max_retake:
                return redirect('my-assessment-score', activity_id=activity.id)

            if student_activity.retake_count > activity.max_retake:
                return redirect('my-assessment-score', activity_id=activity.id)

            student_questions = StudentQuestion.objects.filter(student=user, activity_question__activity=activity)
            has_answered = student_questions.filter(status=True).exists()

            if not has_answered:
                if not student_activity.start_time:
                    student_activity.start_time = timezone.now()
                    student_activity.end_time = student_activity.start_time + timedelta(minutes=activity.time_duration)
                    student_activity.save()

            if not student_activity.start_time:
                return render(request, 'activity/question/display_question.html', {
                    'activity': activity,
                    'is_teacher': is_teacher,
                    'is_student': is_student,
                    'is_time_keeper': is_time_keeper,
                    'student_activity': student_activity,
                    'can_retake': True,
                    'has_answered': False,
                })

            time_remaining = None
            if student_activity.end_time:
                time_remaining = student_activity.end_time - timezone.now()
                if time_remaining.total_seconds() <= 0:
                    # Per-attempt timer expired while the student was away.
                    # If the activity still accepts late submissions and the
                    # grace window is open, extend the attempt so the student
                    # can keep working — Celery will finalize once the late
                    # window also closes.
                    eff_deadline = _effective_deadline(activity)
                    if eff_deadline and timezone.now() < eff_deadline:
                        student_activity.end_time = eff_deadline
                        student_activity.save(update_fields=['end_time'])
                        time_remaining = eff_deadline - timezone.now()
                        messages.info(
                            request,
                            "Your timer ran out, but late submissions are still being accepted "
                            "until {}.".format(eff_deadline.strftime('%b %d, %Y %I:%M %p')),
                        )
                    else:
                        if (student_activity.retake_count or 0) == 0:
                            try:
                                _grade_existing_attempt(student_activity)
                            except Exception:
                                pass
                        messages.info(request, "Your time ran out and your attempt was submitted automatically.")
                        return redirect('my-assessment-score', activity_id=activity.id)

            can_retake = student_activity.retake_count < activity.max_retake
        else:
            student_activity = None
            has_answered = False
            time_remaining = None
            can_retake = False

        questions = list(ActivityQuestion.objects.filter(activity=activity))

        for question in questions:
            rubric_items = RubricsItem.objects.filter(activity_question=question).select_related('rubric')
            question.rubric_items = rubric_items

        # ── Stable per-attempt order + per-MC choice order ──
        # On the first time a student opens this attempt we stamp the order
        # onto the open RetakeRecord. Subsequent renders (reload, browser
        # close+reopen) read that same stamp so the layout is identical.
        if is_student and student_activity:
            attempt_number = max(1, student_activity.retake_count or 1)
            retake_record, _ = RetakeRecord.objects.get_or_create(
                student_activity=student_activity,
                retake_number=attempt_number,
                defaults={
                    'student': user,
                    'activity': activity,
                    'duration': activity.time_duration or 0,
                    'started_at': student_activity.start_time or timezone.now(),
                    'will_end_at': student_activity.end_time,
                    'status': 'in_progress',
                },
            )
            qids = list(retake_record.question_order or [])
            if not qids:
                qid_pool = [q.id for q in questions]
                if activity.shuffle_questions:
                    shuffle(qid_pool)
                qids = qid_pool
                retake_record.question_order = qids
                retake_record.save(update_fields=['question_order'])
            qmap = {q.id: q for q in questions}
            questions = [qmap[i] for i in qids if i in qmap]

            # Per-MC-question choice order (stamped once).
            choice_order = dict(retake_record.choice_order or {})
            order_dirty = False
            for question in questions:
                if question.quiz_type and question.quiz_type.name == 'Multiple Choice':
                    key = str(question.id)
                    cids = choice_order.get(key)
                    if not cids:
                        cids = [c.id for c in question.choices.all()]
                        if activity.shuffle_questions:
                            shuffle(cids)
                        choice_order[key] = cids
                        order_dirty = True
                    cmap = {c.id: c for c in question.choices.all()}
                    question.ordered_choices = [cmap[i] for i in cids if i in cmap]
            if order_dirty:
                retake_record.choice_order = choice_order
                retake_record.save(update_fields=['choice_order'])

            # Hydrate prior answers so resumed attempts pre-fill inputs.
            prior = {
                sq.activity_question_id: sq
                for sq in StudentQuestion.objects.filter(student=user, activity=activity)
            }
            for question in questions:
                sq = prior.get(question.id)
                question.prior_answer = sq.student_answer if sq else ''
                question.prior_uploaded = bool(sq and sq.uploaded_file)

        for question in questions:
            # Convert index to actual choice text for Multiple Choice display
            if question.quiz_type.name == 'Multiple Choice' and is_teacher:
                try:
                    correct_index = int(question.correct_answer)
                    choices = list(question.choices.all())
                    if 0 <= correct_index < len(choices):
                        correct_choice = choices[correct_index]
                        question.correct_answer_display = correct_choice.choice_text or None
                        question.correct_answer_image = correct_choice.choice_image or None
                        question.correct_choice_index = correct_index
                    else:
                        question.correct_answer_display = question.correct_answer
                        question.correct_answer_image = None
                        question.correct_choice_index = -1
                except (ValueError, TypeError):
                    question.correct_answer_display = question.correct_answer
                    question.correct_answer_image = None
                    question.correct_choice_index = -1
            
            if question.quiz_type.name == 'Matching Type':
                pairs = question.correct_answer.split(", ")
                question.pairs = []
                right_terms = []
                for pair in pairs:
                    if '->' in pair:
                        left, right = pair.split(" -> ")
                        question.pairs.append({"left": left, "right": right})
                        right_terms.append(right)

                extra_right_terms = QuestionChoice.objects.filter(question=question, is_left_side=False).exclude(choice_text__in=right_terms)
                right_terms += [term.choice_text for term in extra_right_terms]

                shuffle(right_terms)
                question.shuffled_right_terms = right_terms

            if question.quiz_type.name == 'Document':
                if is_teacher:
                    question.document_link = question.correct_answer if question.correct_answer else None
                elif is_student:
                    question.allow_upload = True

        # Build attempt summary for the "already answered" UI.
        first_attempt = None
        latest_attempt = None
        attempt_count = 0
        if is_student and has_answered and student_activity:
            retakes = list(
                RetakeRecord.objects.filter(student_activity=student_activity)
                .order_by('retake_number')
            )
            attempt_count = len(retakes) or 1
            if retakes:
                first_attempt = {
                    'score': retakes[0].score,
                    'submitted_at': retakes[0].retake_time,
                    'number': retakes[0].retake_number,
                }
                latest_attempt = {
                    'score': retakes[-1].score,
                    'submitted_at': retakes[-1].retake_time,
                    'number': retakes[-1].retake_number,
                }
            else:
                # Fallback when retake records were never written: derive from StudentActivity.
                first_attempt = {
                    'score': student_activity.total_score,
                    'submitted_at': student_activity.end_time,
                    'number': 1,
                }
                latest_attempt = first_attempt

        context = {
            'activity': activity,
            'questions': questions,
            'is_teacher': is_teacher,
            'is_student': is_student,
            'is_time_keeper': is_time_keeper,
            'can_retake': can_retake,
            'has_answered': has_answered,
            'time_remaining': time_remaining.total_seconds() if time_remaining else None,
            'student_activity': student_activity,
            'first_attempt': first_attempt,
            'latest_attempt': latest_attempt,
            'attempt_count': attempt_count,
        }

        return render(request, 'activity/question/display_question.html', context)


@method_decorator(login_required, name='dispatch')
class DisplayQuestionsViewCM(View):
    def get(self, request, activity_id):
        activity = get_object_or_404(Activity, pk=activity_id)
        user = request.user
        
        # ===== AUTHORIZATION CHECK =====
        has_access, redirect_response = check_activity_access(request, activity)
        if not has_access:
            return redirect_response
        # ===== END AUTHORIZATION CHECK =====
        
        subject = activity.subject
        subject_id = activity.subject.id
        subject = get_object_or_404(Subject, id=subject_id)

        is_teacher = user.is_authenticated and user.is_teacher
        is_student = user.is_authenticated and user.is_student

        now = timezone.now()
        deadline = _effective_deadline(activity)
        if deadline and deadline < now:
            if is_student:
                return redirect('my-assessment-score', activity_id=activity.id)
            else:
                return redirect('teacherActivityViewCM', activity_id=activity.id)

        student_activity = None
        can_retake = False
        has_answered = False
        time_remaining = None

        if is_student:
            student_activity, created = StudentActivity.objects.get_or_create(student=user, activity=activity, defaults={'subject': activity.subject})

            if activity.classroom_mode and student_activity.attendance_mode == 'Absent':
                messages.warning(request, "You were marked as absent for this assessment and cannot participate.")
                return redirect('my-assessment-score', activity_id=activity.id)

            if student_activity.retake_count > activity.max_retake:
                return redirect('my-assessment-score', activity_id=activity.id)

            student_questions = StudentQuestion.objects.filter(student=user, activity_question__activity=activity)
            has_answered = student_questions.filter(status=True).exists()

            if not has_answered:
                if not student_activity.start_time:
                    student_activity.start_time = timezone.now()
                    student_activity.end_time = student_activity.start_time + timedelta(minutes=activity.time_duration)
                    student_activity.save()

            if not student_activity.start_time:
                return render(request, 'activity/question/display_question_CM.html', {
                    'activity': activity,
                    'subject': subject,
                    'is_teacher': is_teacher,
                    'is_student': is_student,
                    'student_activity': student_activity,
                    'can_retake': True,
                    'has_answered': False,
                })

            time_remaining = None
            if student_activity.end_time:
                time_remaining = student_activity.end_time - timezone.now()
                if time_remaining.total_seconds() <= 0:
                    eff_deadline = _effective_deadline(activity)
                    if eff_deadline and timezone.now() < eff_deadline:
                        student_activity.end_time = eff_deadline
                        student_activity.save(update_fields=['end_time'])
                        time_remaining = eff_deadline - timezone.now()
                        messages.info(
                            request,
                            "Your timer ran out, but late submissions are still being accepted "
                            "until {}.".format(eff_deadline.strftime('%b %d, %Y %I:%M %p')),
                        )
                    else:
                        return self.auto_submit_answers(student_activity)

            can_retake = student_activity.retake_count < activity.max_retake
        else:
            student_activity = None
            has_answered = False
            time_remaining = None
            can_retake = False

        questions = ActivityQuestion.objects.filter(activity=activity)

        if activity.shuffle_questions and is_student:
            questions = list(questions)
            shuffle(questions)

        for question in questions:
            # Convert index to actual choice text for Multiple Choice display
            if question.quiz_type.name == 'Multiple Choice' and is_teacher:
                try:
                    correct_index = int(question.correct_answer)
                    choices = list(question.choices.all())
                    if 0 <= correct_index < len(choices):
                        correct_choice = choices[correct_index]
                        question.correct_answer_display = correct_choice.choice_text or None
                        question.correct_answer_image = correct_choice.choice_image or None
                        question.correct_choice_index = correct_index
                    else:
                        question.correct_answer_display = question.correct_answer
                        question.correct_answer_image = None
                        question.correct_choice_index = -1
                except (ValueError, TypeError):
                    question.correct_answer_display = question.correct_answer
                    question.correct_answer_image = None
                    question.correct_choice_index = -1
            
            if question.quiz_type.name == 'Matching Type':
                pairs = question.correct_answer.split(", ")
                question.pairs = []
                right_terms = []
                for pair in pairs:
                    if '->' in pair:
                        left, right = pair.split(" -> ")
                        question.pairs.append({"left": left, "right": right})
                        right_terms.append(right)

                extra_right_terms = QuestionChoice.objects.filter(question=question, is_left_side=False).exclude(choice_text__in=right_terms)
                right_terms += [term.choice_text for term in extra_right_terms]

                shuffle(right_terms)
                question.shuffled_right_terms = right_terms

            if question.quiz_type.name == 'Document':
                if is_teacher:
                    question.document_link = question.correct_answer if question.correct_answer else None
                elif is_student:
                    question.allow_upload = True

        context = {
            'activity': activity,
            'subject': subject,
            'questions': questions,
            'is_teacher': is_teacher,
            'is_student': is_student,
            'can_retake': can_retake,
            'has_answered': has_answered,
            'time_remaining': time_remaining.total_seconds() if time_remaining else None,
        }

        return render(request, 'activity/question/display_question_CM.html', context)

    def auto_submit_answers(self, student_activity):
        """
        Automatically submits answers if time expires.
        """
        student = student_activity.student
        activity = student_activity.activity

        questions = ActivityQuestion.objects.filter(activity=activity)

        attempt_number = max(1, student_activity.retake_count or 1)
        retake_record, _ = RetakeRecord.objects.update_or_create(
            student_activity=student_activity,
            retake_number=attempt_number,
            defaults={
                'student': student,
                'activity': activity,
                'duration': activity.time_duration or 0,
                'started_at': student_activity.start_time,
                'will_end_at': student_activity.end_time,
                'status': 'submitted',
            },
        )
        now = timezone.now()
        for question in questions:
            detail, _ = RetakeRecordDetail.objects.update_or_create(
                retake_record=retake_record,
                student=student,
                activity_question=question,
                defaults={'submission_time': now},
            )
            if not detail.student_answer:
                detail.score = 0
            detail.submission_time = now
            detail.save(update_fields=['score', 'submission_time'])

        if (
            activity.allow_late_submission
            and activity.late_submission_penalty_percent
            and activity.end_time
            and timezone.now() > activity.end_time
        ):
            retake_record.late_penalty_percent = max(
                0, min(int(activity.late_submission_penalty_percent), 100)
            )
            retake_record.save(update_fields=['late_penalty_percent'])

        recompute_retake_record_score(retake_record)
        recompute_student_activity_total(student_activity)

        # Show score only if there are non-essay and non-document questions
        has_non_essay_questions = questions.exclude(quiz_type__name__in=['Essay', 'Document']).exists()

        retake_record.refresh_from_db(fields=['score'])
        return redirect('assessment-completed', score=int(retake_record.score or 0), activity_id=activity.id, show_score=has_non_essay_questions)


@method_decorator([login_required], name='dispatch')
class AutoSubmitAnswersView(View):
    def post(self, request, activity_id):
        activity = get_object_or_404(Activity, pk=activity_id)
        
        # ===== AUTHORIZATION CHECK =====
        has_access, redirect_response = check_activity_access(request, activity, require_student=True)
        if not has_access:
            return redirect_response
        # ===== END AUTHORIZATION CHECK =====
        
        student = request.user
        student_activity, created = StudentActivity.objects.get_or_create(student=student, activity=activity, defaults={'subject': activity.subject})

        total_score = 0
        questions = ActivityQuestion.objects.filter(activity=activity)

        session_key = f'auto_submit_{activity_id}_{student.id}'
        if request.session.get(session_key, False):
            pass
        else:
            student_activity.retake_count += 1
            student_activity.save()
            request.session[session_key] = True

        data = request.POST

        retake_record, _ = RetakeRecord.objects.update_or_create(
            student_activity=student_activity,
            retake_number=student_activity.retake_count,
            defaults={
                'student': student,
                'activity': activity,
                'duration': activity.time_duration if activity.time_duration else 0,
                'status': 'submitted',
            },
        )

        now = timezone.now()
        for question in questions:
            answer = data.get(f'question_{question.id}', '').strip()
            current_score = 0
            student_answer = ''

            if question.quiz_type.name == 'Essay':
                student_answer = answer
            else:
                if answer:
                    student_answer = answer
                    if question.quiz_type.name == 'Multiple Choice':
                        student_idx, correct_idx = _resolve_mc_indices(question, answer)
                        is_correct = (
                            student_idx is not None
                            and correct_idx is not None
                            and student_idx == correct_idx
                        )
                    else:
                        is_correct = (
                            _normalize_text(answer) ==
                            _normalize_text(question.correct_answer)
                        )
                    current_score = question.score if is_correct else 0

            RetakeRecordDetail.objects.update_or_create(
                retake_record=retake_record,
                student=student,
                activity_question=question,
                defaults={
                    'student_answer': student_answer,
                    'score': current_score,
                    'submission_time': now,
                },
            )

            total_score += current_score

        recompute_retake_record_score(retake_record)
        recompute_student_activity_total(student_activity)

        return JsonResponse({'status': 'success', 'message': 'Answers saved & submitted!'}, status=200)



# Submit answers
@method_decorator(login_required, name='dispatch')
class SubmitAnswersView(View):
    def post(self, request, activity_id, auto_submit=False):
        activity = get_object_or_404(Activity, pk=activity_id)
        
        # ===== AUTHORIZATION CHECK =====
        has_access, redirect_response = check_activity_access(request, activity, require_student=True)
        if not has_access:
            return redirect_response
        # ===== END AUTHORIZATION CHECK =====
        
        student = request.user
        total_score_current_attempt = 0
        has_non_essay_questions = False
        progress, created = StudentProgress.objects.get_or_create(student=student, activity=activity)
        progress.progress = 100
        progress.completed = True
        progress.save()

        student_activity, created = StudentActivity.objects.get_or_create(student=student, activity=activity, defaults={'subject': activity.subject})
        total_score = 0

        if created:
            student_activity.retake_count = 1
        else:
            student_activity.retake_count += 1

        student_activity.save()

        current_time = timezone.now()
        deadline = _effective_deadline(activity)
        if deadline and current_time > deadline:
            messages.error(request, 'The submission window for this assessment has closed.')
            return self.auto_submit_answers(student_activity)
        if student_activity.end_time and current_time > student_activity.end_time:
            # Per-attempt timer expired (open + time_duration). Auto-submit what
            # the student has — this is independent of the activity's late window.
            messages.error(request, 'Your time has expired. Your answers have been submitted automatically.')
            return self.auto_submit_answers(student_activity)

        def normalize_text(text):
            return re.sub(r'\W+', '', text).lower()

        if student_activity.retake_count > activity.max_retake:
            messages.error(request, 'You have reached the maximum number of attempts for this assessment.')
            return self.auto_submit_answers(student_activity)

        all_questions_answered = True

        retake_record, _ = RetakeRecord.objects.update_or_create(
            student_activity=student_activity,
            retake_number=student_activity.retake_count,
            defaults={
                'student': student,
                'activity': activity,
                'duration': activity.time_duration if activity.time_duration else 0,
                'status': 'submitted',
            },
        )

        prior_details = {
            d.activity_question_id: d
            for d in RetakeRecordDetail.objects.filter(retake_record=retake_record)
        }
        RetakeRecordDetail.objects.filter(retake_record=retake_record).delete()

        now = timezone.now()
        for question in ActivityQuestion.objects.filter(activity=activity):
            answer = request.POST.get(f'question_{question.id}')
            current_score = 0
            student_answer = ''
            uploaded_file = None

            if question.quiz_type.name == 'Document':
                uploaded_file = request.FILES.get(f'question_{question.id}')
                if uploaded_file:
                    student_answer = uploaded_file.name
                else:
                    all_questions_answered = not auto_submit
                current_score = 0

            elif question.quiz_type.name == 'Matching Type':
                matching_left = []
                matching_right = []

                correct_answer_pairs = []
                correct_answer = question.correct_answer.split(", ")

                for pair in correct_answer:
                    if '->' in pair:
                        left, right = pair.split(" -> ")
                        correct_answer_pairs.append((normalize_text(left), normalize_text(right)))

                for idx in range(len(correct_answer_pairs)):
                    left = request.POST.get(f'matching_left_{question.id}_{idx}')
                    right = request.POST.get(f'matching_right_{question.id}_{idx}')

                    if left and right:
                        matching_left.append(left)
                        matching_right.append(right)

                if matching_left and matching_right and len(matching_left) == len(matching_right):
                    pairs_answer = list(zip(matching_left, matching_right))
                    student_answer = str(pairs_answer)

                    normalized_student_answer = [(normalize_text(left), normalize_text(right)) for left, right in pairs_answer]

                    if normalized_student_answer == correct_answer_pairs:
                        current_score = question.score
                    else:
                        current_score = 0
                else:
                    all_questions_answered = not auto_submit
                    current_score = 0

            elif question.quiz_type.name == 'Essay':
                student_answer = answer or ''
                current_score = 0

            else:
                existing_detail = prior_details.get(question.id)
                existing_answer = existing_detail.student_answer if existing_detail else ''
                if not answer and not existing_answer:
                    all_questions_answered = not auto_submit
                    current_score = 0
                else:
                    student_answer = answer or existing_answer
                    if question.quiz_type.name == 'Multiple Choice':
                        student_idx, correct_idx = _resolve_mc_indices(question, student_answer)
                        is_correct = (
                            student_idx is not None
                            and correct_idx is not None
                            and student_idx == correct_idx
                        )
                    else:
                        normalized_answer = normalize_text(student_answer)
                        normalized_correct = normalize_text(question.correct_answer)
                        is_correct = (normalized_answer == normalized_correct)
                    current_score = question.score if is_correct else 0
                    has_non_essay_questions = True

            detail_defaults = {
                'student_answer': student_answer,
                'score': current_score,
                'submission_time': now,
            }
            if uploaded_file is not None:
                detail_defaults['uploaded_file'] = uploaded_file
            RetakeRecordDetail.objects.update_or_create(
                retake_record=retake_record,
                student=student,
                activity_question=question,
                defaults=detail_defaults,
            )

            total_score += current_score
            total_score_current_attempt += current_score

        if (
            activity.allow_late_submission
            and activity.late_submission_penalty_percent
            and activity.end_time
            and timezone.now() > activity.end_time
        ):
            retake_record.late_penalty_percent = max(
                0, min(int(activity.late_submission_penalty_percent), 100)
            )
            retake_record.save(update_fields=['late_penalty_percent'])

        recompute_retake_record_score(retake_record)
        recompute_student_activity_total(student_activity)

        if auto_submit or all_questions_answered:
            messages.success(request, 'Answers submitted successfully!')
            retake_record.refresh_from_db(fields=['score', 'late_penalty_percent'])
            return redirect('assessment-completed', score=int(retake_record.score or 0), activity_id=activity_id, show_score=has_non_essay_questions)
        else:
            messages.error(request, 'You did not answer all questions. Please complete the assessment.')
            return redirect('display_question', activity_id=activity_id)

    def auto_submit_answers(self, student_activity):
        student = student_activity.student
        activity = student_activity.activity

        questions = ActivityQuestion.objects.filter(activity=activity)

        attempt_number = max(1, student_activity.retake_count or 1)
        retake_record, _ = RetakeRecord.objects.update_or_create(
            student_activity=student_activity,
            retake_number=attempt_number,
            defaults={
                'student': student,
                'activity': activity,
                'duration': activity.time_duration or 0,
                'started_at': student_activity.start_time,
                'will_end_at': student_activity.end_time,
                'status': 'submitted',
            },
        )

        now = timezone.now()
        for question in questions:
            detail, _ = RetakeRecordDetail.objects.update_or_create(
                retake_record=retake_record,
                student=student,
                activity_question=question,
                defaults={'submission_time': now},
            )
            if not detail.student_answer:
                detail.score = 0
            detail.submission_time = now
            detail.save(update_fields=['score', 'submission_time'])

        if (
            activity.allow_late_submission
            and activity.late_submission_penalty_percent
            and activity.end_time
            and timezone.now() > activity.end_time
        ):
            retake_record.late_penalty_percent = max(
                0, min(int(activity.late_submission_penalty_percent), 100)
            )
            retake_record.save(update_fields=['late_penalty_percent'])

        recompute_retake_record_score(retake_record)
        recompute_student_activity_total(student_activity)

        # Show score only if there are non-essay and non-document questions
        has_non_essay_questions = questions.exclude(quiz_type__name__in=['Essay', 'Document']).exists()

        retake_record.refresh_from_db(fields=['score'])
        return redirect('assessment-completed', score=int(retake_record.score or 0), activity_id=activity.id, show_score=has_non_essay_questions)


@method_decorator(login_required, name='dispatch')
class RetakeAssessmentView(View):
    def post(self, request, activity_id):
        activity = get_object_or_404(Activity, pk=activity_id)
        
        # ===== AUTHORIZATION CHECK =====
        has_access, redirect_response = check_activity_access(request, activity, require_student=True)
        if not has_access:
            return redirect_response
        # ===== END AUTHORIZATION CHECK =====
        
        student = request.user

        student_activity = StudentActivity.objects.get(student=student, activity=activity)

        if student_activity.retake_count > activity.max_retake:
            messages.error(request, 'You have reached the maximum number of retakes for this assessment.')
            return redirect('assessment-details', activity_id=activity_id)
        else:
            StudentQuestion.objects.filter(student=student, activity_question__activity=activity).update(
                student_answer='',
                status=False,
                uploaded_file=None,
                score=0,
                submission_time=None
            )

            student_activity.start_time = timezone.now()
            student_activity.end_time = student_activity.start_time + timedelta(minutes=activity.time_duration)
            student_activity.save()

            return redirect('display_question', activity_id=activity_id)


@login_required
def assessment_completed_view(request, score, activity_id, show_score):
    activity = get_object_or_404(Activity, pk=activity_id)
    
    # ===== AUTHORIZATION CHECK =====
    has_access, redirect_response = check_activity_access(request, activity)
    if not has_access:
        return redirect_response
    # ===== END AUTHORIZATION CHECK =====

    questions_qs = ActivityQuestion.objects.filter(activity=activity)
    max_score = questions_qs.aggregate(total_score=Sum('score'))['total_score'] or 0
    subject_id = activity.subject.id

    contains_document = questions_qs.filter(quiz_type__name='Document').exists()

    show_score_flag = (show_score == 'True')
    if contains_document:
        show_score_flag = False

    latest_retake = (
        RetakeRecord.objects
        .filter(student_activity__student=request.user, activity=activity)
        .order_by('-retake_time')
        .first()
    )
    late_penalty_percent = int(getattr(latest_retake, 'late_penalty_percent', 0) or 0) if latest_retake else 0
    raw_score = None
    if late_penalty_percent and latest_retake:
        raw_total = (
            latest_retake.retake_record_details.aggregate(v=Sum('score'))['v'] or 0
        )
        raw_score = int(round(raw_total))

    return render(request, 'activity/assessments/assessment-completed.html', {
        'score': score,
        'max_score': max_score,
        'show_score': show_score_flag,
        'subject_id': subject_id,
        'late_penalty_percent': late_penalty_percent,
        'raw_score': raw_score,
    })


# ──────────────────────────────────────────────────────────────────────
# Partial answer save (used by the student question form to autosave
# answers as the student moves between questions / types). Server-side
# StudentQuestion is the source of truth on resume.
# ──────────────────────────────────────────────────────────────────────
@method_decorator(login_required, name='dispatch')
class SavePartialAnswerView(View):
    def post(self, request, activity_id):
        import json as _json
        activity = get_object_or_404(Activity, pk=activity_id)
        try:
            payload = _json.loads(request.body or '{}')
        except (ValueError, TypeError):
            return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

        student = request.user
        sa = StudentActivity.objects.filter(student=student, activity=activity).first()
        if not sa:
            return JsonResponse({'ok': False, 'error': 'No attempt in progress'}, status=403)

        # Block saves past the effective deadline.
        deadline = _effective_deadline(activity)
        now = timezone.now()
        if deadline and now > deadline:
            return JsonResponse({'ok': False, 'error': 'Submission window closed'}, status=400)
        if sa.end_time and now > sa.end_time:
            return JsonResponse({'ok': False, 'error': 'Time expired'}, status=400)

        answers = payload.get('answers') or []
        if not isinstance(answers, list):
            return JsonResponse({'ok': False, 'error': 'Bad payload'}, status=400)

        attempt_number = max(1, sa.retake_count or 1)
        retake_record, _ = RetakeRecord.objects.get_or_create(
            student_activity=sa,
            retake_number=attempt_number,
            defaults={
                'student': student,
                'activity': activity,
                'duration': activity.time_duration or 0,
                'started_at': sa.start_time or now,
                'will_end_at': sa.end_time,
                'status': 'in_progress',
            },
        )

        saved = 0
        touched_qids = []
        for entry in answers:
            try:
                qid = int(entry.get('question_id'))
            except (TypeError, ValueError):
                continue
            question = ActivityQuestion.objects.filter(id=qid, activity=activity).select_related('quiz_type').first()
            if not question:
                continue
            answer_text = entry.get('answer', '')
            if answer_text is None:
                answer_text = ''
            answer_text = str(answer_text)[:10000]

            detail, _ = RetakeRecordDetail.objects.update_or_create(
                retake_record=retake_record,
                student=student,
                activity_question=question,
                defaults={'submission_time': now},
            )
            detail.student_answer = answer_text
            detail.submission_time = now

            qt = question.quiz_type.name if question.quiz_type else ''
            stripped = answer_text.strip()
            if not stripped:
                detail.score = 0
            elif qt == 'Multiple Choice':
                s_idx, c_idx = _resolve_mc_indices(question, stripped)
                detail.score = (question.score or 0) if (
                    s_idx is not None and c_idx is not None and s_idx == c_idx
                ) else 0
            elif qt in ('True/False', 'Fill in the Blank', 'Calculated Numeric'):
                detail.score = (question.score or 0) if (
                    _normalize_text(stripped) == _normalize_text(question.correct_answer)
                ) else 0
            else:
                detail.score = detail.score or 0
            detail.save(update_fields=['student_answer', 'submission_time', 'score'])
            saved += 1
            touched_qids.append(qid)

        if saved and (sa.retake_count or 0) == 0:
            running_total = (
                RetakeRecordDetail.objects
                .filter(retake_record=retake_record)
                .aggregate(t=Sum('score'))
            ).get('t') or 0
            sa.total_score = running_total
            sa.save(update_fields=['total_score'])

        return JsonResponse({'ok': True, 'saved': saved})
