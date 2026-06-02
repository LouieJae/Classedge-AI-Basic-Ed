import csv
import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Permission
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.utils.pagination_utils import (
    get_pagination_context,
    paginate_queryset,
    search_queryset,
)

from .decorators import admin_required
from .forms import RoleForm
from .models import Role
from .permission_categories import (
    get_all_categorized_permissions,
    get_categorized_permissions,
    get_categorized_permissions_grouped,
)

@login_required
@admin_required
def role_list(request):
    """[Classedge LMS] IT-Admin list view of all roles; renders the add-role side modal."""
    form = RoleForm()
    search_query = request.GET.get("search", "").strip()
    roles_qs = Role.objects.all().order_by("name")
    roles_qs = search_queryset(roles_qs, search_query, ["name"])
    page_obj, _ = paginate_queryset(roles_qs, request, items_per_page=10)
    context = {
        "roles": Role.objects.all().order_by("name"),  # for "Copy Permissions From" dropdown
        "search_query": search_query,
        "categorized_permissions": get_categorized_permissions(),
        "categorized_permissions_grouped": get_categorized_permissions_grouped(),
        "form": form,
        # Reusable list-table shell config
        "title": "Roles Master Data",
        "icon": "fa-user-shield",
        "search_placeholder": "Search roles by name...",
        "empty_icon": "fa-user-shield",
        "empty_label": "roles",
        "columns": [
            {"label": "#", "width": "60px", "type": "index"},
            {"label": "Role", "type": "name", "name_attr": "name",
             "editable": True, "edit_endpoint_name": "rename_role",
             "edit_url_arg_attr": "id", "edit_field": "name",
             "edit_min": 2, "edit_max": 100, "edit_label": "Role name"},
            {"label": "Created", "type": "date", "attr": "created_at"},
            {"label": "Action", "align": "right", "type": "actions", "items": [
                {"label": "View", "icon": "fa-eye",
                 "onclick_template": "openViewRoleModal({id})"},
                {"label": "Update", "icon": "fa-edit",
                 "onclick_template": "openEditRoleModal({id})"},
                {"divider": True},
                {"label": "Delete", "icon": "fa-trash", "danger": True,
                 "form_post": True, "url_name": "delete_role", "url_arg_attr": "id",
                 "confirm": "Are you sure you want to delete this role?"},
            ]},
        ],
    }
    context.update(get_pagination_context(page_obj, request))
    if request.GET.get("partial") == "1":
        return render(request, "includes/_list_table.html", context)
    return render(request, "role/role_list.html", context)

@login_required
@admin_required
def view_role(request, role_id):
    """[Classedge LMS] Read-only view of a single role's permission assignments."""
    role_obj = get_object_or_404(Role, id=role_id)
    return render(
        request,
        "role/view_role.html",
        {
            "role": role_obj,
            "categorized_permissions": get_categorized_permissions(),
            "categorized_permissions_grouped": get_categorized_permissions_grouped(),
            "role_permission_ids": set(role_obj.permissions.values_list("id", flat=True)),
        },
    )

@login_required
@admin_required
def create_role(request):
    """[Classedge LMS] Create a new role with selected permissions, optionally
    copying permissions from an existing role."""
    if request.method == "POST":
        form = RoleForm(request.POST)
        role_name = request.POST.get("name")

        if Role.objects.filter(name__iexact=role_name).exists():
            messages.error(
                request,
                f'The role "{role_name}" already exists. Please choose a different name.',
            )
            return redirect("role_list")

        if form.is_valid():
            role = form.save()
            selected_permissions = request.POST.getlist("permissions")
            permissions = Permission.objects.filter(id__in=selected_permissions)
            role.permissions.set(permissions)

            source_role_id = request.POST.get("source_role_id")
            if source_role_id:
                source_role = get_object_or_404(Role, id=source_role_id)
                role.permissions.set(source_role.permissions.all())

            messages.success(request, "Role created successfully!")
            return redirect("role_list")
        else:
            messages.error(
                request,
                "There was an error creating the role. Please check the form.",
            )
    else:
        form = RoleForm()

    return render(
        request,
        "role/add_role.html",
        {
            "form": form,
            "categorized_permissions": get_categorized_permissions(),
            "categorized_permissions_grouped": get_categorized_permissions_grouped(),
        },
    )


@login_required
@admin_required
def update_role(request, pk):
    """[Classedge LMS] Edit an existing role's name + permission assignments."""
    role_obj = get_object_or_404(Role, pk=pk)

    if request.method == "POST":
        form = RoleForm(request.POST, instance=role_obj)
        if form.is_valid():
            role = form.save()
            selected_permissions = request.POST.getlist("permissions")
            permissions = Permission.objects.filter(id__in=selected_permissions)
            role.permissions.set(permissions)
            messages.success(request, "Role updated successfully!")
            return redirect("role_list")
    else:
        form = RoleForm(instance=role_obj)

    return render(
        request,
        "role/update_role.html",
        {
            "form": form,
            "categorized_permissions": get_categorized_permissions(),
            "categorized_permissions_grouped": get_categorized_permissions_grouped(),
            "role": role_obj,
            "role_permission_ids": set(role_obj.permissions.values_list("id", flat=True)),
        },
    )

#Delete Role
@login_required
@admin_required
def delete_role(request, pk):
    role = get_object_or_404(Role, pk=pk)
    role.delete()
    messages.success(request, 'Role deleted successfully!')
    return redirect('role_list')


@login_required
@admin_required
def get_role_permissions(request, role_id):
    role = get_object_or_404(Role, id=role_id)
    permissions = role.permissions.all()
    permission_data = [{'id': perm.id, 'codename': perm.codename} for perm in permissions]
    return JsonResponse({'permissions': permission_data})

