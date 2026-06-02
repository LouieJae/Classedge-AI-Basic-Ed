"""[Classedge LMS] Instructor grading surface views.

This module exposes the teacher-facing gradebook routes:
  * gradebook_home         — landing page with subject tiles
  * subject_gradebook      — per-subject grid (Task 7)
  * subject_gradebook_csv  — CSV export (Task 11)
  * grading_queue          — cross-subject needs-grading queue (Task 8)
  * grade_submission       — full-page Save & Next grading view (Task 9)
  * override_score         — manual override with audit (Task 10)
"""
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.db.models import Q
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods, require_POST

from activity.models.activity_model import Activity, ActivityQuestion
from activity.services.retake_resolver import select_canonical_details
from activity.models.student_activity_model import StudentActivity
from gradebookcomponent.services.access import authorize_subject_access, can_audit_all_gradebooks
from gradebookcomponent.services.csv_export import build_gradebook_csv
from gradebookcomponent.services.xlsx_export import build_gradebook_xlsx
from gradebookcomponent.services.override import apply_override
from gradebookcomponent.services.queue import (
    MANUAL_GRADE_TYPES,
    count_needs_grading_for_subject,
    get_needs_grading_for_teacher,
)
from subject.models import Subject


def _activity_quiz_type_name(activity):
    """[Classedge LMS] Return the quiz-type name for an activity via its first question.

    Activity has no `quiz_type` field; `quiz_type` lives on ActivityQuestion. We
    treat the first question's quiz_type as the activity's de-facto type for
    display / manual-grade classification in the grading queue.
    """
    q = (
        ActivityQuestion.objects.filter(activity=activity)
        .select_related("quiz_type")
        .first()
    )
    if q is None or q.quiz_type_id is None:
        return ""
    return q.quiz_type.name or ""


@permission_required('activity.view_studentactivity', raise_exception=True)
def gradebook_home(request):
    """[Classedge LMS] Gradebook landing page — subject tiles with pending-grading badges.

    Teachers see only the subjects they own or collaborate on. Audit roles
    (registrar / admin / program head / dean / superuser) see every subject
    so they can review grades school-wide.
    """
    if can_audit_all_gradebooks(request.user):
        subjects = Subject.objects.all().distinct()
    else:
        subjects = (
            Subject.objects.filter(
                Q(assign_teacher=request.user) | Q(collaborators=request.user)
            )
            .distinct()
        )
    # COIL/HALI courses follow their own program-level grading and aren't
    # part of the regular gradebook for any role.
    subjects = subjects.exclude(is_coil=True).exclude(is_hali=True)
    tiles = [
        {
            "subject": s,
            "pending": count_needs_grading_for_subject(request.user, s),
        }
        for s in subjects
    ]
    return render(
        request,
        "gradebookcomponent/gradebook_home.html",
        {
            "tiles": tiles,
            "is_auditor": can_audit_all_gradebooks(request.user),
        },
    )


