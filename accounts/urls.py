from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from accounts.views import DisplayImageViewSet
from accounts.utils import *
from accounts.views import *
from accounts.views.archive_views import archive_index, archive_subject, archive_module
from accounts.views.department_admin import (
    department_list,
    department_create,
    department_settings,
    department_delete,
)
from accounts.views.registrar import registrar_dashboard
from gamification.registrar_views import registrar_quest_settings
from accounts.views.coil_admin import coil_admin_dashboard
from accounts.views.academic_director import academic_director_dashboard
from accounts.views.program_head import program_head_dashboard
from accounts.views.time_keeper import time_keeper_dashboard
from accounts.views.super_admin import super_admin_dashboard, user_audit_log

#Router
router = DefaultRouter()
router.register(r'hccci_user', CustomUserViewSet)
router.register(r'display_image', DisplayImageViewSet, basename='display_image')
router.register(r'api_key', APIKeyViewSet, basename='api_key')
router.register(r'me', User_Profile, basename='me')

urlpatterns = [
    path('api/', include(router.urls)),
    path('tour/seen/', __import__('accounts.views.tour_views', fromlist=['mark_tour_seen']).mark_tour_seen, name='mark_tour_seen'),

    #Display Image
    path('display_image_list/', display_image_list, name='display_image_list'),

    #School Profile
    path('school/profile/', school_profile, name='school-profile'),
    path('change_school_name/', change_school_name, name='change_school_name'),
    path('change_brand_color/', change_brand_color, name='change_brand_color'),
    
    # Chart
    path('api/student-per-course/', studentPerCourse, name='api/student-per-course'),
    path("api/student-per-subject/", studentPerSubject, name="student_per_subject"),
    path("api/student_last_login_list/", student_active_count, name="api/student_last_login_list"),
    path('api/student_activities_json/', student_activities_json, name='student_activities_json'),


    # Program
    path('program/list/', program_list, name='program-list'),
    path('program/create/', create_program, name='program-create'),
    path('program/update/<int:id>/', update_program, name='program-update'),
    path('program/delete/<int:id>/', delete_program, name='program-delete'),
    
    # JWT Authentication endpoints
    path('api/auth/login/', LoginAPIView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', PowerSyncTokenRefreshView.as_view(), name='token_refresh'),
    path('api/powersync/jwks/', JWKSView.as_view(), name='powersync-jwks'),
    path('api/powersync/token/', PowerSyncTokenView.as_view(), name='powersync-token'),
        
    # User Authentication
    path('sign_out/', sign_out, name='sign_out'),
    path("otp-reset/", otp_reset_request, name="otp_reset"),
    path("otp-verify/<email>/", otp_verify, name="otp_verify"),
    path("set-new-password/<email>/", set_new_password, name="set_new_password"),
    path("verify-login-otp/", verify_login_otp, name="verify_login_otp"),
    path("resend-login-otp/", resend_login_otp, name="resend_login_otp"),
    path("api/auth/microsoft/", MicrosoftLoginAPIView.as_view(), name="microsoft-login"),

    # OTP Password & Reset & Setup Password & Onboarding API Endpoints
    path("api/auth/request-otp/", otp_request_api, name="otp_request_api"),
    path("api/auth/verify-otp/", otp_verify_api, name="otp_verify_api"),
    path("api/auth/reset-password/", set_new_password_api, name="set_new_password_api"),
    path('api/auth/setup-password/', SetupPasswordView.as_view(), name='setup_password'),
    path('api/auth/onboarding/', OnboardingView.as_view(), name='onboarding'),
    
    # Archive (read-only past-semester browsing)
    path('course/archive/', archive_index, name='archive-index'),
    path('account/archive/subject/<int:subject_id>/<int:semester_id>/', archive_subject, name='archive-subject'),
    path('account/archive/module/<int:module_id>/', archive_module, name='archive-module'),

    #User List
    path('account/student-list/', student_list, name='student-list'),
    path('account/teacher-list/', teacher_list, name='teacher-list'),
    path('account/admin-and-staff-list/', admin_and_staff_list, name='admin-and-staff-list'),
    path('account/program-head-list/', program_head_list, name='program-head-list'),
    path('account/toggle-active/<int:profile_id>/', toggle_user_active, name='toggle_user_active'),
    
    #User Profile
    path('account/profile/<int:pk>/', student_profile, name='account_profile'),
    path('u/<str:token>/', __import__('accounts.views.user.student.public_profile', fromlist=['public_student_profile']).public_student_profile, name='public_student_profile'),
    path('account/profile/share/toggle/', __import__('accounts.views.user.student.public_profile', fromlist=['toggle_profile_share']).toggle_profile_share, name='toggle_profile_share'),
    path('account/profile/view/<int:pk>/', view_student_profile, name='account_profile_view'),
    path('account/profile/update/<int:user_id>/', update_profile, name='update-profile'),
    
    #Admin
    path('account/admin/update-student-profile/<int:pk>/', admin_update_student_profile, name='admin-update-student-profile'),
    path('account/admin/update-teacher-profile/<int:pk>/', admin_update_teacher_profile, name='admin-update-teacher-profile'),
    path('account/admin/update-program-head-profile/<int:pk>/', admin_update_program_head_profile, name='admin-update-program-head-profile'),
    path('account/admin/update-staff-profile/<int:pk>/', admin_update_admin_and_staff_profile, name='admin-update-staff-profile'),
    # Click-to-edit (cl-edit-inline) — PATCH-only rename endpoint
    path('account/rename-profile/<int:pk>/', rename_profile, name='rename-profile'),
    
    #Registrar
    path('account/profile/update/student-profile/<int:pk>/', update_student_profile, name='update-student-profile'),
    path('account/profile/update/teacher-profile/<int:pk>/',  update_teacher_profile, name='update-teacher-profile'),
    path('account/profile/update/staff-profile/<int:pk>/', update_admin_and_staff_profile, name='update-admin-and-staff-profile'),
    path('account/profile/update/program-head-profile/<int:pk>/', update_program_head_profile, name='update-program-head-profile'),
    

    #Certificate
    path('certificate/list/', certificate_list, name='certificate-list'),
    path('certificate/create/', create_certificate, name='certificate-create'),
    path('certificate/update/<int:id>/', update_certificate, name='certificate-update'),
    path('certificate/delete/<int:id>/', delete_certificate, name='certificate-delete'),
    
    #Utils
    path('send_and_save_certificate/', send_and_save_certificate, name='send_and_save_certificate'),
    path('fetch_facebook_posts/', fetch_facebook_posts, name='fetch_facebook_posts'),
    path('import-students/', import_students, name='import_students'),
    path('export-all-user/', export_all_user, name='export_all_user'),
    
    #Reports
    path('student/login/report/', student_login_report, name='student-login-report'),
    path('enrollment/report/<int:student_id>/', enrollment_report, name='enrollment-report'),
    path('subject/report/', subject_report, name='subject-report'),
    path('course/report/', course_report, name='course-report'),
    path('teacher/login/report/', teacher_login_report, name='teacher-login-report'),
    path('teacher/progress/report/', teacher_progress_report, name='teacher-progress-report'),
    path('get_teacher_progress_report/', get_teacher_progress_report, name='get-teacher-progress-report'),
    
    # Interface
    path('', admin_login_view, name='admin_login_view'),
    path("it-admin/", it_admin_dashboard, name="it_admin_dashboard"),
    path("super-admin/", super_admin_dashboard, name="super_admin_dashboard"),
    path("super-admin/audit/", user_audit_log, name="user_audit_log"),
    path("registrar/", registrar_dashboard, name="registrar_dashboard"),
    path("registrar/quest-settings/", registrar_quest_settings, name="registrar_quest_settings"),
    path("coil-admin/", coil_admin_dashboard, name="coil_admin_dashboard"),
    path("academic-director/", academic_director_dashboard, name="academic_director_dashboard"),
    path("program-head/", program_head_dashboard, name="program_head_dashboard"),
    path("time-keeper/", time_keeper_dashboard, name="time_keeper_dashboard"),
    path('setup_password/', setup_password, name='setup_password'),
    path('register_user/', register_user, name='register_user'),
    path('dashboard/', dashboard, name='dashboard'),
    path('import_and_export_user_page/', import_and_export_user_page, name='import_and_export_user_page'),
    
    # Error
    path('error/', error, name='error'),

    # Api key
    path('api_key_management/', api_key_management, name='api_key_management'),

    # Dashboard
    path('student_dashboard/', student_dashboard, name='student_dashboard'),

    # [Classedge LMS] Department admin
    path("departments/list/", department_list, name="department_list"),
    path("departments/create/", department_create, name="department_create"),
    path("departments/<int:dept_id>/update/", department_settings, name="department_settings"),
    path("departments/<int:dept_id>/delete/", department_delete, name="department_delete"),
]
