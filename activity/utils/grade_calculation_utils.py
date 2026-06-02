from collections import defaultdict
from decimal import Decimal
from course.models import TeacherAttendancePoints
from django.db.models import Q
from gradebookcomponent.models import (
    GradeBookComponents,
    TermGradeBookComponents,
    GradeVisibilitySettings,
)


def get_gradebook_components_by_term(subject, terms):
    """
    Returns a dictionary: term_id -> list of GradeBookComponents
    Each component carries its own gradebook_category, percentage, and
    prefetched activity_type_percentages (sub-activities).
    """
    components_by_term = defaultdict(list)
    qs = (
        GradeBookComponents.objects.filter(subject=subject, term__in=terms)
        .select_related('term')
        .prefetch_related('activity_type_percentages__activity_type')
    )
    for component in qs:
        components_by_term[component.term.id].append(component)
    return components_by_term


def get_activity_type_percentage_lookup(subject, terms):
    """
    Backward-compatible lookup: (term_id, activity_type_name) -> percentage.

    Each (term, activity_type) is expected to live under exactly one component
    per subject. If duplicates exist (the model now permits it), the last one
    wins — preserving the prior behavior used by attendance-weighted scoring.
    """
    lookup = {}
    for term_id, components in get_gradebook_components_by_term(subject, terms).items():
        for component in components:
            for atp in component.activity_type_percentages.all():
                lookup[(term_id, atp.activity_type.name)] = atp.percentage
    return lookup


def get_gradebook_category_lookup(subject, terms):
    """
    Returns a dictionary: (term_id, category_name) -> total percentage for that
    category in that term. With flexible categories, the keys reflect whatever
    category names teachers have actually used.
    """
    lookup = defaultdict(lambda: Decimal(0))
    for term_id, components in get_gradebook_components_by_term(subject, terms).items():
        for component in components:
            lookup[(term_id, component.gradebook_category)] += component.percentage
    return lookup


def get_term_gradebook_component_percentage(subject, terms):
    """
    Returns a dictionary: (term_id) -> percentage for the given subject
    """
    term_pct_lookup = {}
    components = TermGradeBookComponents.objects.filter(term__in=terms, subjects=subject)
    for component in components:
        term_pct_lookup[component.term.id] = component.percentage
    return term_pct_lookup


def get_term_gradebook_base_grade(subject, terms):
    """
    Returns a dictionary: (term_id) -> base_grade for the given subject
    """
    term_base_grade_lookup = {}
    components = TermGradeBookComponents.objects.filter(term__in=terms, subjects=subject)
    for component in components:
        term_base_grade_lookup[component.term.id] = component.base_grade
    return term_base_grade_lookup


def apply_remedial_grade(student_summary, passing_grade=Decimal(75)):
    """
    Applies remedial grade adjustments to student summary data.
    """
    for student_name, data in student_summary.items():
        original_grade = data.get("final_grade")
        has_remedial = data.get("has_remedial", False)
        if not has_remedial or original_grade is None:
            continue
        if has_remedial and original_grade >= passing_grade:
            data["final_grade"] = passing_grade
            data["remedial_applied"] = True
    return student_summary


