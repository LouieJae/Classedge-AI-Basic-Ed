from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from subject.models import Subject
from module.models.module import Module
from module.forms import SubjectToSubjectCopyForm, CopyLessonForm
from course.models import Term, Semester
from datetime import timedelta, datetime

@login_required
def copy_lessons(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    current_semester = Semester.current()

    # Get all subjects for the dropdown (filter by teacher if needed)
    if request.user.is_admin:
        all_subjects = Subject.objects.all().order_by('subject_name')
    else:
        # Show subjects where user is teacher or collaborator
        all_subjects = Subject.objects.filter(
            Q(assign_teacher=request.user) | 
            Q(substitute_teacher=request.user) |
            Q(collaborators=request.user)
        ).distinct().order_by('subject_name')

    # Default: show lessons from current subject's previous semesters
    previous_modules = Module.objects.filter(subject=subject).exclude(term__semester=current_semester).filter(term__isnull=False)

    modules_by_semester = {}
    for module in previous_modules:
        semester = module.term.semester
        term = module.term
        if semester not in modules_by_semester:
            modules_by_semester[semester] = {}
        if term not in modules_by_semester[semester]:
            modules_by_semester[semester][term] = []
        modules_by_semester[semester][term].append(module)

    if request.method == 'POST':
        form = CopyLessonForm(request.POST, subject=subject, current_semester=current_semester)
        selected_module_ids = request.POST.getlist('selected_modules')

        if not selected_module_ids:
            messages.error(request, 'No lessons were selected for copying. Please select at least one lesson.')
            return redirect('material-list', id=subject.id)

        if form.is_valid():
            selected_modules = form.cleaned_data['selected_modules']
            
            # Get selected term from form or use first term from current semester
            term_id = request.POST.get('term')
            if term_id:
                try:
                    current_term = Term.objects.get(id=term_id, semester=current_semester)
                except Term.DoesNotExist:
                    current_term = Term.objects.filter(semester=current_semester).first()
            else:
                current_term = Term.objects.filter(semester=current_semester).first()
            
            # Get dates from form or use defaults
            start_date_str = request.POST.get('start_date')
            end_date_str = request.POST.get('end_date')
            
            if start_date_str:
                try:
                    start_date = datetime.fromisoformat(start_date_str)
                    # Make timezone-aware if naive
                    if timezone.is_naive(start_date):
                        start_date = timezone.make_aware(start_date)
                except (ValueError, TypeError):
                    start_date = timezone.localtime(timezone.now())
            else:
                start_date = timezone.localtime(timezone.now())
            
            if end_date_str:
                try:
                    end_date = datetime.fromisoformat(end_date_str)
                    # Make timezone-aware if naive
                    if timezone.is_naive(end_date):
                        end_date = timezone.make_aware(end_date)
                except (ValueError, TypeError):
                    end_date = start_date + timedelta(days=7)
            else:
                end_date = start_date + timedelta(days=7)

            copied_count = 0
            for module in selected_modules:
                existing_module = Module.objects.filter(
                    subject=subject,
                    file_name=module.file_name,
                    term__semester=current_semester
                ).exists()
                if existing_module:
                    continue

                new_module = Module.objects.create(
                    file_name=module.file_name,
                    file=module.file,
                    subject=subject,  # Copy to current subject
                    url=module.url,
                    description=module.description,
                    term=current_term,
                    start_date=start_date,
                    end_date=end_date,
                )
                new_module.display_lesson_for_selected_users.set(module.display_lesson_for_selected_users.all())
                new_module.save()
                copied_count += 1

            messages.success(request, f'Successfully copied {copied_count} lessons to {subject.subject_name}!')
            return redirect('material-list', id=subject.id)
    else:
        form = CopyLessonForm(subject=subject, current_semester=current_semester)

    # Get current term and calculate default dates for display
    current_term = Term.objects.filter(semester=current_semester).first()
    available_terms = Term.objects.filter(semester=current_semester).order_by('term_name') if current_semester else Term.objects.none()
    start_date = timezone.localtime(timezone.now())
    end_date = start_date + timedelta(days=7)
    
    return render(request, 'module/import-material-from-previous-semester.html', {
        'form': form,
        'modules_by_semester': modules_by_semester,
        'subject': subject,
        'all_subjects': all_subjects,
        'current_term': current_term,
        'available_terms': available_terms,
        'default_start_date': start_date,
        'default_end_date': end_date,
    })


@login_required
def copy_lessons_cm(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    current_semester = Semester.current()

    # Get all subjects for the dropdown (filter by teacher if needed)
    if request.user.is_admin:
        all_subjects = Subject.objects.all().order_by('subject_name')
    else:
        # Show subjects where user is teacher or collaborator
        all_subjects = Subject.objects.filter(
            Q(assign_teacher=request.user) | 
            Q(substitute_teacher=request.user) |
            Q(collaborators=request.user)
        ).distinct().order_by('subject_name')

    # Default: show lessons from current subject's previous semesters
    previous_modules = Module.objects.filter(subject=subject).exclude(term__semester=current_semester).filter(term__isnull=False)

    modules_by_semester = {}
    for module in previous_modules:
        semester = module.term.semester
        term = module.term
        if semester not in modules_by_semester:
            modules_by_semester[semester] = {}
        if term not in modules_by_semester[semester]:
            modules_by_semester[semester][term] = []
        modules_by_semester[semester][term].append(module)

    if request.method == 'POST':
        form = CopyLessonForm(request.POST, subject=subject, current_semester=current_semester)
        selected_module_ids = request.POST.getlist('selected_modules')

        if not selected_module_ids:
            messages.error(request, 'No lessons were selected for copying. Please select at least one lesson.')
            return redirect('material-list', id=subject.id)

        if form.is_valid():
            selected_modules = form.cleaned_data['selected_modules']
            
            # Get selected term from form or use first term from current semester
            term_id = request.POST.get('term')
            if term_id:
                try:
                    current_term = Term.objects.get(id=term_id, semester=current_semester)
                except Term.DoesNotExist:
                    current_term = Term.objects.filter(semester=current_semester).first()
            else:
                current_term = Term.objects.filter(semester=current_semester).first()
            
            # Get dates from form or use defaults
            start_date_str = request.POST.get('start_date')
            end_date_str = request.POST.get('end_date')
            
            if start_date_str:
                try:
                    start_date = datetime.fromisoformat(start_date_str)
                    # Make timezone-aware if naive
                    if timezone.is_naive(start_date):
                        start_date = timezone.make_aware(start_date)
                except (ValueError, TypeError):
                    start_date = timezone.localtime(timezone.now())
            else:
                start_date = timezone.localtime(timezone.now())
            
            if end_date_str:
                try:
                    end_date = datetime.fromisoformat(end_date_str)
                    # Make timezone-aware if naive
                    if timezone.is_naive(end_date):
                        end_date = timezone.make_aware(end_date)
                except (ValueError, TypeError):
                    end_date = start_date + timedelta(days=7)
            else:
                end_date = start_date + timedelta(days=7)

            copied_count = 0
            for module in selected_modules:
                existing_module = Module.objects.filter(
                    subject=subject,
                    file_name=module.file_name,
                    term__semester=current_semester
                ).exists()
                if existing_module:
                    continue

                new_module = Module.objects.create(
                    file_name=module.file_name,
                    file=module.file,
                    subject=subject,  # Copy to current subject
                    url=module.url,
                    description=module.description,
                    term=current_term,
                    start_date=start_date,
                    end_date=end_date,
                )
                new_module.display_lesson_for_selected_users.set(module.display_lesson_for_selected_users.all())
                new_module.save()
                copied_count += 1

            messages.success(request, f'Successfully copied {copied_count} lessons to {subject.subject_name}!')
            return redirect('material-list', id=subject.id)
    else:
        form = CopyLessonForm(subject=subject, current_semester=current_semester)

    # Get current term and calculate default dates for display
    current_term = Term.objects.filter(semester=current_semester).first()
    available_terms = Term.objects.filter(semester=current_semester).order_by('term_name') if current_semester else Term.objects.none()
    start_date = timezone.localtime(timezone.now())
    end_date = start_date + timedelta(days=7)
    
    return render(request, 'module/import-material-from-previous-semester-cm.html', {
        'form': form,
        'modules_by_semester': modules_by_semester,
        'subject': subject,
        'all_subjects': all_subjects,
        'current_term': current_term,
        'available_terms': available_terms,
        'default_start_date': start_date,
        'default_end_date': end_date,
    })


@login_required
def get_subject_modules(request, subject_id):
    """Get modules from a subject, excluding current semester (for copy functionality)"""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        subject = get_object_or_404(Subject, id=subject_id)
        current_semester = Semester.current()
        
        # Get modules from previous semesters only
        modules = Module.objects.filter(
            subject=subject,
            term__isnull=False
        ).exclude(term__semester=current_semester).order_by('-term__semester__start_date', 'term__term_name')

        # Group by semester and term
        modules_by_semester = {}
        for module in modules:
            semester = module.term.semester
            term = module.term
            
            semester_key = f"{semester.id}|{semester.semester_name}"
            term_key = f"{term.id}|{term.term_name}"
            
            if semester_key not in modules_by_semester:
                modules_by_semester[semester_key] = {}
            if term_key not in modules_by_semester[semester_key]:
                modules_by_semester[semester_key][term_key] = []
            
            module_data = {
                'id': module.id,
                'file_name': module.file_name,
                'start_date': module.start_date.isoformat() if module.start_date else None,
                'end_date': module.end_date.isoformat() if module.end_date else None,
                'term': module.term.term_name if module.term else None,
                'description': module.description or ''
            }
            modules_by_semester[semester_key][term_key].append(module_data)

        return JsonResponse(modules_by_semester)


@login_required
def check_lesson_exists(request, subject_id):
    if request.method == 'GET' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        lesson_id = request.GET.get('lesson_id')
        subject = get_object_or_404(Subject, id=subject_id)
        current_semester = Semester.current()

        module = get_object_or_404(Module, id=lesson_id)

        exists = Module.objects.filter(
            file_name=module.file_name,
            subject=subject,
            term__semester=current_semester
        ).exists()

        return JsonResponse({'exists': exists})

    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def copy_lessons_from_subject(request, target_subject_id):
    target_subject = get_object_or_404(Subject, id=target_subject_id)

    if not (request.user == target_subject.assign_teacher or request.user.is_admin):
        messages.error(request, "You don't have permission to copy lessons to this subject.")
        return redirect('material-list', id=target_subject_id)

    if request.method == 'POST':
        form = SubjectToSubjectCopyForm(request.POST, target_subject=target_subject, user=request.user)

        if form.is_valid():
            source_subject = form.cleaned_data['source_subject']
            selected_modules = form.cleaned_data['selected_modules']

            if not selected_modules:
                messages.error(request, 'No lessons were selected for copying. Please select at least one lesson.')
                return redirect('copy-materials-from-subject', target_subject_id=target_subject_id)

            # Get dates from form or use defaults
            start_date_str = request.POST.get('start_date')
            end_date_str = request.POST.get('end_date')
            use_override = request.POST.get('use_override_dates') == 'on'
            term_id = request.POST.get('term')
            
            # Get current semester for target subject
            current_semester = Semester.current()
            
            # Get selected term or use first term from current semester
            if term_id:
                try:
                    current_term = Term.objects.get(id=term_id, semester=current_semester)
                except Term.DoesNotExist:
                    current_term = Term.objects.filter(semester=current_semester).first()
            else:
                current_term = Term.objects.filter(semester=current_semester).first()
            
            # Calculate default dates (today + 7 days)
            default_start_date = timezone.localtime(timezone.now())
            default_end_date = default_start_date + timedelta(days=7)
            
            if use_override and start_date_str and end_date_str:
                try:
                    start_date = datetime.fromisoformat(start_date_str)
                    end_date = datetime.fromisoformat(end_date_str)
                    # Make timezone-aware if naive
                    if timezone.is_naive(start_date):
                        start_date = timezone.make_aware(start_date)
                    if timezone.is_naive(end_date):
                        end_date = timezone.make_aware(end_date)
                except (ValueError, TypeError) as e:
                    start_date = default_start_date
                    end_date = default_end_date
            else:
                # When override is unchecked, use current semester defaults (today + 7 days)
                start_date = default_start_date
                end_date = default_end_date
            
            copied_count = 0
            for module in selected_modules:
                if Module.objects.filter(file_name=module.file_name, subject=target_subject).exists():
                    continue

                # Always use the calculated dates (either from override or defaults)
                final_start_date = start_date
                final_end_date = end_date
                final_term = current_term if current_term else module.term

                new_module = Module.objects.create(
                    file_name=module.file_name,
                    file=module.file,
                    subject=target_subject,
                    url=module.url,
                    iframe_code=module.iframe_code,
                    description=module.description,
                    allow_download=module.allow_download,
                    start_date=final_start_date,
                    end_date=final_end_date,
                    term=final_term
                )

                new_module.save()
                copied_count += 1

            messages.success(request, f'Successfully copied {copied_count} lessons from {source_subject.subject_name} to {target_subject.subject_name}!')
            return redirect('material-list', id=target_subject_id)
    else:
        form = SubjectToSubjectCopyForm(target_subject=target_subject, user=request.user)

    # Get current semester and calculate default dates for display
    current_semester = Semester.current()
    current_term = Term.objects.filter(semester=current_semester).first() if current_semester else None
    available_terms = Term.objects.filter(semester=current_semester) if current_semester else Term.objects.none()
    start_date = timezone.localtime(timezone.now())
    end_date = start_date + timedelta(days=7)

    return render(request, 'module/import-material-from-subject.html', {
        'form': form,
        'target_subject': target_subject,
        'subject': target_subject,
        'current_term': current_term,
        'available_terms': available_terms,
        'default_start_date': start_date,
        'default_end_date': end_date,
    })


@login_required
def copy_lessons_from_subject_cm(request, target_subject_id):
    """Classroom-mode (projector) variant of copy_lessons_from_subject — renders the CM shell and redirects to classroom_mode on success."""
    target_subject = get_object_or_404(Subject, id=target_subject_id)

    if not (request.user == target_subject.assign_teacher or request.user.is_admin):
        messages.error(request, "You don't have permission to copy lessons to this subject.")
        return redirect('classroom_mode', pk=target_subject_id)

    if request.method == 'POST':
        form = SubjectToSubjectCopyForm(request.POST, target_subject=target_subject, user=request.user)

        if form.is_valid():
            source_subject = form.cleaned_data['source_subject']
            selected_modules = form.cleaned_data['selected_modules']

            if not selected_modules:
                messages.error(request, 'No lessons were selected for copying. Please select at least one lesson.')
                return redirect('copy-materials-from-subject-cm', target_subject_id=target_subject_id)

            start_date_str = request.POST.get('start_date')
            end_date_str = request.POST.get('end_date')
            use_override = request.POST.get('use_override_dates') == 'on'
            term_id = request.POST.get('term')

            current_semester = Semester.current()

            if term_id:
                try:
                    current_term = Term.objects.get(id=term_id, semester=current_semester)
                except Term.DoesNotExist:
                    current_term = Term.objects.filter(semester=current_semester).first()
            else:
                current_term = Term.objects.filter(semester=current_semester).first()

            default_start_date = timezone.localtime(timezone.now())
            default_end_date = default_start_date + timedelta(days=7)

            if use_override and start_date_str and end_date_str:
                try:
                    start_date = datetime.fromisoformat(start_date_str)
                    end_date = datetime.fromisoformat(end_date_str)
                    if timezone.is_naive(start_date):
                        start_date = timezone.make_aware(start_date)
                    if timezone.is_naive(end_date):
                        end_date = timezone.make_aware(end_date)
                except (ValueError, TypeError):
                    start_date = default_start_date
                    end_date = default_end_date
            else:
                start_date = default_start_date
                end_date = default_end_date

            copied_count = 0
            for module in selected_modules:
                if Module.objects.filter(file_name=module.file_name, subject=target_subject).exists():
                    continue

                final_term = current_term if current_term else module.term

                new_module = Module.objects.create(
                    file_name=module.file_name,
                    file=module.file,
                    subject=target_subject,
                    url=module.url,
                    iframe_code=module.iframe_code,
                    description=module.description,
                    allow_download=module.allow_download,
                    start_date=start_date,
                    end_date=end_date,
                    term=final_term,
                )
                new_module.save()
                copied_count += 1

            messages.success(request, f'Successfully copied {copied_count} lessons from {source_subject.subject_name} to {target_subject.subject_name}!')
            return redirect('classroom_mode', pk=target_subject_id)
    else:
        form = SubjectToSubjectCopyForm(target_subject=target_subject, user=request.user)

    current_semester = Semester.current()
    current_term = Term.objects.filter(semester=current_semester).first() if current_semester else None
    available_terms = Term.objects.filter(semester=current_semester) if current_semester else Term.objects.none()
    start_date = timezone.localtime(timezone.now())
    end_date = start_date + timedelta(days=7)

    return render(request, 'module/import-material-from-subject-cm.html', {
        'form': form,
        'target_subject': target_subject,
        'subject': target_subject,
        'current_term': current_term,
        'available_terms': available_terms,
        'default_start_date': start_date,
        'default_end_date': end_date,
    })


@login_required
def get_subject_modules(request, subject_id):
    """Get modules from a subject for copy functionality"""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        subject = get_object_or_404(Subject, id=subject_id)
        current_semester = Semester.current()
        
        # Get ALL modules from this subject (including current semester)
        # This allows copying from other subjects' current semester modules
        modules = Module.objects.filter(
            subject=subject,
            term__isnull=False
        ).order_by('-term__semester__start_date', 'term__term_name')
        
        # Group by semester and term
        modules_by_semester = {}
        for module in modules:
            semester = module.term.semester
            term = module.term
            
            semester_key = f"{semester.id}|{semester.semester_name}"
            term_key = f"{term.id}|{term.term_name}"
            
            if semester_key not in modules_by_semester:
                modules_by_semester[semester_key] = {}
            if term_key not in modules_by_semester[semester_key]:
                modules_by_semester[semester_key][term_key] = []
            
            module_data = {
                'id': module.id,
                'file_name': module.file_name,
                'start_date': module.start_date.isoformat() if module.start_date else None,
                'end_date': module.end_date.isoformat() if module.end_date else None,
                'term': module.term.term_name if module.term else None,
                'description': module.description or ''
            }
            modules_by_semester[semester_key][term_key].append(module_data)
        
        return JsonResponse({'modules_by_semester': modules_by_semester})

    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def check_subject_lesson_exists(request, target_subject_id):
    if request.method == 'GET' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        lesson_id = request.GET.get('lesson_id')
        target_subject = get_object_or_404(Subject, id=target_subject_id)

        module = get_object_or_404(Module, id=lesson_id)

        exists = Module.objects.filter(
            file_name=module.file_name,
            subject=target_subject
        ).exists()

        return JsonResponse({'exists': exists})

    return JsonResponse({'error': 'Invalid request'}, status=400)
