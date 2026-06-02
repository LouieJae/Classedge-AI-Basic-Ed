from .base import MapperResult, MissingFKError, all_mappers, get_mapper, register_mapper, require_fk

# Register mappers — each import has side-effect of populating the registry.
from . import accounts_course        # noqa: F401
from . import accounts_customuser    # noqa: F401
from . import accounts_department    # noqa: F401
from . import accounts_profile       # noqa: F401
from . import activity_activity      # noqa: F401
from . import activity_activity_question  # noqa: F401
from . import activity_activity_type # noqa: F401
from . import activity_question_choice    # noqa: F401
from . import activity_quiz_type     # noqa: F401
from . import activity_retake_score  # noqa: F401
from . import activity_rubrics       # noqa: F401
from . import activity_student_activity  # noqa: F401
from . import classroom_classroom_mode  # noqa: F401
from . import classroom_screenshot   # noqa: F401
from . import classroom_teacher_attendance  # noqa: F401
from . import course_attendance      # noqa: F401
from . import course_semester        # noqa: F401
from . import course_subjectenrollment  # noqa: F401
from . import course_term            # noqa: F401
from . import gradebookcomponent_models  # noqa: F401
from . import logs_user_activity_log  # noqa: F401
from . import module_module           # noqa: F401
from . import roles_role             # noqa: F401
from . import subject_schedule       # noqa: F401
from . import subject_subject        # noqa: F401

__all__ = ["MapperResult", "MissingFKError", "register_mapper", "get_mapper", "all_mappers", "require_fk"]
