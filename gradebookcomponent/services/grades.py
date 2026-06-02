"""[Classedge LMS] Weighted grade computation (extracted from studentTotalScore view).

Mirrors the conceptual shape of the existing `studentTotalScore` view in
`gradebookcomponent/views/utility_view.py` so that both surfaces agree on
how final grades are calculated.
"""
from activity.models.student_activity_model import StudentActivity
from gradebookcomponent.models import ActivityTypePercentage, GradeBookComponents


def compute_component_subtotal(student, subject, term, component):
    """[Classedge LMS] Return the subtotal (0-100) for one GradeBookComponents row.

    Each component carries a list of `ActivityTypePercentage` rows; we compute
    the student's percentage per activity type (earned_sum / max_sum * 100) and
    weight each by the type's declared percentage within the component.
    Missing submissions count as 0 — matching the existing studentTotalScore math.
    """
    if component.gradebook_category == "quest_completion":
        from gamification.quest_grading import get_student_quest_score
        return get_student_quest_score(student, subject, term)
    type_weights = ActivityTypePercentage.objects.filter(gradebook_component=component)
    subtotal = 0.0
    for tw in type_weights:
        sas = StudentActivity.objects.filter(
            student=student,
            subject=subject,
            term=term,
            activity__activity_type=tw.activity_type,
        ).select_related("activity")
        if not sas.exists():
            continue
        max_sum = sum((sa.activity.max_score or 0) for sa in sas)
        earned_sum = sum((sa.total_score or 0) for sa in sas)
        pct = (earned_sum / max_sum * 100) if max_sum else 0
        subtotal += pct * (float(tw.percentage) / 100.0)
    return round(subtotal, 2)


def compute_weighted_grade(student, subject, term):
    """[Classedge LMS] Return weighted final grade (0-100) for student in subject/term.

    Applies GradeBookComponents.percentage * ActivityTypePercentage.percentage
    weights to the student's StudentActivity scores. Missing scores count as 0.
    """
    components = GradeBookComponents.objects.filter(subject=subject, term=term)
    if not components.exists():
        return 0.0

    total = 0.0
    for component in components:
        subtotal = compute_component_subtotal(student, subject, term, component)
        total += subtotal * (float(component.percentage) / 100.0)
    return round(total, 2)
