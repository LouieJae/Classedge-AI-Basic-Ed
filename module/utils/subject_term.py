from django.db.models import Value
from django.db.models.functions import Concat
from django.core.exceptions import FieldError
from django.utils import timezone
from django.contrib.auth import get_user_model
from subject.models import Subject
from course.models import Term

User = get_user_model()


def _find_teacher_by_name(teacher_name: str):
    """
    Match 'First Last' case-insensitively. Returns a User or None.
    Tries exact full-name match first, then falls back to first/last split.
    """
    if not teacher_name:
        return None
    norm = " ".join(teacher_name.split()).strip()
    if not norm:
        return None

    qs = User.objects.annotate(full_name=Concat('first_name', Value(' '), 'last_name'))
    u = qs.filter(full_name__iexact=norm).first()
    if u:
        return u

    parts = norm.split(" ")
    if len(parts) >= 2:
        first, last = parts[0], parts[-1]
        fallback = User.objects.filter(first_name__iexact=first, last_name__iexact=last).first()
        if fallback:
            return fallback

    return None


# ---------- TERM helpers (work with name/term_name and code/term_code) ----------

_TERM_NAME_CANDIDATES = ["name", "term_name"]
_TERM_CODE_CANDIDATES = ["code", "term_code"]


def _term_filter_exact(val):
    """Return a queryset filtered by exact match on any known name/code field."""
    qs = Term.objects.all()
    for field in _TERM_NAME_CANDIDATES + _TERM_CODE_CANDIDATES:
        try:
            found = qs.filter(**{f"{field}__iexact": val})
            if found.exists():
                return found
        except FieldError:
            continue
    return Term.objects.none()


def _term_filter_contains(val):
    """Return a queryset filtered by icontains on any known name/code field."""
    qs = Term.objects.all()
    for field in _TERM_NAME_CANDIDATES + _TERM_CODE_CANDIDATES:
        try:
            found = qs.filter(**{f"{field}__icontains": val})
            if found.exists():
                return found
        except FieldError:
            continue
    return Term.objects.none()


def _find_term(term_str: str):
    """
    Resolve Term by trying known name/code fields (name, term_name, code, term_code).
    Supports exported format 'Name - YYYY-MM-DD - YYYY-MM-DD'.
    Also supports passing a numeric primary key.
    """
    if not term_str:
        return None
    term_str = term_str.strip()

    # Try the full string exact (any field)
    qs = _term_filter_exact(term_str)
    if qs.exists():
        return qs.first()

    # If looks like "Final Term - 2025-08-01 - 2025-08-31", try the left part
    if " - " in term_str:
        simple = term_str.split(" - ")[0].strip()
        qs = _term_filter_exact(simple)
        if qs.exists():
            return qs.first()
        qs = _term_filter_contains(simple)
        if qs.exists():
            return qs.first()

    # Try contains on the full string
    qs = _term_filter_contains(term_str)
    if qs.exists():
        return qs.first()

    # Numeric ID fallback
    if term_str.isdigit():
        t = Term.objects.filter(pk=int(term_str)).first()
        if t:
            return t

    print(f"[TERM RESOLUTION] Term '{term_str}' not found on any of fields { _TERM_NAME_CANDIDATES + _TERM_CODE_CANDIDATES }")
    return None


# ---------- SUBJECT resolver ----------

def _resolve_subject(subject_code: str, subject_name: str, teacher_name: str, room_number: str):
    """
    Resolve Subject primarily by subject_name (case-insensitive).
    If multiple subjects share the same name, try subject_code to break ties.
    Room/teacher are used ONLY to break ties (never to zero out matches).
    """
    qs = Subject.objects.all()

    candidates = []
    if subject_name:
        candidates = list(qs.filter(subject_name__iexact=subject_name.strip()))

    # If no name match, allow code as fallback
    if not candidates and subject_code:
        candidates = list(qs.filter(subject_code__iexact=subject_code.strip()))

    if len(candidates) == 1:
        return candidates[0]

    # Tie-breakers (do NOT eliminate to zero if no match)
    if len(candidates) > 1 and subject_code:
        narrowed = [s for s in candidates if (s.subject_code or '').strip().lower() == subject_code.strip().lower()]
        if narrowed:
            candidates = narrowed

    if len(candidates) > 1 and room_number:
        rn = room_number.strip().lower()
        narrowed = [s for s in candidates if ((getattr(s, 'room_number', '') or '').strip().lower() == rn)]
        if narrowed:
            candidates = narrowed

    if len(candidates) > 1 and teacher_name:
        teacher = _find_teacher_by_name(teacher_name)
        if teacher:
            narrowed = [s for s in candidates if getattr(s, 'assign_teacher_id', None) == teacher.id]
            if narrowed:
                candidates = narrowed

    # Final decision
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        print(f"[SUBJECT WARN] Multiple subjects matched name='{subject_name}'. Picking the lowest id.")
        return sorted(candidates, key=lambda s: s.id)[0]

    return None
