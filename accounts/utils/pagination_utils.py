from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q

def paginate_queryset(queryset, request, items_per_page=10):
    """
    Reusable pagination function
    
    Args:
        queryset: Django queryset to paginate
        request: HTTP request object
        items_per_page: Number of items per page (default: 10)
    
    Returns:
        page_obj: Paginated page object
        paginator: Paginator instance
    """
    # Get items per page from request or use default
    per_page = request.GET.get('per_page', items_per_page)
    try:
        per_page = int(per_page)
        if per_page not in [5, 10, 25, 50, 100]:
            per_page = items_per_page
    except (ValueError, TypeError):
        per_page = items_per_page
    
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)
    
    return page_obj, paginator


def search_queryset(queryset, search_query, search_fields):
    """
    Reusable search function
    
    Args:
        queryset: Django queryset to search
        search_query: Search term from user
        search_fields: List of field names to search (supports __ lookups)
    
    Returns:
        Filtered queryset
    
    Example:
        search_fields = ['first_name', 'last_name', 'user__email', 'id_number']
    """
    if not search_query or not search_fields:
        return queryset
    
    # Build Q objects for each field
    q_objects = Q()
    for field in search_fields:
        q_objects |= Q(**{f"{field}__icontains": search_query})
    
    return queryset.filter(q_objects)


def get_pagination_context(page_obj, request):
    """
    Generate pagination context for templates
    
    Args:
        page_obj: Paginated page object
        request: HTTP request object
    
    Returns:
        Dictionary with pagination context
    """
    # Get current query parameters (excluding 'page')
    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params.pop('page')
    
    # Build query string for pagination links
    query_string = '&'.join([f"{k}={v}" for k, v in query_params.items()])
    
    # Calculate page range to display (show ±3 pages around current)
    current_page = page_obj.number
    total_pages = page_obj.paginator.num_pages
    
    page_range_start = max(1, current_page - 3)
    page_range_end = min(total_pages, current_page + 3)
    page_range = range(page_range_start, page_range_end + 1)
    
    return {
        'page_obj': page_obj,
        'query_string': query_string,
        'page_range': page_range,
        'show_first': page_range_start > 1,
        'show_last': page_range_end < total_pages,
        'items_per_page': page_obj.paginator.per_page,
    }