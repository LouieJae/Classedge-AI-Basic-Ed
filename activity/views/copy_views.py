from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from activity.models import Activity
from subject.models import Subject
from activity.forms import SubjectToSubjectActivityCopyForm
from activity.utils import copy_activities_from_subject
from datetime import timedelta, datetime
from django.utils import timezone
from course.models import Term, Semester
from django.db import models

@login_required
def copy_assessments_from_subject(request, target_subject_id):
    target_subject = get_object_or_404(Subject, id=target_subject_id)
    if not (request.user == target_subject.assign_teacher or 
            request.user in target_subject.collaborators.all() or 
            request.user.is_admin):
        messages.error(request, "You don't have permission to copy activities to this subject.")
        return redirect('material-list', id=target_subject_id)
    
    if request.method == 'POST':
        form = SubjectToSubjectActivityCopyForm(request.POST, target_subject=target_subject, user=request.user)
        
        if form.is_valid():
            source_subject = form.cleaned_data['source_subject']
            selected_activities = form.cleaned_data['selected_activities']
            
            if not selected_activities:
                messages.error(request, 'No activities were selected for copying. Please select at least one activity.')
                return redirect('copy-assessments-from-subject', target_subject_id=target_subject_id)
            
            # Get custom dates from form
            start_time_str = request.POST.get('start_time')
            end_time_str = request.POST.get('end_time')
            term_id = request.POST.get('term')
            module_ids = request.POST.getlist('modules')  # Get selected modules (multiple)
            
            # Get current semester for target subject
            current_semester = Semester.current()
            
            # Get selected term or use first term from current semester
            if term_id:
                try:
                    selected_term = Term.objects.get(id=term_id, semester=current_semester)
                except Term.DoesNotExist:
                    selected_term = Term.objects.filter(semester=current_semester).first()
            else:
                selected_term = Term.objects.filter(semester=current_semester).first()
            
            # Parse dates with timezone awareness
            default_start_time = timezone.localtime(timezone.now())
            default_end_time = default_start_time + timedelta(days=7)
            
            if start_time_str:
                try:
                    start_time = datetime.fromisoformat(start_time_str)
                    if timezone.is_naive(start_time):
                        start_time = timezone.make_aware(start_time)
                except (ValueError, TypeError):
                    start_time = default_start_time
            else:
                start_time = default_start_time
            
            if end_time_str:
                try:
                    end_time = datetime.fromisoformat(end_time_str)
                    if timezone.is_naive(end_time):
                        end_time = timezone.make_aware(end_time)
                except (ValueError, TypeError):
                    end_time = default_end_time
            else:
                end_time = default_end_time
            
            # Get selected modules from target subject
            from module.models import Module
            selected_modules = []
            if module_ids:
                selected_modules = Module.objects.filter(
                    id__in=module_ids, 
                    subject=target_subject
                ).all()
            
            # Copy activities with custom dates, term, and modules
            copied_count = copy_activities_from_subject(
                source_subject.id, 
                target_subject.id, 
                [activity.id for activity in selected_activities],
                start_time=start_time,
                end_time=end_time,
                term=selected_term,
                target_modules=list(selected_modules)
            )
            
            messages.success(request, f'Successfully copied {copied_count} activities from {source_subject.subject_name} to {target_subject.subject_name}!')
            return redirect('subject-assessment-list', subject_id=target_subject_id)
    else:
        form = SubjectToSubjectActivityCopyForm(target_subject=target_subject, user=request.user)
    
    # Get current semester and calculate default dates for display
    from module.models import Module
    current_semester = Semester.current()
    current_term = Term.objects.filter(semester=current_semester).first() if current_semester else None
    available_terms = Term.objects.filter(semester=current_semester) if current_semester else Term.objects.none()
    available_modules = Module.objects.filter(subject=target_subject, term__isnull=False)
    start_time = timezone.localtime(timezone.now())
    end_time = start_time + timedelta(days=7)
    
    return render(request, 'activity/assessments/copy-assessments-from-subject.html', {
        'form': form,
        'target_subject': target_subject,
        'current_term': current_term,
        'available_terms': available_terms,
        'available_modules': available_modules,
        'default_start_time': start_time,
        'default_end_time': end_time,
    })


