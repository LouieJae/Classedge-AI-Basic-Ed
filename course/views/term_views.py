from django.shortcuts import render, redirect, get_object_or_404
from course.models import  Semester, Term
from subject.models import Subject
from activity.models import Activity ,StudentQuestion
from accounts.models import CustomUser
from django.utils import timezone
from course.forms import termForm
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from datetime import date, datetime
from django.http import JsonResponse
from rest_framework.filters import SearchFilter
from course.serializers import TermSerializer
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from datetime import datetime
from rest_framework.permissions import DjangoModelPermissions

class TermViewSet(ModelViewSet):
    serializer_class = TermSerializer
    filter_backends = [SearchFilter]
    search_fields = ['term_name', 'semester']
    permission_classes = [IsAuthenticated , DjangoModelPermissions]
    
    
    def get_queryset(self):
        today = date.today()
        current_semester = Semester.objects.filter(start_date__lte=today, end_date__gte=today).first()
        
        if current_semester:
            return Term.objects.filter(semester=current_semester)
        
        return Term.objects.all()

# Display term list
@login_required
@permission_required('course.view_term', raise_exception=True)
def term_list(request):
    """[Classedge LMS] Themed term list using the reusable list-table shell."""
    from accounts.utils import get_pagination_context, paginate_queryset, search_queryset

    current_date = timezone.now().date()
    current_semester = Semester.objects.filter(
        start_date__lte=current_date, end_date__gte=current_date
    ).first()

    search_query = request.GET.get('search', '').strip()
    view_all_terms = request.GET.get('view_all_terms') in {'1', 'true', 'on'}

    qs = Term.objects.select_related('semester').all() if view_all_terms \
        else Term.objects.select_related('semester').filter(semester=current_semester)
    qs = qs.order_by('-semester__start_date', 'start_date')
    qs = search_queryset(qs, search_query, ['term_name', 'semester__semester_name'])
    page_obj, _ = paginate_queryset(qs, request, items_per_page=10)

    context = {
        'search_query': search_query,
        'form': termForm(),
        'view_all_terms': view_all_terms,
        'title': 'Term Catalog',
        'icon': 'fa-calendar-week',
        'extra_filters_template': 'course/term/_term_filters.html',
        'search_placeholder': 'Search terms by name or semester...',
        'empty_icon': 'fa-calendar-week',
        'empty_label': 'terms',
        'columns': [
            {'label': '#', 'width': '60px', 'type': 'index'},
            {'label': 'Term', 'type': 'name', 'name_attr': 'term_name'},
            {'label': 'Semester', 'type': 'pill', 'attr': 'semester.semester_name'},
            {'label': 'Start', 'type': 'date', 'attr': 'start_date'},
            {'label': 'End', 'type': 'date', 'attr': 'end_date'},
            {'label': 'Action', 'align': 'right', 'type': 'actions', 'items': [
                {'label': 'Update', 'icon': 'fa-edit',
                 'url_name': 'update-term', 'url_arg_attr': 'id'},
                {'divider': True},
                {'label': 'Delete', 'icon': 'fa-trash', 'danger': True,
                 'form_post': True, 'url_name': 'delete-term', 'url_arg_attr': 'id',
                 'confirm': 'Delete this term? Linked activities and grades may be affected.'},
            ]},
        ],
    }
    context.update(get_pagination_context(page_obj, request))
    if request.GET.get('partial') == '1':
        return render(request, 'includes/_list_table.html', context)
    return render(request, 'course/term/term-list.html', context)

# Create Semester
@login_required
@permission_required('course.add_term', raise_exception=True)
def create_term(request):
    if request.method == 'POST':
        form = termForm(request.POST)

        semester = request.POST.get('semester')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        errors = []

        try:
            semester = Semester.objects.get(id=semester)
        except Semester.DoesNotExist:
            errors.append("Selected semester does not exist.")
            semester = None

        # Check if start_date or end_date is missing
        if not start_date or not end_date:
            errors.append("Both start and end dates are required.")
        else:
            # Convert the date strings to proper date objects for comparison
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                errors.append("Invalid date format. Please enter dates in 'YYYY-MM-DD' format.")

            if start_date and end_date:
                # Check if the start date is after or equal to the end date
                if start_date >= end_date:
                    errors.append("End date must be after the start date.")

                if semester:
                    # Ensure Term dates are within Semester dates
                    if start_date < semester.start_date:
                        errors.append(f"Term start date ({start_date}) cannot be before Semester start date ({semester.start_date}).")
                    if end_date > semester.end_date:
                        errors.append(f"Term end date ({end_date}) cannot be after Semester end date ({semester.end_date}).")

                # Check for overlapping semesters within the same school year
                overlapping_terms = Term.objects.filter(
                    semester=semester
                ).filter(
                    start_date__lte=end_date,  # The new term’s start date must be strictly after any existing term's end date
                    end_date__gte=start_date   # The new term’s end date must be strictly before any existing term's start date
                )

                if overlapping_terms.exists():
                    errors.append("The selected dates overlap with an existing term.")
                    
        if not errors and form.is_valid():
            term = form.save(commit=False)
            term.created_by = request.user  
            term.save()
            messages.success(request, 'Term created successfully!')
            return redirect('term-list')
        else:
            if errors:
                for error in errors:
                    messages.error(request, error)
            else:
                messages.error(request, 'There was an error creating the term. Please try again.')
            return redirect('term-list')
            
    else:
        form = termForm()
    return render(request, 'course/term/create-term.html', {
        'form': form,
    })

# Update Semester
@login_required
@permission_required('course.change_term', raise_exception=True)
def update_term(request, pk):
    term = get_object_or_404(Term, pk=pk)

    if request.method == 'POST':
        form = termForm(request.POST, instance=term)

        semester = request.POST.get('semester')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        errors = []

        try:
            semester = Semester.objects.get(id=semester)
        except Semester.DoesNotExist:
            errors.append("Selected semester does not exist.")
            semester = None

        # Check if start_date or end_date is missing
        if not start_date or not end_date:
            errors.append("Both start and end dates are required.")
        else:
            # Convert the date strings to proper date objects for comparison
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                errors.append("Invalid date format. Please enter dates in 'YYYY-MM-DD' format.")

            if start_date and end_date:
                # Check if the start date is after or equal to the end date
                if start_date >= end_date:
                    errors.append("End date must be after the start date.")

                # Check for overlapping semesters within the same school year
                overlapping_semesters = Term.objects.filter(
                    semester= semester,
                    start_date__lt=end_date,  # Existing semester starts before the new semester ends
                    end_date__gt=start_date   # Existing semester ends after the new semester starts
                ).exclude(pk=term.pk)  # Exclude the current semester from the overlap check

                if overlapping_semesters.exists():
                    errors.append("The selected dates overlap with an existing term.")

        if not errors and form.is_valid():
            form.save()
            messages.success(request, 'Term updated successfully!')
            return redirect('term-list')
        else:
            if errors:
                for error in errors:
                    messages.error(request, error)
            else:
                messages.error(request, 'There was an error creating the term. Please try again.')
            return redirect('term-list')
    else:
        form = termForm(instance=term)
        
    return render(request, 'course/term/update-term.html', {
        'form': form, 
        'term': term
    })

@login_required
def delete_term(request, pk):
    term = get_object_or_404(Term, pk=pk)
    term.delete()
    messages.success(request, 'Term deleted successfully!')
    return redirect('term-list')
