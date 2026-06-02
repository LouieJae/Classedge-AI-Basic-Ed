from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from activity.models import Rubrics
from activity.forms import RubricsForm
from subject.models import Subject
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from course.models import Semester
from django.utils import timezone
from django.db.models import Q

from gradebookcomponent.services.access import can_audit_all_gradebooks


@login_required
@permission_required('activity.view_rubrics', raise_exception=True)
def rubric_list(request):
    user = request.user
    # Get current semester (based on date range)

    today = timezone.now().date()
    current_semester = Semester.objects.filter(
        start_date__lte=today,
        end_date__gte=today
    ).first()

    # Non-teachers (registrar / admin / program head / dean / etc.) see every
    # subject's rubrics. Teachers stay scoped to subjects they teach or
    # collaborate on.
    is_teacher = getattr(user, 'role_name', None) == 'teacher'

    if not is_teacher:
        user_subjects = Subject.objects.all()
        if current_semester:
            user_subjects = user_subjects.filter(
                subjectenrollment__semester=current_semester
            )
        user_subjects = user_subjects.distinct()
    elif current_semester:
        user_subjects = Subject.objects.filter(
            subjectenrollment__semester=current_semester
        ).filter(
            Q(assign_teacher=user) | Q(collaborators=user)
        ).distinct()
    else:
        user_subjects = Subject.objects.filter(
            Q(assign_teacher=user) | Q(collaborators=user)
        ).distinct()

    # Get all rubrics for the resolved subject set
    rubrics = Rubrics.objects.filter(subject__in=user_subjects).select_related('subject').order_by('subject__subject_name', 'rubric_name')
    
    return render(request, 'rubrics/rubric-list.html', {'rubrics': rubrics})

@login_required
@permission_required('activity.add_rubrics', raise_exception=True)
def create_rubric(request):
    user = request.user
    
    if request.method == 'POST':
        form = RubricsForm(request.POST, user=user)
        if form.is_valid():
            rubric = form.save(commit=False)
            rubric.teacher = request.user
            rubric.save()
            messages.success(request, 'Rubric created successfully.')
            return redirect('rubric-list')
    else:
        form = RubricsForm(user=user)
    return render(request, 'rubrics/create-rubric.html', {'form': form})


@login_required
@permission_required('activity.change_rubrics', raise_exception=True)
def update_rubric(request, rubric_id):
    rubric = get_object_or_404(Rubrics, id=rubric_id)
    user = request.user
    
    # Check if user has access to this rubric's subject (teacher or collaborator)
    if rubric.subject:
        if rubric.subject.assign_teacher != user and user not in rubric.subject.collaborators.all():
            messages.error(request, 'You do not have permission to update this rubric.')
            return redirect('rubric-list')
    
    if request.method == 'POST':
        form = RubricsForm(request.POST, instance=rubric, user=user)
        if form.is_valid():
            rubric = form.save(commit=False)
            rubric.teacher = request.user
            rubric.save()
            messages.success(request, 'Rubric updated successfully.')
            return redirect('rubric-list')
    else:
        form = RubricsForm(instance=rubric, user=user)
    return render(request, 'rubrics/update-rubric.html', {'rubric': rubric, 'form': form})

@login_required
@permission_required('activity.delete_rubrics', raise_exception=True)
def delete_rubric(request, rubric_id):
    rubric = get_object_or_404(Rubrics, id=rubric_id)
    user = request.user
    
    # Check if user has access to this rubric's subject (teacher or collaborator)
    if rubric.subject:
        if rubric.subject.assign_teacher != user and user not in rubric.subject.collaborators.all():
            messages.error(request, 'You do not have permission to delete this rubric.')
            return redirect('rubric-list')
    
    rubric.delete()
    messages.success(request, 'Rubric deleted successfully.')
    return redirect('rubric-list')
