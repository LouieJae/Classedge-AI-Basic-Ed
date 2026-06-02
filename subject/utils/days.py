import re
from typing import List
from subject.models import Schedule

DAY_NORMAL = {
    "m": "Mon", "mon": "Mon", "monday": "Mon",
    "t": "Tue", "tue": "Tue", "tuesday": "Tue",
    "w": "Wed", "wed": "Wed", "wednesday": "Wed",
    "th": "Thu", "thu": "Thu", "thur": "Thu", "thurs": "Thu", "thursday": "Thu",
    "f": "Fri", "fri": "Fri", "friday": "Fri",
    "sat": "Sat", "saturday": "Sat",
    "sun": "Sun", "sunday": "Sun",
}

COMPOSITES = {
    "tth": ["Tue", "Thu"],
    "mwf": ["Mon", "Wed", "Fri"],
    "mtw": ["Mon", "Tue", "Wed"],
    "mtwf": ["Mon", "Tue", "Wed", "Fri"],
    "mth": ["Mon", "Thu"],
    "mtthf": ["Mon", "Tue", "Thu", "Fri"],
}

# Canonical order for weekday labels
ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def parse_days(day_cell: str) -> List[str]:
    raw = (day_cell or "").strip()
    if not raw:
        return []
    s = re.sub(r"[()\[\]]", "", raw).strip()

    # comma-separated like "Tue,Thu" or "(Tuesday, Thursday)"
    if "," in s:
        parts = [p.strip() for p in s.split(",") if p.strip()]
        out = []
        for p in parts:
            token = p.lower()
            token = {"tues": "tue", "thur": "thu", "thurs": "thu"}.get(token, token)
            out.append(DAY_NORMAL.get(token, DAY_NORMAL.get(token[:3], DAY_NORMAL.get(token[:2], None))))
        return [d for d in out if d]

    # compact like "TTh", "MWF", or single token
    compact = re.sub(r"\s+", "", s).lower()
    if compact in COMPOSITES:
        return COMPOSITES[compact]

    token = {"tues": "tue", "thur": "thu", "thurs": "thu"}.get(compact, compact)
    d = DAY_NORMAL.get(token, DAY_NORMAL.get(token[:3], DAY_NORMAL.get(token[:2], None)))
    return [d] if d else []


def has_day(qs, day_key: str) -> bool:
    # match start-of-string, middle, or end-of-string tokens in the comma-separated multiselect
    return qs.filter(days_of_week__regex=rf'(^|,){re.escape(day_key)}(,|$)').exists()


TYPE_ALIASES = {
    "Build In": "Build in",
    "Builtin": "Build in",
    "Built-In": "Build in",
    "Over Load": "Overload",
    "Regular": "Regular",
}

# Valid schedule types from model choices
VALID_TYPES = {c[0] for c in Schedule.SCHEDULE_TYPE_CHOICES}
