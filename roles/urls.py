from django.urls import path
from .views import (
    create_role, update_role, delete_role, role_list, view_role, get_role_permissions,
    import_roles_csv, export_roles_csv, download_roles_template, rename_role,
)

urlpatterns = [

    path('role/list/', role_list, name='role_list'),
    path('role/view/<int:role_id>/', view_role, name='view_role'),
    path('role/create/', create_role, name='create_role'),
    path('role/update/<int:pk>/', update_role, name='update_role'),
    path('role/delete/<int:pk>/', delete_role, name='delete_role'),
    path('rename_role/<int:pk>/', rename_role, name='rename_role'),
    path('delete_role/<int:pk>/', delete_role, name='delete_role'),
    path('get_role_permissions/<int:role_id>/', get_role_permissions, name='get_role_permissions'),
    path('import-roles/', import_roles_csv, name='import_roles_csv'),
    path('export-roles/', export_roles_csv, name='export_roles_csv'),
    path('download-roles-template/', download_roles_template, name='download_roles_template'),
  
]
