from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Q
from subject.models import Subject
from activity.models import Activity, ActivityQuestion, RetakeRecordDetail
from activity.utils.authorization import check_subject_access
from course.models import SubjectEnrollment, Semester
from ..models.module import Module
from ..models.student_progress import StudentProgress


@login_required
@permission_required('module.view_module', raise_exception=True)
def view_module(request, pk):
    module = get_object_or_404(Module, pk=pk)
    student = request.user

    # Verify user has profile and role
    if not hasattr(student, 'profile') or not student.profile or not student.profile.role:
        messages.error(request, "Your account is not properly configured. Please contact an administrator.")
        return redirect('SubjectList')
    
    # Ensure user has access to this module's subject
    has_access, redirect_response = check_subject_access(request, module.subject)
    if not has_access:
        return redirect_response

    # Check if module has user-specific visibility restrictions (students only)
    user_role = student.role_name
    is_student_role = user_role == 'student'
    if is_student_role and module.display_lesson_for_selected_users.exists():
        if student not in module.display_lesson_for_selected_users.all():
            messages.error(request, "This lesson is not available to you.")
            return redirect('material-list', id=module.subject.id)

    progress, _ = StudentProgress.objects.get_or_create(
        student=student,
        module=module,
        defaults={'progress': 0, 'last_page': 1}
    )
    progress.save()

    context = {
        'module': module,
        'progress': progress.progress,
        'last_page': progress.last_page,
    }

    if module.file:
        name_lower = module.file.name.lower()
        if name_lower.endswith('.pdf'):
            context['is_pdf'] = True
        elif name_lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            context['is_image'] = True
            # Single-view content has no paging; viewing it is completing it.
            progress.progress = 100
            progress.completed = True
            progress.save()
        elif name_lower.endswith(('.mp4', '.avi', '.mov', '.mkv')):
            context['is_video'] = True
        elif module.onedrive_embed_url:
            # Any file with a saved OneDrive embed URL renders inline,
            # regardless of extension (covers .ppt/.pptx/.doc/.docx/.xls/.xlsx
            # and any future additions).
            print(f"[view_module] using onedrive_embed_url for module={module.pk}: {module.onedrive_embed_url}")
            context['is_office_embed'] = True
            context['office_embed_url'] = module.onedrive_embed_url
            progress.progress = 100
            progress.completed = True
            progress.save()
        else:
            print(f"[view_module] module={module.pk} has no embed_url and ext={name_lower!r} — falling back to is_unknown")
            context['is_unknown'] = True
            # Unsupported content has nothing for the student to interact with;
            # don't gate the quest map on a file we can't even render.
            progress.progress = 100
            progress.completed = True
            progress.save()
    elif module.url:
        if 'youtube.com' in module.url:
            embed_url = module.url.replace("watch?v=", "embed/")
            context['is_youtube'] = True
            context['embed_url'] = embed_url
        elif 'vimeo.com' in module.url:
            vimeo_id = module.url.split('/')[-1]
            embed_url = f"https://player.vimeo.com/video/{vimeo_id}"
            context['is_vimeo'] = True
            context['embed_url'] = embed_url
        elif "sway.cloud.microsoft" in module.url:
            context['is_sway'] = True
            context['sway_embed_url'] = module.url
        elif module.url.endswith(('.mp4', '.webm', '.ogg')):
            context['is_video_url'] = True
        else:
            context['is_url'] = True

        progress.progress = 100
        progress.completed = True
        progress.save()
    elif module.iframe_code:
        context['is_embed'] = True
        progress.progress = 100
        progress.completed = True
        progress.save()
    else:
        context['is_unknown'] = True
        # Empty/unsupported module — no file, no URL, no iframe to view.
        # Treat as completed so the student isn't stuck on a quest-map node
        # they can't possibly interact with.
        progress.progress = 100
        progress.completed = True
        progress.save()

    return render(request, 'module/view-material.html', context)


