from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from gradebookcomponent.forms import TermGradeBookComponentsForm
from gradebookcomponent.models import TermGradeBookComponents
from course.models import Semester


# View TermGradeBook List
@login_required
@permission_required('gradebookcomponent.view_termgradebookcomponents', raise_exception=True)
def term_book(request):
    # Get the current date
    current_date = timezone.now().date()
    current_semester = Semester.objects.filter(start_date__lte=current_date, end_date__gte=current_date).first()
    semesters = Semester.objects.all()

    view_all_terms = request.GET.get('view_all_terms')

    if request.user.is_teacher:
        if view_all_terms:
            termbook = TermGradeBookComponents.objects.filter(
                subjects__assign_teacher=request.user
            ).distinct()
        else:
            termbook = TermGradeBookComponents.objects.filter(
                subjects__assign_teacher=request.user,
                term__semester=current_semester,
            ).distinct()
    else:
        if view_all_terms:
            termbook = TermGradeBookComponents.objects.all().distinct()
        else:
            termbook = TermGradeBookComponents.objects.filter(
                term__semester=current_semester
            ).distinct()

    return render(request, 'termbook/term_book.html', {
        'termbooks': termbook,
        'semesters': semesters,
        'current_semester': current_semester,
        'view_all_terms': view_all_terms,
    })


# create TermGradeBook
@login_required
@permission_required('gradebookcomponent.add_termgradebookcomponents', raise_exception=True)
def create_term_book(request):
    if request.method == 'POST':
        form = TermGradeBookComponentsForm(request.POST, user=request.user)
        if form.is_valid():
            term = form.cleaned_data.get('term')
            subjects = form.cleaned_data.get('subjects')
            percentage = request.POST.get('percentage')

            try:
                # Validate the percentage field
                if not percentage:
                    raise ValueError('Percentage cannot be blank.')

                percentage_value = Decimal(percentage)
                if percentage_value < 0:
                    raise ValueError('Percentage cannot be negative.')

                current_semester = term.semester
                if not current_semester:
                    raise ValueError("No active semester found for the selected term.")

                for subject in subjects:
                    existing_components = TermGradeBookComponents.objects.filter(
                        term__semester=current_semester,
                        subjects=subject,
                    ).exclude(term=term)

                    existing_percentage = existing_components.aggregate(
                        total_percentage=Sum('percentage')
                    )['total_percentage'] or Decimal(0)

                    total_percentage = existing_percentage + percentage_value

                    if total_percentage > 100:
                        raise ValueError(
                            f"Adding {percentage_value}% for '{subject.subject_name}' in '{term.term_name}' would bring the total across all terms in '{current_semester.semester_name}' to {total_percentage}% (max 100%). Existing terms already total {existing_percentage}%."
                        )

                for subject in subjects:
                    if TermGradeBookComponents.objects.filter(term=term, term__semester=current_semester, subjects=subject).exists():
                        messages.error(request, f'The course "{subject}" already exists for the term "{term}" in "{current_semester}". Please choose another course.')
                        return redirect('grade-book')

                instance = form.save(commit=False)
                instance.teacher = request.user
                instance.save()
                form.save_m2m()  # Save ManyToMany relationships

                messages.success(request, 'Termbook created successfully!')
                return redirect('grade-book')

            except ValueError as e:
                messages.error(request, str(e))
                return redirect('grade-book')

        else:
            messages.error(request, 'An error occurred while creating the termbook!')
            return redirect('grade-book')

    else:
        form = TermGradeBookComponentsForm(user=request.user)

    return render(request, 'termbook/create_term_book.html', {'form': form})


# update TermBook
@login_required
@permission_required('gradebookcomponent.change_termgradebookcomponents', raise_exception=True)
def update_term_book(request, id):
    termbook = get_object_or_404(TermGradeBookComponents, id=id)

    if request.method == 'POST':
        form = TermGradeBookComponentsForm(request.POST, instance=termbook, user=request.user)
        if form.is_valid():
            term = form.cleaned_data.get('term')
            subjects = form.cleaned_data.get('subjects')
            percentage = request.POST.get('percentage')

            try:
                # Validate the percentage field
                if not percentage:
                    raise ValueError('Percentage cannot be blank.')

                percentage_value = Decimal(percentage)
                if percentage_value < 0:
                    raise ValueError('Percentage cannot be negative.')

                current_semester = term.semester  # Get the semester from the term
                if not current_semester:
                    raise ValueError("No active semester found.")

                for subject in subjects:
                    existing_components = TermGradeBookComponents.objects.filter(
                        term__semester=current_semester,
                        subjects=subject,
                    ).exclude(id=termbook.id).exclude(term=term)

                    existing_percentage = existing_components.aggregate(
                        total_percentage=Sum('percentage')
                    )['total_percentage'] or Decimal(0)

                    total_percentage = existing_percentage + percentage_value
                    if total_percentage > 100:
                        raise ValueError(
                            f"Updating to {percentage_value}% for '{subject.subject_name}' in '{term.term_name}' would bring the total across all terms in '{current_semester.semester_name}' to {total_percentage}% (max 100%). Existing other terms total {existing_percentage}%."
                        )

                for subject in subjects:
                    if TermGradeBookComponents.objects.filter(term=term, term__semester=current_semester, subjects=subject).exclude(id=termbook.id).exists():
                        messages.error(request, f'The course "{subject}" already exists for the term "{term}" in "{current_semester}". Please choose another course or modify the existing one.')
                        return redirect('update_term_book', id=termbook.id)

                # Save the updated termbook component
                instance = form.save(commit=False)
                instance.teacher = request.user
                instance.save()
                form.save_m2m()  # Save ManyToMany relationships

                messages.success(request, 'Termbook updated successfully!')
                return redirect('grade-book')

            except ValueError as e:
                # Handle percentage validation errors
                messages.error(request, str(e))
                return redirect('update_term_book', id=termbook.id)

        else:
            messages.error(request, 'An error occurred while updating the termbook!')
            return redirect('grade-book')
    else:
        form = TermGradeBookComponentsForm(instance=termbook, user=request.user)

    return render(request, 'termbook/update_term_book.html', {'form': form, 'termbook': termbook})


# view Termbook
@login_required
@permission_required('gradebookcomponent.view_termgradebookcomponents', raise_exception=True)
def view_term_book(request, id=None):
    semesters = Semester.objects.all()
    selected_semester = request.GET.get('semester')

    if selected_semester:
        terms = TermGradeBookComponents.objects.filter(term__semester_id=selected_semester)
    else:
        terms = TermGradeBookComponents.objects.all()

    # Get specific termbook if an id is provided
    termbook = None
    if id:
        termbook = get_object_or_404(TermGradeBookComponents, id=id)

    context = {
        'semesters': semesters,
        'selected_semester': selected_semester,
        'terms': terms,
        'termbook': termbook,  # Pass the specific termbook if present
    }
    return render(request, 'termbook/view_term_book.html', context)


# delete TermBook
@login_required
@permission_required('gradebookcomponent.delete_termgradebookcomponents', raise_exception=True)
def delete_term_book(request, id):
    termbook = get_object_or_404(TermGradeBookComponents, id=id)
    termbook.delete()
    messages.success(request, 'Termbook deleted successfully!')
    return redirect('term-book')
