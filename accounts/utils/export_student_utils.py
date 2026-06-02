# accounts/views.py
import csv
from django.http import HttpResponse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from accounts.models import Profile

CHUNK_SIZE = 2000

def _s(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)

@login_required
def export_all_user(request):
    """
    Minimal export aligned with your import format, plus Year Level.
    Columns: Email, First Name, Last Name, Role, ID Number, Year Level, Course, is_coil_user
    """
    qs = (
        Profile.objects
        .select_related("user", "role", "course")
        .order_by("user__id")
    )

    # Optional role filter: lets per-role list pages (teacher-list,
    # student-list, etc.) reuse this exporter via `?role=teacher`.
    role_filter = (request.GET.get("role") or "").strip()
    if role_filter:
        qs = qs.filter(role__name__iexact=role_filter)

    ts = timezone.now().strftime("%Y%m%d-%H%M%S")
    slug = role_filter.lower().replace(" ", "_") if role_filter else "minimal"
    filename = f"users_{slug}_{ts}.csv"

    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    resp.write("\ufeff")  # BOM for Excel

    w = csv.writer(resp)

    # ---- headers (now with Year Level) ----
    w.writerow([
        "Email",
        "First Name",
        "Last Name",
        "Role",
        "ID Number",
        "Year Level",     
        "Course",
    ])

    for p in qs.iterator(chunk_size=CHUNK_SIZE):
        u = p.user
        first_name = p.first_name or u.first_name or ""
        last_name  = p.last_name or u.last_name or ""
        role_name  = p.role.name if getattr(p, "role", None) else "Student"
        course_name = p.course.name if getattr(p, "course", None) else ""
        year_level = p.grade_year_level or ""

        w.writerow([
            _s(u.email),
            _s(first_name),
            _s(last_name),
            _s(role_name),
            _s(p.id_number),
            _s(year_level),    
            _s(course_name),
        ])

    return resp
