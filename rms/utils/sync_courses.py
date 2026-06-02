"""Sync departments + courses (programs) from RMS.

RMS payload shape (per https://rms.hccci.edu.ph/api/courses/):
    {
        "id": 1,
        "course_name": "Bachelor of Early Childhood Education",
        "course_short_name": "BECED",
        "status": "active",
        "department": {"id": 4, "department_name": "College of Teacher Education"}
    }

ClassEdge stores Department + Course as separate ORM rows linked by FK
(`Course.department`). We upsert Department first (so the FK target exists),
then upsert Course matching on the canonical name.
"""
from accounts.models import Course, Department


def sync_courses(data):
    """Idempotently upsert Department + Course rows from the RMS payload.

    Returns a result dict shaped like the other RMS sync helpers so the
    UI can render uniform counts.
    """
    total_fetched = 0
    departments_created = 0
    departments_updated = 0
    courses_created = 0
    courses_updated = 0
    failed = 0
    failed_items = []

    for item in (data or []):
        total_fetched += 1
        try:
            course_name = (item.get("course_name") or "").strip()
            if not course_name:
                raise ValueError("Missing course_name")
            short_name = (item.get("course_short_name") or "").strip()

            dept_obj = None
            dept_payload = item.get("department") or {}
            dept_name = (dept_payload.get("department_name") or "").strip()
            if dept_name:
                dept_obj, dept_created = Department.objects.get_or_create(
                    name=dept_name,
                )
                if dept_created:
                    departments_created += 1
                else:
                    departments_updated += 1

            course, created = Course.objects.update_or_create(
                name=course_name,
                defaults={
                    "short_name": short_name or None,
                    "department": dept_obj,
                },
            )
            if created:
                courses_created += 1
            else:
                courses_updated += 1

        except Exception as exc:  # noqa: BLE001 — surface reason to caller
            failed += 1
            failed_items.append({
                "id": item.get("id"),
                "course_name": item.get("course_name"),
                "error": f"{type(exc).__name__}: {exc}",
            })

    return {
        "total_fetched": total_fetched,
        "created": courses_created,
        "updated": courses_updated,
        "failed": failed,
        "departments_created": departments_created,
        "departments_seen": departments_created + departments_updated,
        "failed_items": failed_items,
    }
