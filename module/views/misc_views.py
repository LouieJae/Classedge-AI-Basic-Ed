from django.shortcuts import render
from django.contrib.auth.decorators import login_required, permission_required
from ..models.module import Module
from django.db.models import Q


@login_required
@permission_required('module.view_module', raise_exception=True)
def gale_library(request):
    return render(request, 'module/gale-library.html')


@login_required
@permission_required('module.view_module', raise_exception=True)
def import_and_export_lesson_page(request):
    from accounts.utils.pagination_utils import (
        paginate_queryset,
        get_pagination_context,
    )

    search_query = request.GET.get('search', '').strip()

    lessons = Module.objects.all().select_related('subject', 'term')

    # Search
    if search_query:
        lessons = lessons.filter(
            Q(file_name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(subject__subject_name__icontains=search_query)
            | Q(term__term_name__icontains=search_query)
        )

    # Pagination
    page_obj, paginator = paginate_queryset(lessons, request, items_per_page=10)
    pagination_context = get_pagination_context(page_obj, request)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    context.update(pagination_context)

    return render(request, 'module/import-and-export-material-page.html', context)
