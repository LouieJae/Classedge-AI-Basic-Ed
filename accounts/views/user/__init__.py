# The dots are mandatory here to stay inside the 'user' package
from .teacher.teacher_crud import teacher_profile
from .student.student_crud import student_profile
from .general.user_crud import program_head_list, student_list, teacher_list, admin_and_staff_list, toggle_user_active, rename_profile

__all__ = [
    "teacher_profile", "student_profile", "program_head_list","student_list","teacher_list",
    "admin_and_staff_list", "toggle_user_active",
    "rename_profile",
    ]
