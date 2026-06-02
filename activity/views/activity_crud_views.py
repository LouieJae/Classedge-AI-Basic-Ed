from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
from django.db import transaction
from accounts.models import CustomUser
from subject.models import Subject
from course.models import Term, Semester, Attendance
from module.models import Module
from activity.models import Activity, ActivityType, StudentActivity, ActivityQuestion, StudentQuestion, QuizType
from activity.forms import ActivityForm
from django.utils.timezone import is_aware, make_aware
import os
from activity.utils.authorization import check_subject_access, activity_has_submissions

def parse_datetime(value):
    dt = timezone.datetime.strptime(value, "%Y-%m-%dT%H:%M")
    return dt if is_aware(dt) else make_aware(dt)


def _apply_schedule_only_update(request, activity, redirect_name):
    """Persist only the date/time fields on an activity that already has
    submissions, so a teacher can extend the deadline for students who
    missed it without disturbing scoring rules.

    Returns a redirect HttpResponse: error redirect if validation fails,
    success redirect to the subject's material list (assessments tab) if saved.
    """
    start_time_raw = request.POST.get('start_time')
    end_time_raw = request.POST.get('end_time')
    if start_time_raw and end_time_raw and end_time_raw <= start_time_raw:
        messages.error(request, 'End time must be later than the start time.')
        return redirect(redirect_name, activity_id=activity.id)
    try:
        if start_time_raw:
            activity.start_time = parse_datetime(start_time_raw)
        if end_time_raw:
            activity.end_time = parse_datetime(end_time_raw)
    except ValueError:
        messages.error(request, 'Invalid date/time format.')
        return redirect(redirect_name, activity_id=activity.id)
    activity.allow_late_submission = request.POST.get('allow_late_submission') == 'on'
    try:
        activity.late_submission_days = int(request.POST.get('late_submission_days') or 0)
        activity.late_submission_penalty_percent = int(request.POST.get('late_submission_penalty_percent') or 0)
    except (TypeError, ValueError):
        messages.error(request, 'Late submission values must be whole numbers.')
        return redirect(redirect_name, activity_id=activity.id)
    activity.save(update_fields=[
        'start_time', 'end_time',
        'allow_late_submission', 'late_submission_days', 'late_submission_penalty_percent',
    ])
    messages.success(request, 'Schedule updated. Other settings remain locked because students have already submitted.')
    return redirect(f"{reverse('material-list', args=[activity.subject_id])}?view=assessments")


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('activity.add_activity', raise_exception=True), name='dispatch')
class AddAssessmentViewCM(View):
    def get(self, request, subject_id):
        subject = get_object_or_404(Subject, id=subject_id)

        has_access, redirect_response = check_subject_access(request, subject, require_teacher=True)
        if not has_access:
            return redirect_response    

        now = timezone.localtime(timezone.now())
        current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()
        current_term = Term.objects.filter(semester=current_semester, start_date__lte=now, end_date__gte=now).first()
        terms = Term.objects.filter(semester=current_semester)
    
        students = CustomUser.objects.filter(subjectenrollment__subject=subject, subjectenrollment__semester=current_semester, subjectenrollment__status='enrolled', profile__role__name__iexact='Student').distinct()
        modules = Module.objects.filter(subject=subject, term__semester=current_semester, start_date__isnull=False, end_date__isnull=False) 

        activity_type_id = request.GET.get('activity_type_id', None)
        if activity_type_id:
            activity_type = get_object_or_404(ActivityType, id=activity_type_id)
            is_participation = activity_type.name.lower() == 'participation'
        else:
            activity_type = None
            is_participation = False

        return render(request, 'activity/assessments/create-assessment-cm.html', {
            'subject': subject,
            'activity_types': ActivityType.objects.all(),
            'terms': terms,
            'students': students,
            'modules': modules,
            'current_term': current_term,
            'retake_methods': Activity.RETAKE_METHOD_CHOICES,
            'selected_activity_type': activity_type,
            'is_participation': is_participation
        })

    def post(self, request, subject_id):
        subject = get_object_or_404(Subject, id=subject_id)

        has_access, redirect_response = check_subject_access(request, subject, require_teacher=True)
        if not has_access:
            return redirect_response    

        activity_name = request.POST.get('activity_name')
        activity_type_id = request.GET.get('activity_type_id') or request.POST.get('activity_type_id')
        term_id = request.POST.get('term')
        additional_modules_ids = request.POST.getlist('additional_modules', [])
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        time_duration = request.POST.get('time_duration', 0) 
        passing_score = float(request.POST.get('passing_score', 0))
        passing_score_type = request.POST.get('passing_score_type')
        activity_instruction = request.POST.get('activity_instruction', '').strip()
        activity_file_instruction = request.FILES.get('activity_file_instruction')
        is_graded = request.POST.get('is_graded') == 'on'

        if activity_file_instruction:
            ext = os.path.splitext(activity_file_instruction.name)[1].lower()
            allowed = ['.pdf', '.jpg', '.jpeg', '.png']
            if ext not in allowed:
                messages.error(request, "Only PDF and image files are allowed.")
                return self.get(request, subject_id)
            if activity_file_instruction.size > 10 * 1024 * 1024:
                messages.error(request, "File must be less than 10MB.")
                return self.get(request, subject_id)

        if passing_score_type == 'percentage':
            if passing_score > 100:
                messages.error(request, 'Passing score cannot be more than 100 for percentage type.')
                return self.get(request, subject_id)
            passing_score = (passing_score / 100) * 100

        elif passing_score_type == 'number':
            passing_score = passing_score

        try:
            max_retake = int(request.POST.get('max_retake', 2))
            if max_retake < 1:
                max_retake = 1
            elif max_retake > 50:
                max_retake = 50
        except ValueError:
            max_retake = 2

        retake_method = request.POST.get('retake_method', 'highest')
        remedial = request.POST.get('remedial') == 'on'
        shuffle_questions = request.POST.get('shuffle_questions') == 'on'
        remedial_students_ids = request.POST.getlist('remedial_students', None)

        allow_late_submission = request.POST.get('allow_late_submission') == 'on'
        try:
            late_submission_days = max(0, int(request.POST.get('late_submission_days', 0) or 0))
        except (TypeError, ValueError):
            late_submission_days = 0
        try:
            late_submission_penalty_percent = max(0, min(100, int(request.POST.get('late_submission_penalty_percent', 0) or 0)))
        except (TypeError, ValueError):
            late_submission_penalty_percent = 0

        activity_type = get_object_or_404(ActivityType, id=activity_type_id)
        term = get_object_or_404(Term, id=term_id)

        # Major Assessment is direct-scoring, so it doesn't need a lesson
        # attached. Other activity types still require at least one lesson.
        if activity_type.name.lower() != 'participation' and not additional_modules_ids:
            messages.error(request, 'At least one materials must be selected.')
            return self.get(request, subject_id)

        start_time = parse_datetime(start_time)
        end_time = parse_datetime(end_time)

        if start_time >= end_time:
            messages.error(request, 'End time must be after start time.')
            return self.get(request, subject_id)

        activity = Activity.objects.create(
            activity_name=activity_name,
            activity_type=activity_type,
            subject=subject,
            term=term,
            start_time=start_time,
            end_time=end_time,
            max_retake=max_retake,
            time_duration=time_duration,
            retake_method=retake_method,
            remedial=remedial,
            shuffle_questions=shuffle_questions,
            is_graded=is_graded,
            passing_score=passing_score,
            passing_score_type=passing_score_type,
            activity_file_instruction=activity_file_instruction,
            activity_instruction=activity_instruction,
            allow_late_submission=allow_late_submission,
            late_submission_days=late_submission_days,
            late_submission_penalty_percent=late_submission_penalty_percent,
            classroom_mode=True
        )
        
        additional_modules = Module.objects.filter(id__in=additional_modules_ids)
        activity.additional_modules.set(additional_modules)

        messages.success(request, "Assessment created successfully.")

        if remedial and remedial_students_ids:
            remedial_students = CustomUser.objects.filter(id__in=remedial_students_ids,subjectenrollment__subject=subject,subjectenrollment__semester=term.semester,subjectenrollment__status='enrolled')
            activity.remedial_students.set(remedial_students)
            for student in remedial_students:
                StudentActivity.objects.get_or_create(student=student, activity=activity, term=term, subject=subject)
        else:
            students = CustomUser.objects.filter(
                subjectenrollment__subject=subject,
                subjectenrollment__semester=term.semester,
                subjectenrollment__status='enrolled',
                profile__role__name__iexact='Student'
            ).distinct()
            for student in students:
                StudentActivity.objects.get_or_create(student=student, activity=activity, term=term, subject=subject) 

        if activity.classroom_mode:
            attendance_records = Attendance.objects.filter(
                subject=subject,
                date=timezone.now().date()
            )

            for student in students:
                attendance_mode = 'Absent'
                attendance = attendance_records.filter(student=student).first()

                if attendance and attendance.status:
                    attendance_status = attendance.status.status

                    attendance_choices = {choice[0].lower(): choice[0] for choice in StudentActivity._meta.get_field('attendance_mode').choices}
                    if attendance_status.lower() in attendance_choices:
                        attendance_mode = attendance_choices[attendance_status.lower()]

                student_activity, created = StudentActivity.objects.update_or_create(
                    student=student,
                    activity=activity,
                    term=term,
                    defaults={
                        'attendance_mode': attendance_mode,
                        'subject': subject
                    }
                )

        # Store the created activity ID in session to prevent URL manipulation
        request.session['current_activity_id'] = activity.id
        request.session['current_activity_subject_id'] = subject.id

        # Major Assessment is direct-scoring — skip the quiz-type picker
        # and go straight to the student-score roster in CM mode too.
        if activity_type.name.lower() == 'participation':
            participation_qt = QuizType.objects.filter(name='Participation').first()
            if participation_qt:
                return redirect(reverse('add_questionCM', kwargs={
                    'activity_id': activity.id,
                    'quiz_type_id': participation_qt.id,
                }))

        messages.success(request, "You will now be redirected to configure quiz types.")
        return redirect(reverse('add_quiz_typeCM', kwargs={'activity_id': activity.id}))


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('activity.add_activity', raise_exception=True), name='dispatch')
class AddAssessmentView(View):
    def get(self, request, subject_id):
        subject = get_object_or_404(Subject, id=subject_id)

        has_access, redirect_response = check_subject_access(request, subject, require_teacher=True)
        if not has_access:
            return redirect_response

        now = timezone.localtime(timezone.now())
        current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()
        current_term = Term.objects.filter(semester=current_semester, start_date__lte=now, end_date__gte=now).first()
        terms = Term.objects.filter(semester=current_semester)
        
        students = CustomUser.objects.filter(subjectenrollment__subject=subject, subjectenrollment__semester=current_semester, subjectenrollment__status='enrolled', profile__role__name__iexact='Student').distinct()
        modules = Module.objects.filter(subject=subject, term__semester=current_semester, start_date__isnull=False, end_date__isnull=False) 

        activity_type_id = request.GET.get('activity_type_id', None)
        if activity_type_id:
            activity_type = get_object_or_404(ActivityType, id=activity_type_id)
            is_participation = activity_type.name.lower() == 'participation'
        else:
            activity_type = None
            is_participation = False

        return render(request, 'activity/assessments/create-assessment.html', {
            'subject': subject,
            'activity_types': ActivityType.objects.all(),
            'terms': terms,
            'students': students,
            'modules': modules,
            'current_term': current_term,
            'retake_methods': Activity.RETAKE_METHOD_CHOICES,
            'selected_activity_type': activity_type,
            'is_participation': is_participation
        })

    def post(self, request, subject_id):
        subject = get_object_or_404(Subject, id=subject_id)

        has_access, redirect_response = check_subject_access(request, subject, require_teacher=True)
        if not has_access:
            return redirect_response

        if 'questions' in request.session:
            del request.session['questions']
        request.session.modified = True

        activity_name = request.POST.get('activity_name')
        activity_type_id = request.GET.get('activity_type_id') or request.POST.get('activity_type_id')
        term_id = request.POST.get('term')
        additional_modules_ids = request.POST.getlist('additional_modules', [])
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        time_duration = request.POST.get('time_duration', 0) 
        passing_score = float(request.POST.get('passing_score', 0))
        passing_score_type = request.POST.get('passing_score_type')
        activity_instruction = request.POST.get('activity_instruction', '').strip()
        activity_file_instruction = request.FILES.get('activity_file_instruction')
        is_graded = request.POST.get('is_graded') == 'on'

        # Validate the optional instruction file (PDF or image, ≤10MB).
        if activity_file_instruction:
            ext = os.path.splitext(activity_file_instruction.name)[1].lower()
            allowed_exts = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.webp']
            if ext not in allowed_exts:
                messages.error(request, "Instruction file must be PDF or an image (jpg/png/gif/webp).")
                return self.get(request, subject_id)
            if activity_file_instruction.size > 10 * 1024 * 1024:
                messages.error(request, "Instruction file must be smaller than 10MB.")
                return self.get(request, subject_id)

        if passing_score_type == 'percentage':
            if passing_score > 100:
                messages.error(request, 'Passing score cannot be more than 100 for percentage type.')
                return self.get(request, subject_id)
            passing_score = (passing_score / 100) * 100

        elif passing_score_type == 'number':
            passing_score = passing_score

        try:
            max_retake = int(request.POST.get('max_retake', 2))
            if max_retake < 1:
                max_retake = 1
            elif max_retake > 50:
                max_retake = 50
        except ValueError:
            max_retake = 2

        retake_method = request.POST.get('retake_method', 'highest')
        remedial = request.POST.get('remedial') == 'on'
        shuffle_questions = request.POST.get('shuffle_questions') == 'on'
        remedial_students_ids = request.POST.getlist('remedial_students', None)

        allow_late_submission = request.POST.get('allow_late_submission') == 'on'
        try:
            late_submission_days = max(0, int(request.POST.get('late_submission_days', 0) or 0))
        except (TypeError, ValueError):
            late_submission_days = 0
        try:
            late_submission_penalty_percent = max(0, min(100, int(request.POST.get('late_submission_penalty_percent', 0) or 0)))
        except (TypeError, ValueError):
            late_submission_penalty_percent = 0

        activity_type = get_object_or_404(ActivityType, id=activity_type_id)
        term = get_object_or_404(Term, id=term_id)

        # Lesson selection is optional on this flow.

        start_time = parse_datetime(start_time)
        end_time = parse_datetime(end_time)

        if start_time >= end_time:
            messages.error(request, 'End time must be after start time.')
            return self.get(request, subject_id)

        with transaction.atomic():
            activity = Activity.objects.create(
                activity_name=activity_name,
                activity_type=activity_type,
                subject=subject,
                term=term,
                start_time=start_time,
                end_time=end_time,
                max_retake=max_retake,
                time_duration=time_duration,
                retake_method=retake_method,
                remedial=remedial,
                shuffle_questions=shuffle_questions,
                is_graded=is_graded,
                passing_score=passing_score,
                passing_score_type=passing_score_type,
                activity_instruction=activity_instruction,
                activity_file_instruction=activity_file_instruction,
                allow_late_submission=allow_late_submission,
                late_submission_days=late_submission_days,
                late_submission_penalty_percent=late_submission_penalty_percent,
            )
            
            additional_modules = Module.objects.filter(id__in=additional_modules_ids)
            activity.additional_modules.set(additional_modules)

        messages.success(request, "Assessment created successfully.")

        if remedial and remedial_students_ids:
            remedial_students = CustomUser.objects.filter(id__in=remedial_students_ids,subjectenrollment__subject=subject,subjectenrollment__semester=term.semester,subjectenrollment__status='enrolled')
            activity.remedial_students.set(remedial_students)
            for student in remedial_students:
                StudentActivity.objects.get_or_create(student=student, activity=activity, term=term, subject=subject)
        else:
            students = CustomUser.objects.filter(
                subjectenrollment__subject=subject,
                subjectenrollment__semester=term.semester,
                subjectenrollment__status='enrolled',
                profile__role__name__iexact='Student'
            ).distinct()
            for student in students:
                StudentActivity.objects.get_or_create(student=student, activity=activity, term=term, subject=subject) 

        # Store the created activity ID in session to prevent URL manipulation
        request.session['current_activity_id'] = activity.id
        request.session['current_activity_subject_id'] = subject.id

        # Major Assessment (canonical name: "Participation") is a direct-scoring
        # flow — skip the quiz-type picker and land the teacher straight on
        # the student-score roster.
        if activity_type.name.lower() == 'participation':
            participation_qt = QuizType.objects.filter(name='Participation').first()
            if participation_qt:
                return redirect(reverse('add_question', kwargs={
                    'activity_id': activity.id,
                    'quiz_type_id': participation_qt.id,
                }))

        return redirect(reverse('add_quiz_type', kwargs={'activity_id': activity.id}))


