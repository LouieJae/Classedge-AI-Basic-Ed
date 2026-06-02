from django.shortcuts import render, redirect, get_object_or_404
from course.models import Semester
from subject.models import Subject
from activity.models import Activity
from django.views import View
from django.utils import timezone
from course.forms import *
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from course.utils import copy_activities_from_previous_semester
from django.utils.dateformat import DateFormat
from datetime import datetime
from django.db.models import ProtectedError
from django.http import JsonResponse
from collections import defaultdict
from accounts.models import Profile
from django.utils.decorators import method_decorator

# Display semester list
@login_required
@permission_required('course.view_semester', raise_exception=True)
def semester_list(request):
    """[Classedge LMS] Themed semester list using the reusable list-table shell."""
    from accounts.utils import get_pagination_context, paginate_queryset, search_queryset

    search_query = request.GET.get('search', '').strip()
    qs = Semester.objects.all().order_by('-create_at')
    qs = search_queryset(qs, search_query, ['semester_name'])
    page_obj, _ = paginate_queryset(qs, request, items_per_page=10)

    context = {
        'search_query': search_query,
        'form': semesterForm(),
        'title': 'Semester Catalog',
        'icon': 'fa-calendar-days',
        'search_placeholder': 'Search semesters by name...',
        'empty_icon': 'fa-calendar-days',
        'empty_label': 'semesters',
        'columns': [
            {'label': '#', 'width': '60px', 'type': 'index'},
            {'label': 'Semester', 'type': 'name', 'name_attr': 'semester_name'},
            {'label': 'Start', 'type': 'date', 'attr': 'start_date'},
            {'label': 'End', 'type': 'date', 'attr': 'end_date'},
            {'label': 'Status', 'type': 'status', 'attr': 'end-semester',
             'map': {True: 'muted', False: 'success'}},
            {'label': 'Action', 'align': 'right', 'type': 'actions', 'items': [
                {'label': 'Update', 'icon': 'fa-edit',
                 'url_name': 'update-semester', 'url_arg_attr': 'id'},
                {'divider': True},
                {'label': 'End Semester', 'icon': 'fa-power-off',
                 'form_post': True, 'url_name': 'end-semester', 'url_arg_attr': 'id',
                 'confirm': 'End this semester now? This sets the end date to today.'},
                {'label': 'Delete', 'icon': 'fa-trash', 'danger': True,
                 'form_post': True, 'url_name': 'delete-semester', 'url_arg_attr': 'id',
                 'confirm': 'Delete this semester? Linked terms and enrollments must be removed first.'},
            ]},
        ],
    }
    context.update(get_pagination_context(page_obj, request))
    if request.GET.get('partial') == '1':
        return render(request, 'includes/_list_table.html', context)
    return render(request, 'course/semester/semester-list.html', context)


# Create Semester
@login_required
@permission_required('course.add_semester', raise_exception=True)
def create_semester(request):
    unavailable_dates = Semester.objects.values_list('start_date', 'end_date')
    unavailable_dates_formatted = [
        (DateFormat(start).format('Y-m-d'), DateFormat(end).format('Y-m-d')) 
        for start, end in unavailable_dates
    ]

    errors = [] 

    if request.method == 'POST':
        form = semesterForm(request.POST)

        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        semester_name = request.POST.get('semester_name')

        if not start_date or not end_date:
            errors.append("Both start and end dates are required.")
        else:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                errors.append("Invalid date format. Please enter dates in 'YYYY-MM-DD' format.")

            if start_date and end_date:
                if start_date >= end_date:
                    errors.append("End date must be after the start date.")

                start_year = start_date.year
                end_year = end_date.year

                if start_year != end_year:
                    errors.append("Start and end dates must be within the same year.")

                overlapping_semesters = Semester.objects.filter(
                    start_date__year=start_year,  # Filter by year from start_date
                    start_date__lte=end_date,  
                    end_date__gte=start_date   
                )

                if overlapping_semesters.exists():
                    errors.append("The selected dates overlap with an existing semester.")

        if not errors:
            # Check for duplicate semesters with the same name and year
            existing_semester = Semester.objects.filter(
                semester_name=semester_name,
                start_date__year=start_year  # Filter by year from start_date
            ).exists()

            if existing_semester:
                errors.append(f"A semester with the name '{semester_name}' already exists for the year {start_year}.")

        if not errors and form.is_valid():
            form.save()
            messages.success(request, 'Semester created successfully!')
            return redirect('semester-list')
        else:
            if errors:
                for error in errors:
                    messages.error(request, error)
            else:
                messages.error(request, 'There was an error creating the semester. Please try again.')

            return redirect('semester-list')  
    else:
        form = semesterForm()

    return render(request, 'course/semester/create-semester.html', {
        'form': form,
        'disabled_dates': unavailable_dates_formatted 
    })


# Update Semester
@login_required
@permission_required('course.change_semester', raise_exception=True)
def update_semester(request, pk):
    semester = get_object_or_404(Semester, pk=pk)

    # Fetch unavailable date ranges excluding the current semester being updated
    unavailable_dates = Semester.objects.exclude(pk=pk).values_list('start_date', 'end_date')
    unavailable_dates_formatted = [
        (DateFormat(start).format('Y-m-d'), DateFormat(end).format('Y-m-d')) 
        for start, end in unavailable_dates
    ]

    errors = []
    if request.method == 'POST':
        form = semesterForm(request.POST, instance=semester)

        # Extract start_date and end_date directly from POST data
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        semester_name = request.POST.get('semester_name')

        if not start_date or not end_date:
            errors.append("Both start and end dates are required.")
        else:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                errors.append("Invalid date format. Please enter dates in 'YYYY-MM-DD' format.")

            if start_date and end_date:
                if start_date >= end_date:
                    errors.append("End date must be after the start date.")

                # Check for overlapping semesters
                overlapping_semesters = Semester.objects.filter(
                    Q(start_date__lte=end_date, end_date__gte=start_date) |
                    Q(start_date__gte=start_date, end_date__lte=end_date)
                ).exclude(pk=semester.pk)

                if overlapping_semesters.exists():
                    errors.append("The selected dates overlap with an existing semester.")

        # Check if semester_name already exists in the same period
        if not errors:
            existing_semester = Semester.objects.filter(
                semester_name=semester_name
            ).exclude(pk=semester.pk).exists()

            if existing_semester:
                errors.append(f"A semester with the name '{semester_name}' already exists.")

        if not errors and form.is_valid():
            form.save()
            messages.success(request, 'Semester updated successfully!')
            return redirect('semester-list')
        else:
            if errors:
                for error in errors:
                    messages.error(request, error)
            else:
                messages.error(request, 'There was an error updating the semester. Please try again.')

            return redirect('semester-list')

    else:
        form = semesterForm(instance=semester)

    return render(request, 'course/semester/update-semester.html', {
        'form': form,
        'semester': semester,
        'disabled_dates': unavailable_dates_formatted  
    })

@login_required
@permission_required('course.delete_semester', raise_exception=True)
def delete_semester(request, pk):
    semester = get_object_or_404(Semester, pk=pk)
    try:
        semester.delete()
        messages.success(request, 'Semester deleted successfully!')
    except ProtectedError as e:
        messages.error(request, f"Cannot delete this semester because it is referenced by other records.")

    return redirect('semester-list')

@login_required
def end_semester(request, pk):
    semester = get_object_or_404(Semester, pk=pk)
    semester.end_semester = True
    semester.save()
    messages.success(request, 'Semester ended successfully!')
    return redirect('semester-list') 