@login_required
def get_subject_assessments(request, subject_id):
    """AJAX endpoint to get activities for a specific subject"""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        subject = get_object_or_404(Subject, id=subject_id)
        activities = Activity.objects.filter(subject=subject).exclude(activity_type__name__iexact='participation')
        
        activities_data = []
        for activity in activities:
            activity_data = {
                'id': activity.id,
                'activity_name': activity.activity_name,
                'activity_type': activity.activity_type.name if activity.activity_type else None,
                'term': activity.term.term_name if activity.term else None,
                'additional_modules': [module.file_name for module in activity.additional_modules.all()],
                'start_time': activity.start_time.isoformat() if activity.start_time else None,
                'end_time': activity.end_time.isoformat() if activity.end_time else None,
            }
            activities_data.append(activity_data)
        
        return JsonResponse({'activities': activities_data})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def check_subject_assessment_exists(request, target_subject_id):
    """Check if an activity already exists in the target subject"""
    if request.method == 'GET' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        activity_id = request.GET.get('activity_id')
        target_subject = get_object_or_404(Subject, id=target_subject_id)
        
        activity = get_object_or_404(Activity, pk=activity_id)
        
        exists = Activity.objects.filter(
            activity_name=activity.activity_name,
            subject=target_subject
        ).exists()
        
        return JsonResponse({'exists': exists})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def copy_assessments(request, subject_id):
    """Copy activities from previous semesters of the same subject"""
    
    subject = get_object_or_404(Subject, id=subject_id)
    if not (request.user == subject.assign_teacher or 
            request.user in subject.collaborators.all() or 
            request.user.is_admin):
        messages.error(request, "You don't have permission to copy activities for this subject.")
        return redirect('subject-assessment-list', subject_id=subject_id)
    
    if request.method == 'POST':
        selected_activity_ids = request.POST.getlist('selected_activities')
        start_time_str = request.POST.get('start_time')
        end_time_str = request.POST.get('end_time')
        term_id = request.POST.get('term')
        module_ids = request.POST.getlist('modules')
        
        if not selected_activity_ids:
            messages.error(request, 'No activities were selected for copying.')
            return redirect('copy_activities', subject_id=subject_id)
        
        # Get current semester
        current_semester = Semester.current()
        
        # Get selected term
        if term_id:
            try:
                selected_term = Term.objects.get(id=term_id, semester=current_semester)
            except Term.DoesNotExist:
                selected_term = Term.objects.filter(semester=current_semester).first()
        else:
            selected_term = Term.objects.filter(semester=current_semester).first()
        
        # Parse dates
        default_start_time = timezone.localtime(timezone.now())
        default_end_time = default_start_time + timedelta(days=7)
        
        if start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str)
                if timezone.is_naive(start_time):
                    start_time = timezone.make_aware(start_time)
            except (ValueError, TypeError):
                start_time = default_start_time
        else:
            start_time = default_start_time
        
        if end_time_str:
            try:
                end_time = datetime.fromisoformat(end_time_str)
                if timezone.is_naive(end_time):
                    end_time = timezone.make_aware(end_time)
            except (ValueError, TypeError):
                end_time = default_end_time
        else:
            end_time = default_end_time
        
        # Get selected modules
        from module.models import Module
        selected_modules = []
        if module_ids:
            selected_modules = Module.objects.filter(
                id__in=module_ids, 
                subject=subject
            ).all()
        
        # Copy activities
        copied_count = 0
        for activity_id in selected_activity_ids:
            try:
                activity = Activity.objects.get(pk=activity_id)
                
                # Check if activity already exists in current semester
                if Activity.objects.filter(
                    activity_name=activity.activity_name,
                    subject=subject,
                    term=selected_term
                ).exists():
                    continue
                
                # Create new activity
                new_activity = Activity.objects.create(
                    activity_name=activity.activity_name,
                    activity_type=activity.activity_type,
                    subject=subject,
                    term=selected_term,
                    start_time=start_time,
                    end_time=end_time,
                    show_score=activity.show_score,
                    remedial=False,
                    max_retake=activity.max_retake,
                    time_duration=activity.time_duration,
                    max_score=activity.max_score,
                    status=activity.status,
                    passing_score=activity.passing_score,
                    passing_score_type=activity.passing_score_type,
                    retake_method=activity.retake_method,
                    activity_instruction=activity.activity_instruction,
                    classroom_mode=activity.classroom_mode,
                    shuffle_questions=activity.shuffle_questions
                )
                
                # Add modules
                if selected_modules:
                    new_activity.additional_modules.add(*selected_modules)
                
                # Copy questions
                from activity.models import ActivityQuestion
                questions = ActivityQuestion.objects.filter(activity=activity)
                for question in questions:
                    new_question = ActivityQuestion.objects.create(
                        activity=new_activity,
                        subject=new_activity.subject,
                        question_text=question.question_text,
                        correct_answer=question.correct_answer,
                        quiz_type=question.quiz_type,
                        score=question.score
                    )
                    
                    for choice in question.choices.all():
                        new_question.choices.create(
                            choice_text=choice.choice_text,
                            is_left_side=choice.is_left_side
                        )
                
                copied_count += 1
            except Activity.DoesNotExist:
                continue
        
        messages.success(request, f'Successfully copied {copied_count} activities!')
        return redirect('subject-assessment-list', subject_id=subject_id)
    
    # GET request - display form
    current_semester = Semester.current()
    current_term = Term.objects.filter(semester=current_semester).first() if current_semester else None
    available_terms = Term.objects.filter(semester=current_semester) if current_semester else Term.objects.none()
    
    # Get activities from previous semesters
    from module.models import Module
    available_modules = Module.objects.filter(subject=subject, term__isnull=False)
    
    # Get all subjects where user is teacher, collaborator, or admin
    if request.user.is_admin:
        all_subjects = Subject.objects.all().order_by('subject_name')
    else:
        all_subjects = Subject.objects.filter(
            models.Q(assign_teacher=request.user) | models.Q(collaborators=request.user)
        ).distinct().order_by('subject_name')
    
    # Get activities grouped by semester and term (default: current subject)
    activities_by_semester = {}
    previous_activities = Activity.objects.filter(
        subject=subject,
        term__isnull=False
    ).exclude(
        term__semester=current_semester
    ).order_by('-term__semester__start_date', 'term__term_name')
    
    for activity in previous_activities:
        semester = activity.term.semester
        term = activity.term
        
        if semester not in activities_by_semester:
            activities_by_semester[semester] = {}
        if term not in activities_by_semester[semester]:
            activities_by_semester[semester][term] = []
        
        activities_by_semester[semester][term].append(activity)
        
    start_time = timezone.localtime(timezone.now())
    end_time = start_time + timedelta(days=7)
    
    return render(request, 'activity/assessments/copy-assessments-from-previous-semester.html', {
        'subject': subject,
        'all_subjects': all_subjects,
        'activities_by_semester': activities_by_semester,
        'current_term': current_term,
        'available_terms': available_terms,
        'available_modules': available_modules,
        'default_start_time': start_time,
        'default_end_time': end_time,
    })