@login_required
@permission_required('activity.change_activity', raise_exception=True)
def UpdateAssessment(request, activity_id):
    activity = get_object_or_404(Activity, local_id=activity_id)
    subject = activity.subject
    has_submissions = activity_has_submissions(activity)

    now = timezone.localtime(timezone.now())
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()
    current_term = Term.objects.filter(semester=current_semester, start_date__lte=now, end_date__gte=now).first()
    terms = Term.objects.filter(semester=current_semester)

    if request.method == 'POST':
        if has_submissions:
            return _apply_schedule_only_update(request, activity, 'update-assessment')
        form = ActivityForm(request.POST, request.FILES, instance=activity, terms_queryset=terms)
        remedial = request.POST.get('remedial') == 'on'
        shuffle_questions = request.POST.get('shuffle_questions') == 'on'
        is_graded = request.POST.get('is_graded') == 'on'
        remedial_students_ids = request.POST.getlist('remedial_students', None)
        additional_modules_ids = request.POST.getlist('additional_modules', [])
        activity_file_instruction = request.FILES.get('activity_file_instruction')

        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')

        if start_time and end_time and end_time <= start_time:
            messages.error(request, 'End time must be later than the start time.')
            return redirect('update-assessment', activity_id=activity_id)

        if activity_file_instruction:
            ext = os.path.splitext(activity_file_instruction.name)[1].lower()
            allowed = ['.pdf', '.jpg', '.jpeg', '.png']
            if ext not in allowed:
                messages.error(request, "Only PDF and image files are allowed.")
                return redirect('update-assessment', activity_id=activity_id)
            if activity_file_instruction.size > 10 * 1024 * 1024:
                messages.error(request, "File must be less than 10MB.")
                return redirect('update-assessment', activity_id=activity_id)

        # Lesson selection is optional on the regular update flow.

        if form.is_valid():
            activity_instance = form.save(commit=False)
            if activity_file_instruction:
                activity_instance.activity_file_instruction = activity_file_instruction
            activity_instance.save()
            form.save_m2m()
            
            additional_modules = Module.objects.filter(id__in=additional_modules_ids)
            activity.additional_modules.set(additional_modules)

            if remedial and remedial_students_ids:
                remedial_students = CustomUser.objects.filter(id__in=remedial_students_ids,subjectenrollment__subject=subject,subjectenrollment__status='enrolled')
                activity.remedial_students.set(remedial_students)
            else:
                activity.remedial_students.clear()

            students = CustomUser.objects.filter(
                subjectenrollment__subject=subject,
                subjectenrollment__status='enrolled',
                profile__role__name__iexact='Student'
            ).distinct()

            for student in students:
                student_activity, created = StudentActivity.objects.get_or_create(
                    student=student, activity=activity, term=activity.term, subject=subject
                )

            request.session['current_activity_id'] = activity_id
            request.session['current_activity_subject_id'] = subject.id
            messages.success(request, 'Assessment updated. You can now edit the questions.')
            return redirect('add_quiz_type', activity_id=activity_id)
        else:
            messages.error(request, 'There was an error updating the assessment. Please try again.')

    else:
        form = ActivityForm(instance=activity, terms_queryset=terms)

    return render(request, 'activity/assessments/update-assessment.html', {
        'form': form,
        'activity': activity,
        'modules': Module.objects.filter(subject=subject),
        'students': CustomUser.objects.filter(subjectenrollment__subject=subject, subjectenrollment__status='enrolled', profile__role__name__iexact='Student').distinct(),
        'terms': terms,
        'current_term': current_term,
        'has_submissions': has_submissions,
    })


