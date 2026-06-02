
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from module.models.module import Module
from subject.models import Subject
from course.models import Term
from .utils.parsing import (
    _parse_bool,
    _norm_header,
    _has_any_header,
    _row_get,
    _parse_dt,
)
from .utils.subject_term import _resolve_subject, _find_term
from .utils.viewers import _split_viewers
import csv
import io

def import_modules(request):
    """
    Optimized CSV import for Module.
    - Uses Subject/Term caches
    - Uses bulk_create / bulk_update for speed
    - Bulk inserts M2M viewers
    """
    if request.method != "POST":
        return HttpResponse(status=405)

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    update_existing = _parse_bool(request.POST.get("update_existing"))

    import_file = request.FILES.get("import_file")
    if not import_file:
        message = "No file selected"
        if is_ajax:
            return JsonResponse({'success': False, 'message': message})
        messages.error(request, message)
        return redirect("import-modules")

    # ---- read CSV safely ----
    raw_bytes = import_file.read()
    text = raw_bytes.decode("utf-8-sig", errors="replace")

    try:
        sniff = csv.Sniffer().sniff(text[:4096])
        dialect = sniff
    except Exception:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        msg = "CSV seems empty or has no header row."
        if is_ajax:
            return JsonResponse({'success': False, 'message': msg})
        messages.error(request, msg)
        return redirect("import-modules")

    norm_headers = {_norm_header(h): h for h in reader.fieldnames if h}
    if not _has_any_header(norm_headers, "File Name", "Filename", "file_name", "File name"):
        msg = "CSV format error: Missing required column 'File Name'."
        if is_ajax:
            return JsonResponse({'success': False, 'message': msg})
        messages.error(request, msg)
        return redirect("import-modules")

    # ---- build caches ----
    subjects = {s.subject_code: s for s in Subject.objects.all()}
    terms = {}
    for t in Term.objects.all():
        # assume str(t) matches your _find_term display
        terms[str(t).strip()] = t

    to_create, to_update = [], []
    m2m_relations = []  # (module, [users])
    errors = []
    rows_ok, rows_updated, rows_skipped = 0, 0, 0

    # ---- prefetch existing modules (if updating) ----
    existing_modules = {}
    if update_existing:
        for m in Module.objects.all().only("id", "file_name", "subject_id", "term_id"):
            key = (m.subject_id, m.file_name, m.term_id or None)
            existing_modules[key] = m

    # ---- parse rows ----
    for idx, row in enumerate(reader, start=2):
        try:
            file_name = _row_get(row, norm_headers, "File Name", "Filename").strip()
            subject_code = _row_get(row, norm_headers, "Subject Code", "subject_code", "Code").strip()
            subject_name = _row_get(row, norm_headers, "Subject Name", "subject_name").strip()
            teacher_name = _row_get(row, norm_headers, "Teacher Name", "teacher_name").strip()
            room_number = _row_get(row, norm_headers, "Room Number", "room_number").strip()
            term_str = _row_get(row, norm_headers, "Term", "term").strip()
            url = _row_get(row, norm_headers, "URL", "Url").strip()
            iframe_code = _row_get(row, norm_headers, "Iframe Code").strip()
            file_url = _row_get(row, norm_headers, "File URL").strip()
            allow_download = _parse_bool(_row_get(row, norm_headers, "Allow Download").strip())
            start_date_str = _row_get(row, norm_headers, "Start Date (local)", "Start Date").strip()
            end_date_str = _row_get(row, norm_headers, "End Date (local)", "End Date").strip()
            description = _row_get(row, norm_headers, "Description").strip()
            order_str = _row_get(row, norm_headers, "Order").strip()
            viewers_cell = _row_get(row, norm_headers, "Visible To (emails | separated)", "visible_to").strip()

            if not file_name or not (subject_code or subject_name):
                errors.append(f"Row {idx}: Missing File Name or Subject")
                rows_skipped += 1
                continue

            subject = subjects.get(subject_code) or _resolve_subject(subject_code, subject_name, teacher_name, room_number)
            if not subject:
                errors.append(f"Row {idx}: Subject not found ({subject_code}/{subject_name})")
                rows_skipped += 1
                continue

            term = terms.get(term_str) or _find_term(term_str) if term_str else None

            final_url = url or file_url or ""
            start_dt = _parse_dt(start_date_str)
            end_dt = _parse_dt(end_date_str)

            try:
                order_val = int(order_str) if order_str else None
            except ValueError:
                order_val = None
                errors.append(f"Row {idx}: Invalid order '{order_str}'")

            viewers = _split_viewers(viewers_cell) if viewers_cell else []

            key = (subject.id, file_name, term.id if term else None)
            if update_existing and key in existing_modules:
                m = existing_modules[key]
                m.url = final_url
                m.iframe_code = iframe_code
                m.allow_download = allow_download
                m.start_date = start_dt
                m.end_date = end_dt
                m.description = description
                to_update.append(m)
                m2m_relations.append((m, viewers))
                rows_updated += 1
            else:
                m = Module(
                    subject=subject,
                    term=term,
                    file_name=file_name,
                    url=final_url,
                    iframe_code=iframe_code,
                    allow_download=allow_download,
                    start_date=start_dt,
                    end_date=end_dt,
                    description=description,
                    order=order_val or 0,
                )
                to_create.append(m)
                m2m_relations.append((m, viewers))
                rows_ok += 1

        except Exception as e:
            errors.append(f"Row {idx}: {e}")
            rows_skipped += 1

    # ---- bulk insert/update ----
    try:
        with transaction.atomic():
            if to_create:
                Module.objects.bulk_create(to_create, batch_size=500)
            if to_update:
                Module.objects.bulk_update(
                    to_update,
                    ["url", "iframe_code", "allow_download", "start_date", "end_date", "description", "order"],
                    batch_size=500,
                )

            # bulk M2M handling
            if m2m_relations:
                through = Module.display_lesson_for_selected_users.through
                inserts = []
                for m, viewers in m2m_relations:
                    if not viewers:
                        continue
                    for v in viewers:
                        inserts.append(through(module_id=m.id, customuser_id=v.id))
                if inserts:
                    through.objects.bulk_create(inserts, batch_size=1000, ignore_conflicts=True)

    except Exception as e:
        msg = f"Import failed: {e}"
        if is_ajax:
            return JsonResponse({'success': False, 'message': msg})
        messages.error(request, msg)
        return redirect("import-modules")

    # ---- summary ----
    summary = f"Import complete: {rows_ok} created, {rows_updated} updated, {rows_skipped} skipped"
    if is_ajax:
        return JsonResponse({
            "success": True,
            "message": summary,
            "created": rows_ok,
            "updated": rows_updated,
            "skipped": rows_skipped,
            "errors": errors,
        })
    messages.success(request, summary)
    for e in errors:
        messages.warning(request, e)
    return redirect("import-and-export-material-page")