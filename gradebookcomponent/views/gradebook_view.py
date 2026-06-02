from decimal import Decimal
import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.csrf import csrf_exempt
from gradebookcomponent.forms import (
    ActivityTypePercentageFormSet,
    CopyGradeBookForm,
    GradeBookComponentsForm,
)
from gradebookcomponent.models import GradeBookComponents, ActivityTypePercentage, TermGradeBookComponents
from course.models import Semester, Term, SubjectEnrollment
from subject.models import Subject
from django.utils import timezone


def _save_subactivities(component, formset):
    """Persist sub-activities from the formset. Teachers freely choose which
    activity types contribute and at what weight; the formset enforces sum=100%."""
    component.activity_type_percentages.all().delete()
    for f in formset.forms:
        if not f.cleaned_data or f.cleaned_data.get("DELETE"):
            continue
        ActivityTypePercentage.objects.create(
            gradebook_component=component,
            activity_type=f.cleaned_data["activity_type"],
            percentage=f.cleaned_data["percentage"],
        )


def _category_suggestions(user):
    """Return distinct category names the teacher (or anyone, for admins) has used,
    so the create/update form can suggest them via a <datalist>."""
    qs = GradeBookComponents.objects.values_list('gradebook_category', flat=True)
    if user and not user.is_superuser:
        qs = qs.filter(teacher=user)
    return sorted(set(c for c in qs if c))


@login_required
@permission_required('gradebookcomponent.view_gradebookcomponents', raise_exception=True)
@permission_required('gradebookcomponent.view_termgradebookcomponents', raise_exception=True)
def grade_book(request):

    success = request.GET.get('success')
    if success == 'created':
        messages.success(request, 'GradeBook Created Successfully!')
    elif success == 'updated':
        messages.success(request, 'GradeBook Updated Successfully!')

    today = timezone.now().date()
    current_semester = Semester.objects.filter(start_date__lte=today, end_date__gte=today).first()
    view_all_terms = request.GET.get('view_all_terms')
    is_teacher = request.user.is_teacher

    if current_semester:
        # Clean base queryset (no JOIN-on-enrollment so aggregates aren't inflated).
        # COIL/HALI subjects run on their own grading flow and are excluded
        # from the regular gradebook for every role.
        base_qs = (
            GradeBookComponents.objects
            .filter(term__semester=current_semester)
            .exclude(subject__is_coil=True)
            .exclude(subject__is_hali=True)
        )
        if is_teacher:
            base_qs = base_qs.filter(teacher=request.user)
        # Restrict to subjects that actually have enrollments this semester.
        enrolled_subject_ids = SubjectEnrollment.objects.filter(
            semester=current_semester
        ).values_list('subject_id', flat=True).distinct()
        base_qs = base_qs.filter(subject_id__in=enrolled_subject_ids)
    else:
        base_qs = GradeBookComponents.objects.none()

    components_qs = (
        base_qs.select_related('subject', 'term')
        .prefetch_related('activity_type_percentages__activity_type')
        .order_by('subject__subject_name', 'term__term_name', 'gradebook_category')
    )

    subject_totals = {}
    for row in base_qs.values('subject_id', 'subject__subject_name').annotate(total=Sum('percentage')):
        subject_totals[row['subject__subject_name'] or '—'] = row['total'] or Decimal(0)

    grouped_components = {}
    for component in components_qs:
        grouped_components.setdefault(component.subject, []).append(component)

    if is_teacher:
        termbook_qs = TermGradeBookComponents.objects.all().distinct() if view_all_terms else \
            TermGradeBookComponents.objects.filter(teacher=request.user, term__semester=current_semester).distinct()
    else:
        termbook_qs = TermGradeBookComponents.objects.all().distinct() if view_all_terms else \
            TermGradeBookComponents.objects.filter(term__semester=current_semester).distinct()

    grouped_termbooks = {}
    for term in termbook_qs:
        for subject in term.subjects.all():
            grouped_termbooks.setdefault(subject, []).append(term)

    context = {
        'current_semester': current_semester,
        'view_all_terms': view_all_terms,
        'grouped_termbooks': grouped_termbooks,
        'grouped_components': grouped_components,
        'subject_totals': subject_totals,
    }

    return render(request, 'gradebook/grade-book.html', context)


@login_required
@permission_required('gradebookcomponent.add_gradebookcomponents', raise_exception=True)
def create_grade_book(request):
    if request.method == 'POST':
        form = GradeBookComponentsForm(request.POST, user=request.user)
        formset = ActivityTypePercentageFormSet(request.POST, prefix='subactivities')
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                component = form.save(commit=False)
                component.teacher = request.user
                component.save()
                _save_subactivities(component, formset)
            messages.success(request, 'Gradebook created successfully!')
            return redirect('grade-book')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = GradeBookComponentsForm(user=request.user)
        formset = ActivityTypePercentageFormSet(prefix='subactivities')

    return render(request, 'gradebook/create-grade-book.html', {
        'form': form,
        'formset': formset,
        'category_suggestions': _category_suggestions(request.user),
    })