@login_required
@permission_required('activity.change_activity', raise_exception=True)
def UpdateAssessmentCM(request, activity_id):
    activity = get_object_or_404(Activity, local_id=activity_id)
    subject = activity.subject
    subject_id = activity.subject.id
    subject = get_object_or_404(Subject, id=subject_id)
    has_submissions = activity_has_submissions(activity)

    now = timezone.localtime(timezone.now())
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()
    current_term = Term.objects.filter(semester=current_semester, start_date__lte=now, end_date__gte=now).first()
    terms = Term.objects.filter(semester=current_semester)

    if request.method == 'POST':
        if has_submissions:
            return _apply_schedule_only_update(request, activity, 'update-assessment-cm')
        form = ActivityForm(request.POST, request.FILES, instance=activity, terms_queryset=terms)
        remedial = request.POST.get('remedial') == 'on'
        remedial_students_ids = request.POST.getlist('remedial_students', None)
        additional_modules_ids = request.POST.getlist('additional_modules', [])
        
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')

        if start_time and end_time and end_time <= start_time:
            messages.error(request, 'End time must be later than the start time.')
            return redirect('update-assessment-cm', activity_id=activity_id)

        if form.is_valid():
            activity_instance = form.save(commit=False)
            activity_instance.save()
            form.save_m2m()
            
            additional_modules = Module.objects.filter(id__in=additional_modules_ids)
            activity.additional_modules.set(additional_modules)

            if remedial and remedial_students_ids:
                remedial_students = CustomUser.objects.filter(id__in=remedial_students_ids,subjectenrollment__subject=subject,subjectenrollment__status='enrolled')
                activity.remedial_students.set(remedial_students)
            else:
                activity.remedial_students.clear()

            if remedial and remedial_students_ids:
                for student_id in remedial_students_ids:
                    student = CustomUser.objects.get(local_id=student_id)
                    student_activity = StudentActivity.objects.filter(student=student, activity=activity, term=activity.term).first()
                    if not student_activity:
                        StudentActivity.objects.create(student=student, activity=activity, term=activity.term, subject=subject)
            else:
                students = CustomUser.objects.filter(subjectenrollment__subject=subject, subjectenrollment__status='enrolled', profile__role__name__iexact='Student').distinct()
                for student in students:
                    student_activity = StudentActivity.objects.filter(student=student, activity=activity, term=activity.term).first()
                    if not student_activity:
                        StudentActivity.objects.create(student=student, activity=activity, term=activity.term, subject=subject)

            if activity.term and activity.start_time and activity.end_time:
                students = CustomUser.objects.filter(subjectenrollment__subject=subject, subjectenrollment__status='enrolled', profile__role__name__iexact='Student').distinct()
                for student in students:
                    student_activity = StudentActivity.objects.filter(student=student, activity=activity).first()
                    if not student_activity:
                        student_activity = StudentActivity.objects.create(student=student, activity=activity, subject=subject)

            request.session['current_activity_id'] = activity_id
            request.session['current_activity_subject_id'] = subject.id
            messages.success(request, 'Assessment updated. You can now edit the questions.')
            return redirect('add_quiz_typeCM', activity_id=activity_id)
        else:
            messages.error(request, 'There was an error updating the assessment. Please try again.')
    else:
        form = ActivityForm(instance=activity, terms_queryset=terms)

    return render(request, 'activity/assessments/update-assessment-cm.html', {
        'form': form,
        'subject': subject,
        'activity': activity,
        'modules': Module.objects.filter(subject=subject),
        'students': CustomUser.objects.filter(subjectenrollment__subject=subject, subjectenrollment__status='enrolled', profile__role__name__iexact='Student').distinct(),
        'terms': terms,
        'current_term': current_term,
        'has_submissions': has_submissions,
    })