@login_required
@permission_required('module.view_module', raise_exception=True)
def view_subject_module(request, pk):
    module = get_object_or_404(Module, pk=pk)
    subject = module.subject

    # Ensure user has access to this module's subject
    has_access, redirect_response = check_subject_access(request, subject)
    if not has_access:
        return redirect_response

    # Check if module has user-specific visibility restrictions (students only)
    user_role = request.user.role_name
    is_student_role = user_role == 'student'
    if is_student_role and module.display_lesson_for_selected_users.exists():
        if request.user not in module.display_lesson_for_selected_users.all():
            messages.error(request, "This lesson is not available to you.")
            return redirect('material-list', id=subject.id)


    direct_exams = Activity.objects.filter(
        subject=subject,
        status=True,
        additional_modules=module,
        activity_type__name__iexact="Exam",
    )
    direct_assignment = Activity.objects.filter(
        subject=subject,
        status=True,
        additional_modules=module,
        activity_type__name__iexact="Assignment",
    )
    direct_special_activity = Activity.objects.filter(
        subject=subject,
        status=True,
        additional_modules=module,        
        activity_type__name__iexact="Special Activity",
    )
    direct_quiz = Activity.objects.filter(
        subject=subject,
        status=True,
        additional_modules=module,
        activity_type__name__iexact="Quiz",
    )

    additional_exams = Activity.objects.filter(additional_modules=module, status=True, activity_type__name__iexact="Exam")
    additional_assignment = Activity.objects.filter(additional_modules=module, status=True, activity_type__name__iexact="Assignment")
    additional_special_activity = Activity.objects.filter(additional_modules=module, status=True, activity_type__name__iexact="Special Activity")
    additional_quiz = Activity.objects.filter(additional_modules=module, status=True, activity_type__name__iexact="Quiz")
    
    exams = (direct_exams | additional_exams).distinct()
    assignment = (direct_assignment | additional_assignment).distinct()
    special_activity = (direct_special_activity | additional_special_activity).distinct()
    quiz = (direct_quiz | additional_quiz).distinct()

    activities_with_grading_needed = []
    ungraded_items_count = 0

    all_activities = Activity.objects.filter(
        Q(subject=subject) | Q(additional_modules=module),
        status=True,
    ).distinct()
    for activity in all_activities:
        questions_requiring_grading = ActivityQuestion.objects.filter(
            activity=activity,
            quiz_type__name__in=['Essay', 'Document']
        )
        ungraded_items = RetakeRecordDetail.objects.filter(
            Q(activity_question__in=questions_requiring_grading),
            Q(student_answer__isnull=False) | Q(uploaded_file__isnull=False),
            score=0
        ).exclude(student_answer__isnull=True, uploaded_file='').exclude(student_answer='', uploaded_file='')
        if ungraded_items.exists():
            activities_with_grading_needed.append((activity, ungraded_items.count()))
            ungraded_items_count += ungraded_items.count()

    activity_counts = {
        "exam_count": exams.count(),
        "assignment_count": assignment.count(),
        "special_activity_count": special_activity.count(),
        "quiz_count": quiz.count(),
    }

    context = {
        'module': module,
        'subject': subject,
        'exams': exams,
        'assignment': assignment,
        'special_activity': special_activity,
        'quiz': quiz,
        'activities_with_grading_needed': activities_with_grading_needed,
        'ungraded_items_count': ungraded_items_count,
        'activity_counts': activity_counts,
    }

    if module.file:
        name_lower = module.file.name.lower()
        if name_lower.endswith('.pdf'):
            context['is_pdf'] = True
        elif name_lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            context['is_image'] = True
        elif name_lower.endswith(('.mp4', '.avi', '.mov', '.mkv')):
            context['is_video'] = True
        elif module.onedrive_embed_url:
            context['is_office_embed'] = True
            context['office_embed_url'] = module.onedrive_embed_url
        else:
            context['is_unknown'] = True
    elif module.url:
        if 'youtube.com' in module.url:
            embed_url = module.url.replace("watch?v=", "embed/")
            context['is_youtube'] = True
            context['embed_url'] = embed_url
        elif 'vimeo.com' in module.url:
            vimeo_id = module.url.split('/')[-1]
            embed_url = f"https://player.vimeo.com/video/{vimeo_id}"
            context['is_vimeo'] = True
            context['embed_url'] = embed_url
        elif "sway.cloud.microsoft" in module.url:
            context['is_sway'] = True
            context['sway_embed_url'] = module.url
        elif module.url.endswith(('.mp4', '.webm', '.ogg')):
            context['is_video_url'] = True
        else:
            context['is_url'] = True

    return render(request, 'module/view_subject_module.html', context)


