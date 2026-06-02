from .user_views import *
from .archive_views import archive_index, archive_subject, archive_module  # noqa: F401
from .display_image_views import *

from .certificate_views import *
from .chart_views import *
from .course_views import *
from .dashboard import *
from .api_views import *
from .report_views import *
from .school_profile_views import *
from .sdg_views import *
from .api_key_views import *
from .jwks_views import *
from .dashboard import *
from .it_admin import *

from .department_admin import *  

from .user import (
    teacher_profile,student_profile, program_head_list, student_list, teacher_list, admin_and_staff_list,
    toggle_user_active, rename_profile,
    )

__all__ = [

    # User
    "student_profile", "teacher_profile","program_head_list","student_list","teacher_list","admin_and_staff_list",
    "toggle_user_active",
    "rename_profile",

    # Registrar Update Profile
    "update_student_profile",  "update_teacher_profile", "update_admin_and_staff_profile", "update_program_head_profile",

    "update_profile",

    # User views
    "CustomUserViewSet", "LoginAPIView", "register_user", "admin_login_view", 
    "student_list", "teacher_list",
    "admin_and_staff_list", "program_head_list",
     "admin_update_student_profile", "admin_update_teacher_profile", 
    "admin_update_program_head_profile", "admin_update_admin_and_staff_profile",
    "import_and_export_user_page",
    "error", "sign_out", "otp_reset_request", "otp_verify", "set_new_password", "setup_password",
    "IsSuperUser","verify_login_otp","resend_login_otp", "otp_request_api", "otp_verify_api", "set_new_password_api", 
    "MicrosoftLoginAPIView", "OnboardingView", "SetupPasswordView","view_student_profile", "User_Profile", "PowerSyncTokenRefreshView",
    "UserLegalConsentViewSet",
    
    # Display image views
    "DisplayImageViewSet", "display_image_list",
    
    # Certificate views
    "certificate_list", "create_certificate", "update_certificate", "delete_certificate","student_activities_json",
    
    # Chart views
    "studentPerCourse", "studentPerSubject",
    
    # Course views
    "program_list", "create_program", "update_program", "delete_program",
    
    # Dashboard
    "dashboard",
    
    # API views
    "get_user_subject_count", "get_student_count_per_course", "student_active_count",
    
    # Report views
    "get_teacher_progress_report", "teacher_login_report", "student_login_report",
    "enrollment_report", "subject_report", "course_report",
    "teacher_progress_report",

    # School profile views
    "school_profile", "change_school_name", "change_brand_color",

    # API key views
    "APIKeyViewSet", "api_key_management",

    # JWKS views
    "JWKSView", "PowerSyncTokenView",

    #dashboard
    "student_dashboard",

    # IT Admin
    "it_admin_dashboard",
]