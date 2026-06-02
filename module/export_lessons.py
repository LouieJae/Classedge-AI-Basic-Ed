from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Prefetch
from module.models.module import Module
import csv
import os

_TERM_NAME_CANDIDATES = ['name', 'title', 'display_name', 'term_name']
_TERM_CODE_CANDIDATES = ['code', 'term_code', 'short_name', 'identifier']

# Safe stringify for CSV.
def _s(v):
    
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)

# Friendly display for a Term regardless of actual field names.       
def _get_term_display(term):
   
    for attr in _TERM_NAME_CANDIDATES + _TERM_CODE_CANDIDATES:
        if hasattr(term, attr):
            val = getattr(term, attr, None)
            if val:
                return str(val)
    return str(term)

# Format datetimes as local 'YYYY-MM-DD HH:MM' for Excel friendliness.
def _fmt_dt(dt):
    
    if not dt:
        return ""
    try:
        return timezone.localtime(dt).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return dt.strftime("%Y-%m-%d %H:%M")


CHUNK_SIZE = 2000  # tune as you wish

@login_required
def export_modules(request):
    """
    Export Module rows to CSV (one row per Module).
    Includes Teacher Name + Room Number so export→import is unambiguous even if subject codes are reused.
    M2M 'display_lesson_for_selected_users' exported as pipe-separated emails.
    """

    # Template mode for the "Download Template" button
    if request.GET.get("template") == "true":
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="modules_template.csv"'
        resp.write("\ufeff")
        w = csv.writer(resp)
        w.writerow([
            "File Name",
            "Subject Name",
            "Subject Code",
            "Teacher Name",
            "Room Number",
            "Term",
            "URL",
            "Iframe Code",
            "File URL",
            "Stored File Name",
            "Allow Download",
            "Start Date (local)",
            "End Date (local)",
            "Description",
            "Visible To (emails | separated)",
        ])
        return resp

    ts = timezone.now().strftime("%Y%m%d-%H%M%S")
    filename = f"modules_{ts}.csv"

    qs = (
        Module.objects
        .select_related("subject", "term", "subject__assign_teacher")
        .prefetch_related(Prefetch("display_lesson_for_selected_users"))
        .order_by("subject__subject_code", "id")
    )

    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    resp.write("\ufeff")  # BOM for Excel

    w = csv.writer(resp)
    w.writerow([
        "File Name",
        "Subject Name",
        "Subject Code",
        "Teacher Name",
        "Room Number",
        "Term",
        "URL",
        "Iframe Code",
        "File URL",
        "Stored File Name",
        "Allow Download",
        "Start Date (local)",
        "End Date (local)",
        "Description",
        "Visible To (emails | separated)",
    ])

    for m in qs.iterator(chunk_size=CHUNK_SIZE):
        subj = m.subject
        term = m.term
        file_url = m.file.url if m.file else ""
        stored_file = os.path.basename(m.file.name) if m.file else ""

        # Teacher full name
        teacher_name = ""
        if subj and getattr(subj, "assign_teacher", None):
            t = subj.assign_teacher
            teacher_name = f"{(t.first_name or '').strip()} {(t.last_name or '').strip()}".strip()

        # Room
        room_number = getattr(subj, "room_number", "") or ""

        # join emails (fallback to username if email empty)
        viewers = []
        for u in m.display_lesson_for_selected_users.all():
            viewers.append(u.email or u.username or "")
        viewers_str = "|".join(sorted(set(filter(None, viewers))))

        # Friendly Term value regardless of field names
        term_display = _get_term_display(term) if term else ""

        w.writerow([
            _s(m.file_name),
            _s(getattr(subj, "subject_name", "")),
            _s(getattr(subj, "subject_code", "")),
            _s(teacher_name),
            _s(room_number),
            _s(term_display),
            _s(m.url),
            _s(m.iframe_code),
            _s(file_url),
            _s(stored_file),
            _s(m.allow_download),
            _s(_fmt_dt(m.start_date)),
            _s(_fmt_dt(m.end_date)),
            _s(m.description),
            _s(viewers_str),
        ])

    return resp

