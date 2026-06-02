from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from gradebookcomponent.models import TransmutationRule
from gradebookcomponent.forms import Transmutation_form
from django.contrib.auth.decorators import login_required

@login_required
def transmutation_list(request):
    """[Classedge LMS] Themed transmutation rule list using the reusable shell."""
    from accounts.utils import get_pagination_context, paginate_queryset, search_queryset

    search_query = request.GET.get('search', '').strip()
    qs = TransmutationRule.objects.all()
    qs = search_queryset(qs, search_query, ['transmutation_table_name', 'transmuted_value'])
    page_obj, _ = paginate_queryset(qs, request, items_per_page=10)

    context = {
        'search_query': search_query,
        'title': 'Transmutation Rules',
        'icon': 'fa-sliders',
        'search_placeholder': 'Search by table name or transmuted value...',
        'empty_icon': 'fa-sliders',
        'empty_label': 'transmutation rules',
        'columns': [
            {'label': '#', 'width': '60px', 'type': 'index'},
            {'label': 'Table', 'type': 'name', 'name_attr': 'transmutation_table_name'},
            {'label': 'Min Grade', 'type': 'meta', 'attr': 'min_grade'},
            {'label': 'Max Grade', 'type': 'meta', 'attr': 'max_grade'},
            {'label': 'Transmuted', 'type': 'pill', 'attr': 'transmuted_value'},
            {'label': 'Action', 'align': 'right', 'type': 'actions', 'items': [
                {'label': 'Update', 'icon': 'fa-edit',
                 'url_name': 'update-transmutation', 'url_arg_attr': 'id'},
                {'divider': True},
                {'label': 'Delete', 'icon': 'fa-trash', 'danger': True,
                 'form_post': True, 'url_name': 'delete-transmutation', 'url_arg_attr': 'id',
                 'confirm': 'Delete this transmutation rule?'},
            ]},
        ],
    }
    context.update(get_pagination_context(page_obj, request))
    if request.GET.get('partial') == '1':
        return render(request, 'includes/_list_table.html', context)
    return render(request, 'transmutation/transmutation-list.html', context)

@login_required
def create_transmutation(request):
    if request.method == 'POST':
        form = Transmutation_form(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Transmutation created successfully.')
                return redirect('transmutation-list')
            except Exception as e:
                messages.error(request, f'An unexpected error occurred: {e}')
        else:
            error_messages = []
            for field, errors in form.errors.items():
                for error in errors:
                    error_messages.append(f"{field.capitalize()}: {error}")
            messages.error(request, "Errors occurred:\n" + "\n".join(error_messages))
    else:
        form = Transmutation_form()

    return render(request, 'transmutation/create-transmutation.html', {'form': form})

@login_required
def update_transmutation(request, id):
    transmutation = get_object_or_404(TransmutationRule, id=id)
    if request.method == 'POST':
        form = Transmutation_form(request.POST, instance=transmutation)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transmutation updated successfully.')
            return redirect('transmutation-list')
        else:
            messages.error(request, 'An error occurred while updating the transmutation.')
    else:
        form = Transmutation_form(instance=transmutation)
    return render(request, 'transmutation/update-transmutation.html', {'form': form, 'transmutation': transmutation})

@login_required
def delete_transmutation(request, id):
    transmutation = get_object_or_404(TransmutationRule, id=id)
    transmutation.delete()
    messages.success(request, 'Transmutation deleted successfully.')
    return redirect('transmutation-list')


@login_required
def get_transmutation_rules(request):
    rules = TransmutationRule.objects.all().order_by('-max_grade')
    data = [
        {
            'table_name': rule.transmutation_table_name,
            'min_grade': float(rule.min_grade),
            'max_grade': float(rule.max_grade),
            'transmuted_value': float(rule.transmuted_value),
        }
        for rule in rules
    ]
    return JsonResponse({'rules': data})