# ─── Click-to-edit endpoint ───────────────────────────────────────────
# Thin PATCH handler for the cl-edit-inline engine. Renames an Activity
# (and could be extended to other single-field edits later). Returns
# JSON the engine knows how to interpret:
#   { "ok": true,  "value": "<saved string>" }                                  (200)
#   { "ok": false, "error": "<human message>" }                                 (400)
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

@login_required
@permission_required('activity.change_activity', raise_exception=True)
@require_http_methods(["PATCH"])
def rename_activity(request, activity_id):
    activity = get_object_or_404(Activity, local_id=activity_id)
    subject = activity.subject

    has_access, _ = check_subject_access(request, subject, require_teacher=True)
    if not has_access:
        return JsonResponse({'ok': False, 'error': 'Permission denied.'}, status=403)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Malformed request body.'}, status=400)

    new_name = (payload.get('activity_name') or '').strip()
    if not new_name:
        return JsonResponse({'ok': False, 'error': 'Activity name cannot be empty.'}, status=400)
    if len(new_name) < 2:
        return JsonResponse({'ok': False, 'error': 'Activity name must be at least 2 characters.'}, status=400)
    if len(new_name) > 100:
        return JsonResponse({'ok': False, 'error': 'Activity name must be at most 100 characters.'}, status=400)

    activity.activity_name = new_name
    activity.save(update_fields=['activity_name'])

    return JsonResponse({'ok': True, 'value': new_name})

