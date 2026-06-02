"""[Classedge LMS] CSV export — streaming generator for per-subject gradebook."""
import csv

from accounts.models import CustomUser
from activity.models.activity_model import Activity
from activity.models.student_activity_model import StudentActivity
from gradebookcomponent.models import GradeBookComponents
from gradebookcomponent.services.grades import (
    compute_component_subtotal,
    compute_weighted_grade,
)


class _Echo:
    """[Classedge LMS] Minimal file-like object for csv.writer to stream into."""

    def write(self, value):
        return value


def build_gradebook_csv(subject, term):
    """[Classedge LMS] Yield CSV rows: header + one row per student with raw scores + weighted grade.

    If `term` is None, no activities can be scoped to a term, so the generator
    yields only the header + student demographic columns.
    """
    writer = csv.writer(_Echo())

    activity_qs = Activity.objects.filter(subject=subject, is_graded=True)
    if term is not None:
        activity_qs = activity_qs.filter(term=term)
    # Activity uses `local_id` as its primary key (no default `id` column).
    activities = list(activity_qs.order_by("start_time", "local_id"))

    component_qs = GradeBookComponents.objects.filter(subject=subject)
    if term is not None:
        component_qs = component_qs.filter(term=term)
    components = list(component_qs)

    header = ["Student ID", "Last Name", "First Name"]
    for a in activities:
        header.append(f"{a.activity_name} ({a.max_score})")
    for c in components:
        header.append(f"{c.gradebook_name or ''} Subtotal (%)")
    header.append("Final Grade (%)")
    yield writer.writerow(header)

    sa_qs = StudentActivity.objects.filter(subject=subject)
    if term is not None:
        sa_qs = sa_qs.filter(term=term)
    student_ids = list(sa_qs.values_list("student_id", flat=True).distinct())
    students = CustomUser.objects.filter(pk__in=student_ids).order_by(
        "last_name", "first_name"
    )

    for student in students:
        last_name = student.last_name or ""
        first_name = student.first_name or ""
        # If both name fields are blank, fall back to username so the row is
        # identifiable in the CSV (the helper fixtures leave names empty).
        if not last_name and not first_name:
            last_name = student.username or ""
        row = [
            getattr(student, "id_number", "") or student.id,
            last_name,
            first_name,
        ]
        sa_map_qs = StudentActivity.objects.filter(
            student=student, subject=subject
        ).prefetch_related("score_logs")
        if term is not None:
            sa_map_qs = sa_map_qs.filter(term=term)
        sa_map = {sa.activity_id: sa for sa in sa_map_qs}
        for a in activities:
            sa = sa_map.get(a.local_id)
            if sa is None:
                row.append("")
            else:
                # Uses prefetched score_logs — no additional query per cell.
                has_override = bool(list(sa.score_logs.all())[:1]) if hasattr(sa, "score_logs") else False
                marker = "*" if has_override else ""
                row.append(f"{sa.total_score}{marker}")
        for c in components:
            row.append(f"{compute_component_subtotal(student, subject, term, c)}")
        row.append(f"{compute_weighted_grade(student, subject, term)}")
        yield writer.writerow(row)
