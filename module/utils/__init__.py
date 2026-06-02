# Re-export commonly used utilities for backward compatibility
from .parsing import _parse_bool, _parse_dt, _norm_header, _has_any_header, _row_get
from .viewers import _split_viewers
from .subject_term import _find_teacher_by_name, _find_term, _resolve_subject
