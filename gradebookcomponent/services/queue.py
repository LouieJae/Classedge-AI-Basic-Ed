"""[Classedge LMS] Needs-grading queue service.

Returns StudentActivity rows that need teacher attention. Only activities that
truly require manual grading — Essay and Document quiz types — are surfaced.
Auto-graded types (Multiple Choice, True/False, Fill in the Blank, Matching
Type, Calculated Numeric) and Participation / Direct Score are intentionally
excluded so the queue stays focused on submissions a teacher actually has to
read and score.

Note: `quiz_type` is modeled on `ActivityQuestion`, not `Activity`. We therefore
traverse `activity__activityquestion__quiz_type__name` and use DISTINCT to
deduplicate rows that may match multiple questions.
"""
from django.db.models import Exists, OuterRef, Q

from activity.models.activity_model import ActivityQuestion
from activity.models.retake_models import RetakeRecordDetail
from activity.models.student_activity_model import StudentActivity

MANUAL_GRADE_TYPES = ["Essay", "Document"]


def _base_queryset_for_teacher(user):
    """[Classedge LMS] StudentActivity filtered to subjects the teacher owns or collaborates on.

    COIL/HALI submissions are excluded — they live on their own
    program-level grading flow and shouldn't surface in the regular
    needs-grading queue.
    """
    return StudentActivity.objects.filter(
        Q(activity__subject__assign_teacher=user)
        | Q(activity__subject__collaborators=user),
        activity__is_graded=True,
    ).exclude(
        activity__subject__is_coil=True,
    ).exclude(
        activity__subject__is_hali=True,
    ).distinct()


def _manual_quiz_type_subquery():
    """[Classedge LMS] Exists() subquery: the activity has a question of a manual quiz type."""
    return ActivityQuestion.objects.filter(
        activity=OuterRef("activity"),
        quiz_type__name__in=MANUAL_GRADE_TYPES,
    )


def _any_quiz_type_subquery():
    """[Classedge LMS] Exists() subquery: the activity has any question with a quiz_type set."""
    return ActivityQuestion.objects.filter(
        activity=OuterRef("activity"),
        quiz_type__isnull=False,
    )


def get_needs_grading_for_teacher(user):
    """[Classedge LMS] Return StudentActivity queryset (oldest submission first) needing teacher attention.

    Only Essay/Document submissions are returned — auto-graded quiz types are
    excluded entirely from the queue.
    """
    submitted_subq = RetakeRecordDetail.objects.filter(
        student=OuterRef("student"),
        activity_question__activity=OuterRef("activity"),
        submission_time__isnull=False,
    )

    qs = (
        _base_queryset_for_teacher(user)
        .annotate(
            submitted=Exists(submitted_subq),
            is_manual=Exists(_manual_quiz_type_subquery()),
        )
        .filter(submitted=True, is_manual=True, total_score=0)
    )

    return (
        qs.select_related("student", "activity__subject", "activity__activity_type")
        .order_by("start_time", "local_id")
    )


def count_needs_grading_for_subject(user, subject):
    """[Classedge LMS] Count needs-grading submissions for one subject."""
    return (
        get_needs_grading_for_teacher(user)
        .filter(activity__subject=subject)
        .count()
    )