# ─── Classroom Mode variants ───────────────────────────────────────────
# These reuse the exact business logic of copy_assessments and
# copy_assessments_from_subject but render the CM-style standalone templates
# and redirect back to assessment_list_cm on success so the user never leaves
# the projector shell.

@login_required
def copy_assessments_cm(request, subject_id):
    """CM variant of copy_assessments — renders the CM template and redirects to assessment_list_cm."""
    from module.models import Module

    subject = get_object_or_404(Subject, id=subject_id)
    if not (request.user == subject.assign_teacher or
            request.user in subject.collaborators.all() or
            request.user.is_admin):
        messages.error(request, "You don't have permission to copy activities for this subject.")
        return redirect('assessment-list-cm', subject_id=subject_id)

    if request.method == 'POST':
        selected_activity_ids = request.POST.getlist('selected_activities')
        start_time_str = request.POST.get('start_time')
        end_time_str = request.POST.get('end_time')
        term_id = request.POST.get('term')
        module_ids = request.POST.getlist('modules')

        if not selected_activity_ids:
            messages.error(request, 'No activities were selected for copying.')
            return redirect('copy_assessments_cm', subject_id=subject_id)

        current_semester = Semester.current()
        if term_id:
            try:
                selected_term = Term.objects.get(id=term_id, semester=current_semester)
            except Term.DoesNotExist:
                selected_term = Term.objects.filter(semester=current_semester).first()
        else:
            selected_term = Term.objects.filter(semester=current_semester).first()

        default_start = timezone.localtime(timezone.now())
        default_end = default_start + timedelta(days=7)
        try:
            start_time = datetime.fromisoformat(start_time_str) if start_time_str else default_start
            if timezone.is_naive(start_time):
                start_time = timezone.make_aware(start_time)
        except (ValueError, TypeError):
            start_time = default_start
        try:
            end_time = datetime.fromisoformat(end_time_str) if end_time_str else default_end
            if timezone.is_naive(end_time):
                end_time = timezone.make_aware(end_time)
        except (ValueError, TypeError):
            end_time = default_end

        selected_modules = []
        if module_ids:
            selected_modules = Module.objects.filter(id__in=module_ids, subject=subject).all()

        copied_count = 0
        for activity_id in selected_activity_ids:
            try:
                activity = Activity.objects.get(pk=activity_id)
                if Activity.objects.filter(
                    activity_name=activity.activity_name,
                    subject=subject,
                    term=selected_term,
                ).exists():
                    continue
                new_activity = Activity.objects.create(
                    activity_name=activity.activity_name,
                    activity_type=activity.activity_type,
                    subject=subject,
                    term=selected_term,
                    start_time=start_time,
                    end_time=end_time,
                    show_score=activity.show_score,
                    remedial=False,
                    max_retake=activity.max_retake,
                    time_duration=activity.time_duration,
                    max_score=activity.max_score,
                    status=activity.status,
                    passing_score=activity.passing_score,
                    passing_score_type=activity.passing_score_type,
                    retake_method=activity.retake_method,
                    activity_instruction=activity.activity_instruction,
                    classroom_mode=activity.classroom_mode,
                    shuffle_questions=activity.shuffle_questions,
                )
                if selected_modules:
                    new_activity.additional_modules.add(*selected_modules)
                from activity.models import ActivityQuestion
                for question in ActivityQuestion.objects.filter(activity=activity):
                    new_question = ActivityQuestion.objects.create(
                        activity=new_activity, subject=new_activity.subject,
                        question_text=question.question_text,
                        correct_answer=question.correct_answer,
                        quiz_type=question.quiz_type, score=question.score,
                    )
                    for choice in question.choices.all():
                        new_question.choices.create(
                            choice_text=choice.choice_text,
                            is_left_side=choice.is_left_side,
                        )
                copied_count += 1
            except Activity.DoesNotExist:
                continue

        messages.success(request, f'Successfully copied {copied_count} activities!')
        return redirect('assessment-list-cm', subject_id=subject_id)

    current_semester = Semester.current()
    current_term = Term.objects.filter(semester=current_semester).first() if current_semester else None
    available_terms = Term.objects.filter(semester=current_semester) if current_semester else Term.objects.none()
    available_modules = Module.objects.filter(subject=subject, term__isnull=False)

    if request.user.is_admin:
        all_subjects = Subject.objects.all().order_by('subject_name')
    else:
        all_subjects = Subject.objects.filter(
            models.Q(assign_teacher=request.user) | models.Q(collaborators=request.user)
        ).distinct().order_by('subject_name')

    activities_by_semester = {}
    previous_activities = Activity.objects.filter(
        subject=subject, term__isnull=False,
    ).exclude(term__semester=current_semester).order_by('-term__semester__start_date', 'term__term_name')
    for activity in previous_activities:
        sem = activity.term.semester
        trm = activity.term
        if sem not in activities_by_semester:
            activities_by_semester[sem] = {}
        if trm not in activities_by_semester[sem]:
            activities_by_semester[sem][trm] = []
        activities_by_semester[sem][trm].append(activity)

    start_time = timezone.localtime(timezone.now())
    end_time = start_time + timedelta(days=7)

    return render(request, 'activity/assessments/copy-assessments-from-previous-semester-cm.html', {
        'subject': subject,
        'all_subjects': all_subjects,
        'activities_by_semester': activities_by_semester,
        'current_term': current_term,
        'available_terms': available_terms,
        'available_modules': available_modules,
        'default_start_time': start_time,
        'default_end_time': end_time,
    })