@login_required
@permission_required('gradebookcomponent.change_gradebookcomponents', raise_exception=True)
def update_grade_book(request, pk):
    component = get_object_or_404(GradeBookComponents, pk=pk)
    if request.method == 'POST':
        form = GradeBookComponentsForm(request.POST, instance=component, user=request.user)
        formset = ActivityTypePercentageFormSet(request.POST, instance=component, prefix='subactivities')
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                updated = form.save(commit=False)
                if not updated.teacher_id:
                    updated.teacher = request.user
                updated.save()
                _save_subactivities(updated, formset)
            messages.success(request, 'Gradebook updated successfully!')
            return redirect('grade-book')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = GradeBookComponentsForm(instance=component, user=request.user)
        formset = ActivityTypePercentageFormSet(instance=component, prefix='subactivities')

    return render(request, 'gradebook/update-grade-book.html', {
        'form': form,
        'formset': formset,
        'gradebook': component,
        'category_suggestions': _category_suggestions(request.user),
    })


@login_required
@permission_required('gradebookcomponent.add_gradebookcomponents', raise_exception=True)
def copy_grade_book(request):
    if request.method == 'POST':
        form = CopyGradeBookForm(request.POST, user=request.user)

        if form.is_valid():
            source_semester = form.cleaned_data['source_semester']
            term = form.cleaned_data['term']
            source_subject = form.cleaned_data['copy_from_subject']
            target_subjects = form.cleaned_data['subject']
            current_term = form.cleaned_data['current_term']

            if source_subject in target_subjects:
                messages.error(request, 'Source subject cannot be the same as target subjects.')
                return redirect('grade-book')

            components_to_copy = GradeBookComponents.objects.filter(subject=source_subject, term=term)

            if not components_to_copy.exists():
                messages.error(request, 'No gradebook components found to copy from the selected subject and term.')
                return redirect('grade-book')

            errors_found = False

            with transaction.atomic():
                for target_subject in target_subjects:
                    existing_components = GradeBookComponents.objects.filter(
                        subject=target_subject, term=current_term
                    ).values_list('gradebook_name', flat=True)

                    for component in components_to_copy:
                        if component.gradebook_name in existing_components:
                            messages.error(request, f"'{component.gradebook_name}' already exists in {target_subject}.")
                            errors_found = True
                            continue

                        new_percentage = GradeBookComponents.objects.filter(
                            subject=target_subject, term=current_term
                        ).aggregate(Sum('percentage'))['percentage__sum'] or 0

                        if new_percentage + component.percentage > 100:
                            messages.error(
                                request, f"Cannot copy '{component.gradebook_name}'; total would exceed 100% in {target_subject}."
                            )
                            errors_found = True
                            continue

                        new_component = GradeBookComponents.objects.create(
                            teacher=request.user,
                            subject=target_subject,
                            activity_type=component.activity_type,
                            gradebook_name=component.gradebook_name,
                            percentage=component.percentage,
                            term=current_term,
                            gradebook_category=component.gradebook_category,
                        )

                        # Copy ActivityTypePercentage entries
                        for atp in component.activity_type_percentages.all():
                            ActivityTypePercentage.objects.create(
                                gradebook_component=new_component,
                                activity_type=atp.activity_type,
                                percentage=atp.percentage
                            )

            if errors_found:
                return redirect('grade-book')

            messages.success(request, '✅ Gradebook (with sub-activities) copied successfully!')
            return redirect('grade-book')
        
        else:
            messages.error(request, 'An error occurred while copying the gradebook!')
            return redirect('grade-book')

    else:
        form = CopyGradeBookForm(user=request.user)

    return render(request, 'gradebook/copy-grade-book.html', {'form': form})

@login_required
def get_terms_and_subjects(request, semester_id):
    terms = Term.objects.filter(semester_id=semester_id).values('id', 'term_name')
    subjects = Subject.objects.filter(
        gradebook_components__term__semester_id=semester_id
    ).distinct().values('id', 'subject_name', 'subject_type')
    return JsonResponse({'terms': list(terms), 'subjects': list(subjects)})

@csrf_exempt
@login_required
@permission_required('gradebookcomponent.delete_gradebookcomponents', raise_exception=True)
def delete_multiple_gradebookcomponents(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ids = data.get("ids", [])

            # Ensure all IDs are valid integers
            ids = [int(i) for i in ids if str(i).isdigit()]

            if not ids:
                return JsonResponse({'status': 'error', 'message': 'Invalid IDs provided.'}, status=400)

            GradeBookComponents.objects.filter(id__in=ids).delete()
            return JsonResponse({'status': 'success', 'message': 'Selected GradeBook items deleted successfully!'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=400)


@login_required
@permission_required('gradebookcomponent.delete_gradebookcomponents', raise_exception=True)
def delete_grade_book(request, pk):
    if request.method != 'POST':
        return redirect('grade-book')
    component = get_object_or_404(GradeBookComponents, pk=pk)
    component.delete()
    messages.success(request, 'Gradebook component deleted.')
    return redirect('grade-book')
