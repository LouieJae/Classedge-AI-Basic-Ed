from accounts.models import Course
from accounts.forms import CourseForm
from accounts.utils import get_pagination_context, paginate_queryset, search_queryset
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.contrib.auth import get_user_model

User = get_user_model()


@login_required
@permission_required('course.view_course', raise_exception=True)
def program_list(request):
    """[Classedge LMS] Themed course list using the reusable list-table shell."""
    search_query = request.GET.get('search', '').strip()
    qs = Course.objects.select_related('department').all().order_by('name')
    qs = search_queryset(qs, search_query, ['name', 'short_name', 'department__name'])
    page_obj, _ = paginate_queryset(qs, request, items_per_page=10)

    context = {
        'search_query': search_query,
        'form': CourseForm(),
        'title': 'Program Catalog',
        'icon': 'fa-book-open',
        'search_placeholder': 'Search programs by name or short name...',
        'empty_icon': 'fa-book-open',
        'empty_label': 'programs',
        'columns': [
            {'label': '#', 'width': '60px', 'type': 'index'},
            {'label': 'Program', 'type': 'name', 'name_attr': 'name'},
            {'label': 'Short Name', 'type': 'pill', 'attr': 'short_name'},
            {'label': 'Department', 'type': 'pill', 'attr': 'department.name'},
            {'label': 'Action', 'align': 'right', 'type': 'actions', 'items': [
                {'label': 'Update', 'icon': 'fa-edit',
                 'onclick_template': 'openCourseEditModal({id})'},
                {'divider': True},
                {'label': 'Delete', 'icon': 'fa-trash', 'danger': True,
                 'form_post': True, 'url_name': 'program-delete', 'url_arg_attr': 'id',
                 'confirm': 'Delete this program? Students assigned to it will lose this label but otherwise be unaffected.'},
            ]},
        ],
    }
    context.update(get_pagination_context(page_obj, request))
    if request.GET.get('partial') == '1':
        return render(request, 'includes/_list_table.html', context)
    return render(request, 'accounts/course/course_list.html', context)


@login_required
@permission_required('course.add_course', raise_exception=True)
def create_program(request):
    """[Classedge LMS] Create program. Modal-driven from course_list."""
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Program created successfully.')
        else:
            messages.error(request, 'There were errors creating the program. Please review the form.')
    return redirect('program-list')


@login_required
@permission_required('course.change_course', raise_exception=True)
def update_program(request, id):
    """[Classedge LMS] Update program. GET returns the partial form for the edit modal."""
    course = get_object_or_404(Course, id=id)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, 'Program updated successfully.')
        else:
            messages.error(request, 'There were errors updating the program. Please review the form.')
        return redirect('program-list')
    form = CourseForm(instance=course)
    return render(request, 'accounts/course/_course_form.html', {'form': form, 'course': course})


@login_required
@permission_required('course.delete_course', raise_exception=True)
def delete_program(request, id=None):
    """[Classedge LMS] Two delete-pathways supported:

    - Legacy bulk delete via POST with ``id`` form-field (kept for backwards compat).
    - Inline single-row delete via the table action with the ``id`` URL kwarg.
    """
    target_id = id if id is not None else request.POST.get('id')
    course = get_object_or_404(Course, id=target_id)
    course.delete()
    messages.success(request, 'Course deleted successfully.')
    return redirect('program-list')