@login_required
def copy_assessments_from_subject_cm(request, target_subject_id):
    """CM variant of copy_assessments_from_subject — renders CM template, redirects to assessment_list_cm."""
    from module.models import Module

    target_subject = get_object_or_404(Subject, id=target_subject_id)
    if not (request.user == target_subject.assign_teacher or
            request.user in target_subject.collaborators.all() or
            request.user.is_admin):
        messages.error(request, "You don't have permission to copy activities to this subject.")
        return redirect('assessment-list-cm', subject_id=target_subject_id)

    if request.method == 'POST':
        form = SubjectToSubjectActivityCopyForm(request.POST, target_subject=target_subject, user=request.user)
        if form.is_valid():
            source_subject = form.cleaned_data['source_subject']
            selected_activities = form.cleaned_data['selected_activities']

            if not selected_activities:
                messages.error(request, 'No activities were selected for copying.')
                return redirect('copy-assessments-from-subject-cm', target_subject_id=target_subject_id)

            term_id = request.POST.get('term')
            current_semester = Semester.current()
            if term_id:
                try:
                    selected_term = Term.objects.get(id=term_id, semester=current_semester)
                except Term.DoesNotExist:
                    selected_term = Term.objects.filter(semester=current_semester).first()
            else:
                selected_term = Term.objects.filter(semester=current_semester).first()

            module_ids = request.POST.getlist('modules')
            selected_modules = Module.objects.filter(id__in=module_ids, subject=target_subject) if module_ids else Module.objects.none()

            default_start = timezone.localtime(timezone.now())
            default_end = default_start + timedelta(days=7)
            try:
                start_time = datetime.fromisoformat(request.POST.get('start_time') or '') or default_start
                if timezone.is_naive(start_time):
                    start_time = timezone.make_aware(start_time)
            except (ValueError, TypeError):
                start_time = default_start
            try:
                end_time = datetime.fromisoformat(request.POST.get('end_time') or '') or default_end
                if timezone.is_naive(end_time):
                    end_time = timezone.make_aware(end_time)
            except (ValueError, TypeError):
                end_time = default_end

            copied_count = copy_activities_from_subject(
                source_subject.id, target_subject.id,
                [a.id for a in selected_activities],
                start_time=start_time, end_time=end_time,
                term=selected_term, target_modules=list(selected_modules),
            )
            messages.success(request, f'Successfully copied {copied_count} activities from {source_subject.subject_name} to {target_subject.subject_name}!')
            return redirect('assessment-list-cm', subject_id=target_subject_id)
    else:
        form = SubjectToSubjectActivityCopyForm(target_subject=target_subject, user=request.user)

    current_semester = Semester.current()
    current_term = Term.objects.filter(semester=current_semester).first() if current_semester else None
    available_terms = Term.objects.filter(semester=current_semester) if current_semester else Term.objects.none()
    available_modules = Module.objects.filter(subject=target_subject, term__isnull=False)
    start_time = timezone.localtime(timezone.now())
    end_time = start_time + timedelta(days=7)

    return render(request, 'activity/assessments/copy-assessments-from-subject-cm.html', {
        'form': form,
        'target_subject': target_subject,
        'subject': target_subject,
        'current_term': current_term,
        'available_terms': available_terms,
        'available_modules': available_modules,
        'default_start_time': start_time,
        'default_end_time': end_time,
    })


