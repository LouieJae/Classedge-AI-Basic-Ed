from django.urls import path
from module.views import *
from module.export_lessons import export_modules
from module.import_lessons import import_modules

urlpatterns = [
    path('material/list/<int:id>/', material_list, name='material-list'),
    path('material/list/<int:id>/students/', subject_student_roster, name='subject-student-roster'),
    path('student/pdf/viewer/', student_pdf_viewer, name='student-pdf-viewer'),
    path('material/list-cm/<int:id>/', material_list_cm, name='material-list-cm'),
    path('material/delete/<int:pk>/', delete_material, name='delete-material'),

    # Standard Mode URLs
    path('material/create/<int:subject_id>/', create_material, name='create-material'),
    path('material/create/url/<int:subject_id>/', create_material_url, name='create-material-url'),
    path('material/create/embed/<int:subject_id>/', create_material_embed, name='create-material-embed'),
    path('material/create/conference/<int:subject_id>/', create_conference, name='create-conference'),
    path('material/update/<int:pk>/', update_material, name='update-material'),
    path('material/update/url/<int:pk>/', update_material_url, name='update-material-url'),
    path('material/update/embed/<int:pk>/', update_material_embed, name='update-material-embed'),
    # Click-to-edit (cl-edit-inline) — PATCH-only rename endpoint
    path('material/rename/<int:pk>/', rename_module, name='rename-module'),
    path('material/view/<int:pk>/', view_module, name='view-material'),

    # Classroom Mode URLs
    path('create-material-cm/<int:subject_id>/', create_material_cm, name='create-material-cm'),
    path('create-material-url-cm/<int:subject_id>/', create_material_url_cm, name='create-material-url-cm'),
    path('create-material-embed-cm/<int:subject_id>/', create_material_embed_cm, name='create-material-embed-cm'),
    path('update-material-cm/<int:pk>/', update_material_cm, name='update-material-cm'),


    path('view-module-cm/<int:pk>/', view_module_cm, name='view-module-cm'),
    path('view-subject-module/<int:pk>/', view_subject_module, name='view-subject-module'),
    path('module-progress/', module_progress, name='module-progress'),
    path('activity-progress/module/<str:activity_id>/', detail_activity_progress, name='activity-progress'),
    path('progress-list/', progress_list, name='progress-list'),
    path('detail-progress/module/<int:module_id>/', detail_module_progress, name='detail-module-progress'),
    path('detail-progress-cm/module/<int:module_id>/', detail_module_progress_cm, name='detail-module-progress-cm'),
    path('download/<int:module_id>/', download_module, name='download'),
    path('file-validation-data/', file_validation_data, name='file-validation-data'),

    path('start-module-session/', start_module_session, name='start-module-session'),
    path('stop-module-session/', stop_module_session, name='stop-module-session'),
    path('subject/<int:subject_id>/copy-materials/', copy_lessons, name='copy-materials'),
    path('subject/<int:subject_id>/copy-materials-cm/', copy_lessons_cm, name='copy-materials-cm'),
    path('subject/<int:subject_id>/check-material-exists/', check_lesson_exists, name='check-material-exists'),
    path('subject/<int:subject_id>/get-subject-modules/', get_subject_modules, name='get-subject-modules'),

    # Subject-to-subject copy
    path('subject/<int:target_subject_id>/copy-materials-from-subject/', copy_lessons_from_subject, name='copy-materials-from-subject'),
    path('subject/<int:target_subject_id>/copy-materials-from-subject-cm/', copy_lessons_from_subject_cm, name='copy-materials-from-subject-cm'),
    path('check-subject-material-exists/<int:target_subject_id>/', check_subject_lesson_exists, name='check-subject-material-exists'),

    path('gale-library/', gale_library, name='gale-library'),

    path('export-modules/', export_modules, name='export-modules'),
    path('import-modules/', import_modules, name='import-modules'),

    path('import-and-export-material-page/', import_and_export_lesson_page, name='import-and-export-material-page'),

    path('material-progress-report/<int:pk>/', material_progress_report, name='material-progress-report'),
]