@permission_required('activity.view_studentactivity', raise_exception=True)
def subject_gradebook(request, subject_id):
    """[Classedge LMS] Per-subject grid: students x activities with weighted subtotals.

    Term and final grades are sourced from `get_student_activity_summary` —
    the same helper that powers the `/api/student-assessment-summary/` endpoint
    — so the numbers shown here match the API contract exactly.
    """
    from accounts.models import CustomUser
    from activity.models.activity_model import Activity
    from activity.models.student_activity_model import StudentActivity
    from activity.utils.grade_calculation_utils import get_student_activity_summary
    from course.models import Attendance, Term

    subject = get_object_or_404(Subject, pk=subject_id)
    if subject.is_coil or subject.is_hali:
        messages.error(
            request,
            "COIL and HALI courses have their own grading flow and aren't part of the gradebook.",
        )
        return redirect("gradebook_home")
    authorize_subject_access(request.user, subject)

    activity_qs = (
        Activity.objects.filter(subject=subject, is_graded=True)
        .select_related("activity_type", "term")
        .order_by("start_time", "local_id")
    )
    activities = list(activity_qs)

    # Derive the semester from the subject's first graded activity. The API
    # endpoint takes semester+subject as inputs, so we mirror that scoping here.
    primary_term = activities[0].term if activities else None
    semester = primary_term.semester if primary_term else None
    terms = (
        list(Term.objects.filter(semester=semester).order_by("start_date"))
        if semester else []
    )

    student_ids = (
        StudentActivity.objects.filter(subject=subject)
        .values_list("student_id", flat=True)
        .distinct()
    )
    students = list(
        CustomUser.objects.filter(pk__in=student_ids).order_by(
            "last_name", "first_name"
        )
    )

    sa_rows = StudentActivity.objects.filter(
        subject=subject, student_id__in=student_ids
    ).select_related("activity")
    cells = {(sa.student_id, sa.activity_id): sa for sa in sa_rows}

    summary = {}
    if semester and terms:
        student_activities_qs = StudentActivity.objects.select_related(
            "activity", "activity__activity_type", "activity__subject", "term", "student__profile"
        ).filter(
            term__semester=semester,
            activity__subject=subject,
            activity__status=True,
        )
        attendance_qs = Attendance.objects.select_related("subject", "student").filter(
            subject=subject,
            graded=True,
            date__range=(semester.start_date, semester.end_date),
        )
        summary = get_student_activity_summary(
            semester, subject, terms, student_activities_qs, attendance_qs, request.user
        )

    rows = []
    for student in students:
        student_name = (
            f"{student.profile.first_name} {student.profile.last_name}"
            if hasattr(student, "profile") and student.profile and student.profile.first_name
            else None
        )
        data = summary.get(student_name) if student_name else None

        term_grades = []
        if data:
            for t in terms:
                tg = (data.get("term_grades") or {}).get(t.term_name) or {}
                term_grades.append({
                    "name": t.term_name,
                    "total": tg.get("total_grade"),
                })
        final = data.get("final_grade") if data else None

        row = {
            "student": student,
            "cells": [],
            "final": final,
            "term_grades": term_grades,
        }
        for activity in activities:
            sa = cells.get((student.id, activity.id))
            row["cells"].append({"activity": activity, "sa": sa})
        rows.append(row)

    return render(
        request,
        "gradebookcomponent/subject_gradebook.html",
        {
            "subject": subject,
            "term": primary_term,
            "terms": terms,
            "activities": activities,
            "rows": rows,
        },
    )