@login_required
def check_assessment_exists(request, subject_id):
    """Check if an activity already exists in the current semester"""
    if request.method == 'GET' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        activity_id = request.GET.get('activity_id')
        subject = get_object_or_404(Subject, id=subject_id)
        current_semester = Semester.current()
        
        activity = get_object_or_404(Activity, pk=activity_id)
        current_term = Term.objects.filter(semester=current_semester).first()
        
        exists = Activity.objects.filter(
            activity_name=activity.activity_name,
            subject=subject,
            term=current_term
        ).exists()
        
        return JsonResponse({'exists': exists})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def get_subject_assessments_by_semester(request, subject_id):
    """Get activities from a subject grouped by semester and term (AJAX endpoint)"""
    if request.method == 'GET' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        subject = get_object_or_404(Subject, id=subject_id)
        current_semester = Semester.current()
        
        activities_by_semester = {}
        previous_activities = Activity.objects.filter(
            subject=subject,
            term__isnull=False
        ).exclude(
            term__semester=current_semester
        ).order_by('-term__semester__start_date', 'term__term_name')

        for activity in previous_activities:
            semester = activity.term.semester
            term = activity.term
            
            semester_key = f"{semester.id}|{semester.semester_name}"
            term_key = f"{term.id}|{term.term_name}"
                        
            if semester_key not in activities_by_semester:
                activities_by_semester[semester_key] = {}
            if term_key not in activities_by_semester[semester_key]:
                activities_by_semester[semester_key][term_key] = []
            
            activities_by_semester[semester_key][term_key].append({
                'id': activity.id,
                'activity_name': activity.activity_name,
                'activity_type': activity.activity_type.name if activity.activity_type else None,
                'start_time': activity.start_time.isoformat() if activity.start_time else None,
                'end_time': activity.end_time.isoformat() if activity.end_time else None,
                'term': term.term_name,
            })
        
        return JsonResponse({'activities_by_semester': activities_by_semester})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)
