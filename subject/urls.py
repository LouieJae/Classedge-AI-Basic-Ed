from django.urls import path, include
from subject.utils import *
from subject.views import *
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'subject', SubjectViewSet, basename='subjects')
router.register(r'schedule_data', Schedule_Data, basename='schedule_data')
router.register(r'grade-finalization', SubjectGradeFinalizationViewSet, basename='grade-finalization')

urlpatterns = [
    path('api/', include(router.urls)),
    
    # Course
    path('course/list/', course_list, name='course-list'),
    path('course/create/', create_course, name='create-course'), 
    path('course/update/<int:pk>/', update_course, name='update-course'),
    # Click-to-edit (cl-edit-inline) — PATCH-only rename endpoint
    path('course/rename/<int:subject_id>/', rename_subject, name='rename-subject'),
    path('course/delete/<int:pk>/', delete_course, name='delete_course'),
    path('course/update/photo/<int:pk>/', update_course_photo, name='update-course-photo'),

    path('course/clear/photo/<int:pk>/', clear_subject_photo, name='clear_subject_photo'),

    path('check-duplicate-subject/', check_duplicate_subject, name='check_duplicate_subject'),
    path('filter_substitute_teacher/<int:assign_teacher_id>/', filter_substitute_teacher, name='filter_substitute_teacher'),
    path('create_coil_subject', create_coil_subject, name='create_coil_subject'),

    # Schedule  
    path('schedule/list/', schedule_list, name='schedule'),
    path('createSchedule/', create_schedule, name='createSchedule'),
    path('updateSchedule/<int:pk>/', update_schedule, name='updateSchedule'),
    path('deleteSchedule/<int:pk>/', delete_schedule, name='deleteSchedule'),
    path('api/schedules/<int:subject_id>/', ScheduleAPI.as_view(), name='schedule-api'),
    path('api/classroom_mode_schedules/<int:subject_id>/', Classroom_Mode_ScheduleAPI.as_view(), name='api/classroom_mode_schedules'),


    # Import Subjects and Schedules
    path('import-subjects/', import_subjects_and_schedules, name='import_subjects_and_schedules'),
    path("export-subjects-and-schedules/", export_subjects_and_schedules, name="export_subjects_and_schedules"),
    path("import_and_export_subject_page/", import_and_export_subject_page, name="import_and_export_subject_page"),
    

    #Evaluation
    path('create_evaluation_question/', create_evaluation_question, name='create_evaluation_question'),
    path('update_evaluation_question/<int:question_id>/', update_evaluation_question, name='update_evaluation_question'),
    path('delete_evaluation_question/<int:question_id>/', delete_evaluation_question, name='delete_evaluation_question'),
    path('list_questions/', list_evaluation_questions, name='list_questions'),
    path('create_teacher_evaluation/', create_teacher_evaluation, name='create_teacher_evaluation'),
    path('update_teacher_evaluation/<int:assignment_id>/', update_teacher_evaluation, name='update_teacher_evaluation'),
    path('delete_evaluation_assignment/<int:assignment_id>/', delete_evaluation_assignment, name='delete_evaluation_assignment'),
    path('list_evaluation_assignments/', list_evaluation_assignments, name='list_evaluation_assignments'),
    path('submit_evaluation/<int:assignment_id>/', submit_evaluation, name='submit_evaluation'),
    path('view_evaluation_results/<int:teacher_id>/<int:subject_id>/', view_evaluation_results, name='view_evaluation_results'),
    path('list_evaluation_results/', list_evaluation_results, name='list_evaluation_results'),
    path('list_available_evaluations/', list_available_evaluations, name='list_available_evaluations'),
    path('api/get_all_teachers_average_ratings_json/', get_all_teachers_average_ratings_json, name='api/get_all_teachers_average_ratings_json'),

    path('send-invite/<int:subject_id>/', send_collaboration_invite, name='send_collaboration_invite'),
    path('accept-invite/<uuid:token>/', accept_collaboration_invite, name='accept_collaboration_invite'),
    
    # Grade Finalization
    path('grade/finalization/', grade_finalization_page, name='grade_finalization_page'),
    
]