@login_required
@admin_required
def import_roles_csv(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file.')
            return redirect('import_roles_csv')
        
        try:
            # Read and decode the CSV file
            data_set = csv_file.read().decode('UTF-8')
            io_string = io.StringIO(data_set)
            reader = csv.DictReader(io_string)
            
            # Get all permissions for reference
            all_permissions = get_all_categorized_permissions()
            
            permission_map = {perm.codename: perm for perm in all_permissions}
            
            created_count = 0
            updated_count = 0

            for row in reader:
                try:
                    role_name = row.get('Role Name', '').strip()
                    if not role_name:
                        continue

                    # Get existing role (case-insensitive) or create a new one.
                    existing = Role.objects.filter(name__iexact=role_name).first()
                    if existing:
                        role = existing
                        was_created = False
                    else:
                        role = Role.objects.create(name=role_name)
                        was_created = True

                    # Process permissions dynamically
                    permissions_to_add = []

                    # Get all available permissions dynamically
                    for perm in all_permissions:
                        # Create display name for CSV column
                        action = perm.codename.split('_')[0]
                        model_name = perm.content_type.model
                        display_name = f'Can {action} {model_name}'

                        # Check if this permission is marked as Yes in the CSV
                        if display_name in row and row[display_name].strip().lower() in ['yes', 'y', '1', 'true']:
                            permissions_to_add.append(perm)

                        # Also check for alternative formats
                        alternative_names = [
                            perm.codename,
                            perm.codename.replace('_', ' ').title(),
                            f'{action} {model_name}'.title()
                        ]

                        for alt_name in alternative_names:
                            if alt_name in row and row[alt_name].strip().lower() in ['yes', 'y', '1', 'true']:
                                if perm not in permissions_to_add:
                                    permissions_to_add.append(perm)
                                break

                    # Replace the role's permissions with the CSV-defined set
                    # (set() also clears any permissions not present in the CSV row).
                    role.permissions.set(permissions_to_add)

                    if was_created:
                        created_count += 1
                    else:
                        updated_count += 1

                except Exception as e:
                    messages.warning(request, f'Error processing row: {str(e)}')
                    continue

            messages.success(request, f'Successfully created {created_count} new roles and updated {updated_count} existing roles from the CSV.')
            return redirect('role_list')
            
        except Exception as e:
            messages.error(request, f'Error processing CSV file: {str(e)}')
            return redirect('import_roles_csv')
    
    return render(request, 'role/import_roles.html')

@login_required
@admin_required
def download_roles_template(request):
    """[Classedge LMS] Download a CSV template for role import.

    Header row is built dynamically from get_all_categorized_permissions so
    it always stays in sync with what import_roles_csv will accept — the
    old hardcoded list drifted (wrong model names, dead models) and caused
    silent data loss on re-import.
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="roles_import_template.csv"'

    writer = csv.writer(response)

    sorted_permissions = get_all_categorized_permissions().order_by(
        "content_type__app_label", "content_type__model", "codename",
    )
    headers = ["Role Name"] + [
        f"Can {p.codename.split('_', 1)[0]} {p.content_type.model}"
        for p in sorted_permissions
    ]
    writer.writerow(headers)

    sample_row = ["Sample Role"] + ["No"] * (len(headers) - 1)
    writer.writerow(sample_row)

    return response

@login_required
@admin_required
def export_roles_csv(request):
    # Create a CSV export of all existing roles with their permissions
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="roles_export.csv"'
    
    writer = csv.writer(response)
    
    # Define the header row
    headers = ['Role Name']
    
    # Get all relevant permissions dynamically
    all_permissions = get_all_categorized_permissions()
    
    # Sort permissions by model and action for consistent ordering
    sorted_permissions = sorted(all_permissions, key=lambda p: (p.content_type.model, p.codename))
    
    # Build permission codename map dynamically
    permission_codename_map = {}
    permission_display_names = []
    
    for perm in sorted_permissions:
        action = perm.codename.split('_')[0]
        model_name = perm.content_type.model
        display_name = f'Can {action} {model_name}'
        permission_display_names.append(display_name)
        permission_codename_map[display_name] = perm.codename
    
    headers.extend(permission_display_names)
    writer.writerow(headers)
    
    # Get all roles with their permissions
    roles = Role.objects.all().prefetch_related('permissions')
    
    # Write data for each role
    for role in roles:
        row_data = [role.name]
        
        # Check each permission
        for display_name in permission_display_names:
            codename = permission_codename_map[display_name]
            has_permission = role.permissions.filter(codename=codename).exists()
            row_data.append('Yes' if has_permission else 'No')
        
        writer.writerow(row_data)
    
    return response


# ─── Click-to-edit endpoint ───────────────────────────────────────────
import json
from django.views.decorators.http import require_http_methods
from .models import Role


@login_required
@admin_required
@require_http_methods(["PATCH"])
def rename_role(request, pk):
    role = get_object_or_404(Role, pk=pk)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Malformed request body.'}, status=400)

    new_name = (payload.get('name') or '').strip()
    if not new_name:
        return JsonResponse({'ok': False, 'error': 'Role name cannot be empty.'}, status=400)
    if len(new_name) < 2:
        return JsonResponse({'ok': False, 'error': 'Role name must be at least 2 characters.'}, status=400)
    if len(new_name) > 100:
        return JsonResponse({'ok': False, 'error': 'Role name must be at most 100 characters.'}, status=400)

    if Role.objects.exclude(pk=role.pk).filter(name__iexact=new_name).exists():
        return JsonResponse({'ok': False, 'error': 'Another role already uses this name.'}, status=400)

    role.name = new_name
    role.save(update_fields=['name'])
    return JsonResponse({'ok': True, 'value': new_name})