def get_student_activity_summary(semester, subject, terms, activity_queryset, attendance_queryset, request_user):
    summary = defaultdict(
        lambda: {
            "student_id": None,
            "activities": defaultdict(dict),
            "attendance": defaultdict(dict),
            "term_info": {},
            "has_remedial": False,
        }
    )

    user_is_student = (
        hasattr(request_user, "profile")
        and request_user.profile.role
        and request_user.profile.is_student
    )

    visibility_by_term = {}
    if user_is_student:
        activity_queryset = activity_queryset.filter(student=request_user)
        attendance_queryset = attendance_queryset.filter(student=request_user)
        visibility_qs = GradeVisibilitySettings.objects.filter(subject=subject)
        subject_level_setting = visibility_qs.filter(term=None).first()
        default_visibility = subject_level_setting.is_visible if subject_level_setting else False
        visibility_by_term[None] = default_visibility
        for v in visibility_qs.filter(term__isnull=False):
            visibility_by_term[v.term.id] = v.is_visible
            
    activity_queryset = activity_queryset.filter(
        activity__studentquestion__isnull=False
    ).distinct()

    percentage_lookup = get_activity_type_percentage_lookup(subject, terms)
    base_grade_lookup = get_term_gradebook_base_grade(subject, terms)

    # Activities
    for activity in activity_queryset:
        student = activity.student
        student_name = f"{student.profile.first_name} {student.profile.last_name}"
        activity_type = activity.activity.activity_type.name if activity.activity.activity_type else "Unknown Activity Type"
        term = activity.term
        term_name = term.term_name if term else "Unknown Term"
        max_score = Decimal(activity.activity.max_score or 0)
        total_score = Decimal(activity.total_score or 0)

        summary[student_name]["student_id"] = student.id
        summary[student_name]["email"] = student.email
        if activity.activity.remedial and (student in activity.activity.remedial_students.all()):
            summary[student_name]["has_remedial"] = True

        if activity_type not in summary[student_name]["activities"][term_name]:
            summary[student_name]["activities"][term_name][activity_type] = {
                "total_score": Decimal(0),
                "max_score": Decimal(0),
                "weighted_score": Decimal(0),
                "activities_breakdown": [],
            }

        summary[student_name]["activities"][term_name][activity_type]["activities_breakdown"].append(
            {
                "activity_name": activity.activity.activity_name,
                "start_date": activity.activity.start_time.strftime("%m/%d/%Y %I:%M%p") if activity.activity.start_time else None,
                "end_date": activity.activity.end_time.strftime("%m/%d/%Y %I:%M%p") if activity.activity.end_time else None,
                "student_score": float(total_score),
                "max_score": float(max_score),
                "remedial": activity.activity.remedial,
                "passing_score": float(activity.activity.passing_score) if activity.activity.passing_score else 0,
                "passing_score_type": activity.activity.passing_score_type if hasattr(activity.activity, 'passing_score_type') else "percentage",
            }
        )

        summary[student_name]["activities"][term_name][activity_type]["total_score"] += total_score
        summary[student_name]["activities"][term_name][activity_type]["max_score"] += max_score

    # Compute weighted scores
    for student_name, data in summary.items():
        for term in terms:
            term_name = term.term_name
            for activity_type, scores in data["activities"].get(term_name, {}).items():
                max_score = scores["max_score"]
                total_score = scores["total_score"]
                percentage = Decimal(percentage_lookup.get((term.id, activity_type), 0))
                # Calculate weighted score: (score/max) * 100 * (percentage/100) = (score/max) * percentage
                # But we want the result as a percentage contribution, so: (score/max) * percentage
                weighted_score = (total_score / max_score) * percentage if max_score > 0 else Decimal(0)
                data["activities"][term_name][activity_type]["weighted_score"] = round(weighted_score, 2)

    # Attendance
    for record in attendance_queryset:
        student = record.student
        student_name = f"{student.profile.first_name} {student.profile.last_name}"
        
        # Set student_id and email if not already set (for students with only attendance, no activities)
        if summary[student_name]["student_id"] is None:
            summary[student_name]["student_id"] = student.id
            summary[student_name]["email"] = student.email
        
        term_name = "Unknown Term"
        matched_term = None
        for term in terms:
            # Terms without a start/end window can't match an attendance date;
            # likewise, records without a date can't slot into any term.
            if not term.start_date or not term.end_date or record.date is None:
                continue
            if term.start_date <= record.date <= term.end_date:
                term_name = term.term_name
                matched_term = term
                break
        points_obj = TeacherAttendancePoints.objects.filter(teacher=record.teacher, status=record.status).first()
        attendance_points = Decimal(points_obj.points if points_obj else 0)
        if "total_attendance" not in summary[student_name]["attendance"].get(term_name, {}):
            summary[student_name]["attendance"][term_name] = {
                "total_attendance": Decimal(0),
                "max_attendance": Decimal(0),
                "weighted_score": Decimal(0),
                "records": [],
            }
        summary[student_name]["attendance"][term_name]["total_attendance"] += attendance_points
        summary[student_name]["attendance"][term_name]["max_attendance"] += Decimal(10)
        summary[student_name]["attendance"][term_name]["records"].append(
            {"date": record.date, "status": record.status.status if record.status else None, "points": attendance_points}
        )

    # Attendance weighted score
    for student_name, data in summary.items():
        for term in terms:
            term_name = term.term_name
            if term_name in data["attendance"]:
                attendance_data = data["attendance"][term_name]
                total = attendance_data["total_attendance"]
                max_val = attendance_data["max_attendance"]
                percentage = Decimal(percentage_lookup.get((term.id, "Attendance"), 0))
                attendance_data["weighted_score"] = round((total / max_val) * percentage, 2) if max_val > 0 else Decimal(0)

    # Aggregate per-term gradebook categories and final grade.
    # Each GradeBookComponents row is a category configured by the teacher.
    # Its child ActivityTypePercentage rows say which activity types contribute
    # and at what sub-weight (sub-weights sum to 100 within a category).
    components_by_term = get_gradebook_components_by_term(subject, terms)
    base_grade_lookup = get_term_gradebook_base_grade(subject, terms)

    for student_name, data in summary.items():
        if "term_grades" not in data:
            data["term_grades"] = {}
        for term in terms:
            term_name = term.term_name
            student_term_activities = data["activities"].get(term_name, {})
            attendance_for_term = data["attendance"].get(term_name)

            base_grade = Decimal(base_grade_lookup.get(term.id, 0) or 0)
            term_total = Decimal(0)
            categories_breakdown = {}

            for component in components_by_term.get(term.id, []):
                category = component.gradebook_category
                category_pct = Decimal(component.percentage or 0)

                # Sum the sub-activity contributions for this category.
                # Each ATP contributes (score/max) * atp.percentage, yielding a
                # score in [0, atp.percentage]. The sum across ATPs is in [0, 100].
                category_score_within = Decimal(0)
                for atp in component.activity_type_percentages.all():
                    activity_type_name = atp.activity_type.name
                    sub_pct = Decimal(atp.percentage or 0)

                    # Special case: Attendance is tracked separately in
                    # data["attendance"], not in data["activities"].
                    if activity_type_name.lower() == "attendance":
                        if attendance_for_term:
                            total = attendance_for_term["total_attendance"]
                            max_val = attendance_for_term["max_attendance"]
                            if max_val > 0:
                                category_score_within += (total / max_val) * sub_pct
                        continue

                    item = student_term_activities.get(activity_type_name)
                    if not item:
                        continue
                    max_score = item["max_score"]
                    total_score = item["total_score"]
                    if max_score > 0:
                        category_score_within += (total_score / max_score) * sub_pct

                # category_score_within is 0..100; weight by the category percentage.
                category_contribution = category_score_within * category_pct / 100
                if base_grade > 0 and category_pct > 0:
                    category_contribution = max(
                        category_contribution, (base_grade / 100) * category_pct
                    )

                categories_breakdown[category] = (
                    categories_breakdown.get(category, Decimal(0)) + category_contribution
                )
                term_total += category_contribution

            term_total = min(term_total, Decimal(100))

            term_grades_entry = {cat: round(score, 2) for cat, score in categories_breakdown.items()}
            term_grades_entry["categories"] = [
                {"name": cat, "score": round(score, 2)}
                for cat, score in categories_breakdown.items()
            ]
            term_grades_entry["total_grade"] = round(term_total, 2)
            data["term_grades"][term_name] = term_grades_entry

    term_pct_lookup = get_term_gradebook_component_percentage(subject, terms)
    for student_name, data in summary.items():
        final_grade = Decimal(0)
        for term in terms:
            term_name = term.term_name
            term_grades = data.get("term_grades", {}).get(term_name)
            if term_grades and "total_grade" in term_grades:
                term_pct = Decimal(term_pct_lookup.get(term.id, 100))
                final_grade += term_grades["total_grade"] * term_pct / 100
        data["final_grade"] = round(min(final_grade, Decimal(100)), 2)

    passing_grade = Decimal(semester.passing_grade if semester else 75)
    summary = apply_remedial_grade(summary, passing_grade)

    term_info = {}
    for term in terms:
        term_info[term.term_name] = term.id
    for student_name, data in summary.items():
        data["term_info"] = term_info

    # Always expose per-term visibility so teachers/admins can render the
    # correct toggle state. For students the value is ALSO used to hide
    # term grades (handled below).
    teacher_visibility_qs = GradeVisibilitySettings.objects.filter(subject=subject)
    teacher_visibility = {}
    teacher_default = teacher_visibility_qs.filter(term=None).first()
    teacher_visibility[None] = teacher_default.is_visible if teacher_default else False
    for v in teacher_visibility_qs.filter(term__isnull=False):
        teacher_visibility[v.term.id] = v.is_visible
    for student_name, data in summary.items():
        for term in terms:
            term_name = term.term_name
            tv = teacher_visibility.get(term.id, teacher_visibility.get(None, False))
            if "term_grades" in data and term_name in data["term_grades"]:
                data["term_grades"][term_name]["visibility"] = tv

    if user_is_student:
        for student_name, data in summary.items():
            for term in terms:
                term_name = term.term_name
                is_visible = visibility_by_term.get(term.id, visibility_by_term.get(None, False))
                if "term_grades" in data and term_name in data["term_grades"]:
                    data["term_grades"][term_name]["visibility"] = is_visible
                if not is_visible and "term_grades" in data and term_name in data["term_grades"]:
                    hidden_categories = list(
                        data["term_grades"][term_name].get("categories", []) or []
                    )
                    data["term_grades"][term_name] = {
                        "categories": [{"name": c["name"], "score": None} for c in hidden_categories],
                        "total_grade": None,
                        "visibility": False,
                    }
            all_terms_visible = all(visibility_by_term.get(term.id, visibility_by_term.get(None, False)) for term in terms)
            if not all_terms_visible:
                data["final_grade"] = None

    return summary

def get_consolidated_student_grades(summary):
    """Return consolidated grades per student.

    Input is the mapping returned by get_student_activity_summary(), keyed by
    student name. Output is a list of dicts with:
      - student_name
      - student_id
      - terms: {term_name: total_grade}
      - final_grade
      - status: "PASSED" if final_grade >= 75, "FAILED" if < 75, None if grade is None
    This respects whatever visibility and remedial rules were already applied
    inside get_student_activity_summary().
    """
    results = []
    for student_name, data in summary.items():
        final_grade = data.get("final_grade")
        
        # Determine pass/fail status
        status = None
        if final_grade is not None:
            status = "PASSED" if final_grade >= 75 else "FAILED"
        
        entry = {
            "student_name": student_name,
            "email": data.get("email"),
            "student_id": data.get("student_id"),
            "terms": {},
            "final_grade": final_grade,
            "status": status,
        }

        term_grades = data.get("term_grades") or {}
        for term_name, term_data in term_grades.items():
            entry["terms"][term_name] = term_data.get("total_grade")

        results.append(entry)

    return results