@login_required
@permission_required('module.view_module', raise_exception=True)
def material_progress_report(request, pk):
    module = get_object_or_404(Module, pk=pk)
    subject = module.subject

    # Ensure user has access to this module's subject (teachers only)
    has_access, redirect_response = check_subject_access(request, subject, require_teacher=True)
    if not has_access:
        return redirect_response

    all_progress = (
        StudentProgress.objects
        .filter(module=module, student__profile__role__name__iexact='student')
        .select_related('student', 'student__profile', 'student__profile__role')
    )

    context = {
        'module': module,
        'subject': subject,
        'all_progress': all_progress,
    }

    if module.file:
        name_lower = module.file.name.lower()
        if name_lower.endswith('.pdf'):
            context['is_pdf'] = True
        elif name_lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            context['is_image'] = True
        elif name_lower.endswith(('.mp4', '.avi', '.mov', '.mkv')):
            context['is_video'] = True
        elif module.onedrive_embed_url:
            context['is_office_embed'] = True
            context['office_embed_url'] = module.onedrive_embed_url
        else:
            context['is_unknown'] = True
    elif module.url:
        if 'youtube.com' in module.url:
            embed_url = module.url.replace("watch?v=", "embed/")
            context['is_youtube'] = True
            context['embed_url'] = embed_url
        elif 'vimeo.com' in module.url:
            vimeo_id = module.url.split('/')[-1]
            embed_url = f"https://player.vimeo.com/video/{vimeo_id}"
            context['is_vimeo'] = True
            context['embed_url'] = embed_url
        elif "sway.cloud.microsoft" in module.url:
            context['is_sway'] = True
            context['sway_embed_url'] = module.url
        elif module.url.endswith(('.mp4', '.webm', '.ogg')):
            context['is_video_url'] = True
        else:
            context['is_url'] = True
    return render(request, 'module/material-progress-report.html', context)


@login_required
@permission_required('module.view_module', raise_exception=True)
def view_module_cm(request, pk):
    module = get_object_or_404(Module, pk=pk)
    student = request.user
    subject_id = module.subject.id
    subject = get_object_or_404(Subject, id=subject_id)

    # Ensure user has access to this module's subject
    has_access, redirect_response = check_subject_access(request, subject)
    if not has_access:
        return redirect_response

    # Check if module has user-specific visibility restrictions (students only)
    user_role = student.role_name
    is_student_role = user_role == 'student'
    if is_student_role and module.display_lesson_for_selected_users.exists():
        if student not in module.display_lesson_for_selected_users.all():
            messages.error(request, "This lesson is not available to you.")
            return redirect('classroom_mode', pk=subject.id)

    progress, _ = StudentProgress.objects.get_or_create(
        student=student,
        module=module,
        defaults={'progress': 0, 'last_page': 1}
    )
    progress.save()

    context = {
        'module': module,
        'progress': progress.progress,
        'last_page': progress.last_page,
        'subject': subject,
    }

    if module.file:
        name_lower = module.file.name.lower()
        if name_lower.endswith('.pdf'):
            context['is_pdf'] = True
        elif name_lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            context['is_image'] = True
            # Single-view content has no paging; viewing it is completing it.
            progress.progress = 100
            progress.completed = True
            progress.save()
        elif name_lower.endswith(('.mp4', '.avi', '.mov', '.mkv')):
            context['is_video'] = True
        elif module.onedrive_embed_url:
            # Any file with a saved OneDrive embed URL renders inline,
            # regardless of extension (covers .ppt/.pptx/.doc/.docx/.xls/.xlsx
            # and any future additions).
            print(f"[view_module] using onedrive_embed_url for module={module.pk}: {module.onedrive_embed_url}")
            context['is_office_embed'] = True
            context['office_embed_url'] = module.onedrive_embed_url
            progress.progress = 100
            progress.completed = True
            progress.save()
        else:
            print(f"[view_module] module={module.pk} has no embed_url and ext={name_lower!r} — falling back to is_unknown")
            context['is_unknown'] = True
            # Unsupported content has nothing for the student to interact with;
            # don't gate the quest map on a file we can't even render.
            progress.progress = 100
            progress.completed = True
            progress.save()
    elif module.url:
        if 'youtube.com' in module.url:
            embed_url = module.url.replace("watch?v=", "embed/")
            context['is_youtube'] = True
            context['embed_url'] = embed_url
        elif 'vimeo.com' in module.url:
            vimeo_id = module.url.split('/')[-1]
            embed_url = f"https://player.vimeo.com/video/{vimeo_id}"
            context['is_vimeo'] = True
            context['embed_url'] = embed_url
        elif module.url.endswith(('.mp4', '.webm', '.ogg')):
            context['is_video_url'] = True
        else:
            context['is_url'] = True

        progress.progress = 100
        progress.completed = True
        progress.save()
    else:
        context['is_unknown'] = True
        # Empty/unsupported module — no file, no URL to view. Treat as
        # completed so the student isn't stuck on a quest-map node they
        # can't possibly interact with.
        progress.progress = 100
        progress.completed = True
        progress.save()

    return render(request, 'module/view-material-cm.html', context)


@login_required
@permission_required('module.view_module', raise_exception=True)
def download_module(request, module_id):
    module = get_object_or_404(Module, pk=module_id)

    # Ensure user has access to this module's subject
    has_access, redirect_response = check_subject_access(request, module.subject)
    if not has_access:
        return redirect_response

    if not module.file:
        return HttpResponse("No file available for download.", status=404)

    file_path = module.file.path
    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type="application/octet-stream")
        response['Content-Disposition'] = f'attachment; filename="{module.file_name}"'
        return response
