import re
from datetime import datetime
from django.utils import timezone
from django.utils.dateparse import parse_datetime

# Boolean parsing

def _parse_bool(val) -> bool:
    if val is None:
        return False
    s = str(val).strip().lower()
    return s in {"true", "1", "yes", "y", "t", "on"}


# Datetime parsing

_DT_FORMATS = [
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y %I:%M %p",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%dT%H:%M:%S",
]


def _parse_dt(s):
    if not s:
        return None
    s = s.strip()
    dt = parse_datetime(s)
    if dt is None:
        for fmt in _DT_FORMATS:
            try:
                dt = datetime.strptime(s, fmt)
                break
            except ValueError:
                continue
    if dt and timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


# Robust CSV header helpers

def _norm_header(s: str) -> str:
    """Normalize a header for resilient matching: remove BOM, collapse spaces, lowercase."""
    if not s:
        return ""
    return re.sub(r"\s+", " ", s.replace("\ufeff", "")).strip().lower()


def _has_any_header(norm_headers: dict, *aliases: str) -> bool:
    """Check if any alias exists in the normalized header map."""
    return any(_norm_header(a) in norm_headers for a in aliases)


def _row_get(row: dict, norm_headers: dict, *aliases: str) -> str:
    for a in aliases:
        norm = _norm_header(a)
        if norm in norm_headers:
            original = norm_headers[norm]
            if original in row:
                val = row.get(original)
                if val is not None:
                    return str(val)
    # if we didn't find via alias map, try direct keys as fallback
    for a in aliases:
        v = row.get(a)
        if v is not None:
            return str(v)
    return ""
