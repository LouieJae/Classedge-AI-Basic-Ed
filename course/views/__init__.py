
from .attendance_views import *
from .self_attendance_views import student_self_mark_attendance, toggle_self_attendance
from .classroom_views import *
from .classroom_views import *
from .coil_and_hali_subject_views import *
from .enrollment_views import *
from .semester_views import *
from .subject_details_views import *
from .term_views import *
from .cte_subject import *
from .classmates_views import classmates

__all__ = [
            # Attendance Views
            "record_attendanceCM", "record_attendance", "attendance_list", "attendance_list_CM", "update_attendance",
            "update_attendance_CM", "delete_points","get_student_attendance",
            "attendance_report", "student_subject_attendance", "student_subject_attendanceCM", "export_attendance_by_date_range",
            "export_attendance_by_date_rangeCM", "export_student_attendance",
            "student_self_mark_attendance", "toggle_self_attendance",

            # Status
            'status_list', "add_points", "update_points",
            
            # Classroom Views
            "classroom_mode", 
            
            # Coil and Hali Subject Views — listings only; invite actions live in coil.views
            "coil_subjectList", "hali_subjectList",
            
            # Enrollment Views
            "EnrollStudentView", "enrollment_list", "drop_student_from_subject",
            "restore_student_from_subject", "delete_student_from_subject", "import_and_export_enrollment_page",
            "bulk_drop_enrollments", "drop_all_in_subject",
            "bulk_remove_enrollments", "remove_all_in_subject",
            
            # Semester Views
            "semester_list", "create_semester", "update_semester", "delete_semester", "end_semester",
            
            # Subject Details
            "subjectStudentListCM",
            "get_attendance_statuses", "update_attendance_status", "delete_attendance",
            "get_subject_students_api",
            
            # Term Views
            "TermViewSet", "term_list", "create_term", "update_term",
            "delete_term",

            # CTE Subject Views
            "cte_subject_list",

            # Classmates
            "classmates",
]