@permission_required('activity.view_studentactivity', raise_exception=True)
def subject_gradebook_csv(request, subject_id):
    """[Classedge LMS] Stream a CSV export of the subject's gradebook.

    Subject has no direct `term` field; we derive the term from the subject's
    first graded activity. Callers seeking a different term scope should use
    a per-term export (future work).
    """
    subject = get_object_or_404(Subject, pk=subject_id)
    if subject.is_coil or subject.is_hali:
        return HttpResponseForbidden(
            "COIL and HALI courses are not part of the regular gradebook export."
        )
    authorize_subject_access(request.user, subject)

    first_activity = (
        Activity.objects.filter(subject=subject, is_graded=True)
        .select_related("term")
        .order_by("start_time", "local_id")
        .first()
    )
    term = first_activity.term if first_activity else None
    term_slug = slugify(term.term_name) if term is not None else "all"
    filename = (
        f"gradebook_{slugify(subject.subject_name)}_{term_slug}_"
        f"{date.today().isoformat()}.csv"
    )
    response = StreamingHttpResponse(
        build_gradebook_csv(subject, term),
        content_type="text/csv; charset=utf-8",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@permission_required('activity.view_studentactivity', raise_exception=True)
def subject_gradebook_xlsx(request, subject_id):
    """[Classedge LMS] Per-subject gradebook as a styled .xlsx (class record)."""
    subject = get_object_or_404(Subject, pk=subject_id)
    if subject.is_coil or subject.is_hali:
        return HttpResponseForbidden(
            "COIL and HALI courses are not part of the regular gradebook export."
        )
    authorize_subject_access(request.user, subject)

    first_activity = (
        Activity.objects.filter(subject=subject, is_graded=True)
        .select_related("term")
        .order_by("start_time", "local_id")
        .first()
    )
    term = first_activity.term if first_activity else None
    term_slug = slugify(term.term_name) if term is not None else "all"
    filename = (
        f"gradebook_{slugify(subject.subject_name)}_{term_slug}_"
        f"{date.today().isoformat()}.xlsx"
    )
    buf = build_gradebook_xlsx(subject, term)
    response = HttpResponse(
        buf.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


QUEUE_PAGE_SIZE = 100


@permission_required('activity.change_studentactivity', raise_exception=True)
def grading_queue(request):
    """[Classedge LMS] Needs-grading queue across all subjects the teacher owns.

    Capped at QUEUE_PAGE_SIZE rows to bound memory on teachers with very large
    backlogs. A future enhancement can add pagination or filter chips.

    Optional `?activity=<local_id>` filters to a single activity (used by the
    "Grade Submissions" button on the assessment-detail page).
    """
    qs = get_needs_grading_for_teacher(request.user)
    activity_filter = request.GET.get('activity')
    filter_activity = None
    if activity_filter:
        qs = qs.filter(activity__local_id=activity_filter)
        from activity.models import Activity
        filter_activity = Activity.objects.filter(local_id=activity_filter).first()
    qs = qs[:QUEUE_PAGE_SIZE]
    rows = []
    for sa in qs:
        qt_name = _activity_quiz_type_name(sa.activity)
        rows.append({
            "sa": sa,
            "quiz_type_name": qt_name,
            "badge": "Needs grading" if qt_name in MANUAL_GRADE_TYPES else "Review auto-grade",
        })
    return render(request, "gradebookcomponent/grading_queue.html", {
        "rows": rows,
        "filter_activity": filter_activity,
    })


@permission_required('activity.change_studentactivity', raise_exception=True)
@require_http_methods(["GET", "POST"])
def grade_submission(request, student_activity_id):
    """[Classedge LMS] Full-page grading view with Save & Next progression."""
    sa = get_object_or_404(
        StudentActivity.objects.select_related("student", "activity__subject"),
        pk=student_activity_id,
    )
    authorize_subject_access(request.user, sa.activity.subject)

    if request.method == "POST":
        try:
            score = float(request.POST.get("score", ""))
        except (ValueError, TypeError):
            return HttpResponseBadRequest("Invalid score")
        if score < 0 or score > (sa.activity.max_score or 0):
            return HttpResponseBadRequest("Score out of range")
        sa.total_score = score
        sa.feedback = request.POST.get("feedback", "")
        sa.save(update_fields=["total_score", "feedback"])

        # Persist the teacher's grade onto the canonical attempt so the
        # per-attempt history (assessment-detail.html) reflects it instead
        # of showing the auto-grader's 0 for Essay/Document submissions.
        method = sa.activity.retake_method
        records = sa.retake_records.all()
        if records.exists():
            if method == "highest":
                canonical = records.order_by("-score", "-retake_time").first()
            elif method == "first":
                canonical = records.order_by("retake_time").first()
            else:  # latest / average
                canonical = records.order_by("-retake_time").first()
            if canonical and canonical.score != score:
                canonical.score = score
                canonical.save(update_fields=["score"])

        messages.success(
            request,
            f"Saved score {score:g} for {sa.student.get_full_name() or sa.student.username}.",
        )

        queue_url = f"{reverse('gradebook_queue')}?activity={sa.activity_id}"
        if request.POST.get("save_and_next"):
            next_sa = (
                get_needs_grading_for_teacher(request.user)
                .filter(activity_id=sa.activity_id)
                .exclude(pk=sa.pk).first()
            )
            if next_sa:
                return redirect("gradebook_grade", student_activity_id=next_sa.id)
            return redirect(queue_url)
        # Bare "Save" returns to the queue so the teacher sees the row drop off.
        return redirect(queue_url)

    answers = select_canonical_details(sa)
    next_sa = (
        get_needs_grading_for_teacher(request.user)
        .exclude(pk=sa.pk).first()
    )
    return render(
        request,
        "gradebookcomponent/grade_submission.html",
        {"sa": sa, "answers": answers, "has_next": bool(next_sa)},
    )


@permission_required('activity.change_studentactivity', raise_exception=True)
@require_POST
def override_score(request, student_activity_id):
    """[Classedge LMS] HTMX POST: override an auto-graded score; reason is required."""
    sa = get_object_or_404(
        StudentActivity.objects.select_related("activity__subject"),
        pk=student_activity_id,
    )
    authorize_subject_access(request.user, sa.activity.subject)

    reason = (request.POST.get("reason") or "").strip()
    if not reason:
        return HttpResponseBadRequest("Reason is required for overrides.")

    try:
        new_score = float(request.POST.get("new_score", ""))
    except (ValueError, TypeError):
        return HttpResponseBadRequest("Invalid score")
    if new_score < 0 or new_score > (sa.activity.max_score or 0):
        return HttpResponseBadRequest("Score out of range")

    apply_override(sa, new_score, reason, request.user)
    # HTMX requests get the cell fragment back; regular form submits get a
    # redirect to the subject gradebook so the teacher lands on the refreshed grid.
    if request.headers.get("HX-Request"):
        return HttpResponse(f'<span class="graded">{new_score}*</span>')
    return redirect("gradebook_subject", subject_id=sa.activity.subject_id)
