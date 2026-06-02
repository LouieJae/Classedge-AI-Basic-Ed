"""[Classedge LMS] Shared test helpers for gradebookcomponent tests."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.utils import timezone

from accounts.models import Profile
from activity.models.activity_model import (
    Activity, ActivityType, QuizType, ActivityQuestion, StudentQuestion,
)
from activity.models.student_activity_model import StudentActivity
from course.models import Semester, Term
from roles.models import Role
from subject.models import Subject

User = get_user_model()


# Permissions a Teacher needs for gradebookcomponent test views to render.
# Kept narrow on purpose — adding here triggers fewer 403s than granting
# is_staff or is_superuser, which would mask permission regressions.
TEACHER_PERMS = (
    ("gradebookcomponent", "view_gradebookcomponents"),
    ("gradebookcomponent", "add_gradebookcomponents"),
    ("gradebookcomponent", "change_gradebookcomponents"),
    ("gradebookcomponent", "delete_gradebookcomponents"),
    ("gradebookcomponent", "view_termgradebookcomponents"),
    ("activity", "view_studentactivity"),
    ("activity", "change_studentactivity"),
)


def _grant_perms(user, perms):
    for app_label, codename in perms:
        perm = Permission.objects.filter(
            content_type__app_label=app_label, codename=codename
        ).first()
        if perm:
            user.user_permissions.add(perm)


def make_user(email, role_name="Teacher"):
    """[Classedge LMS] Create a user with a Profile + Role for tests."""
    role, _ = Role.objects.get_or_create(name=role_name)
    user, _ = User.objects.get_or_create(
        username=email,
        defaults={"email": email},
    )
    if not user.has_usable_password():
        user.set_password("Test@1234")
        user.save()
    Profile.objects.update_or_create(user=user, defaults={"role": role})
    if role_name == "Teacher":
        _grant_perms(user, TEACHER_PERMS)
    return user


def make_semester(name="First Semester"):
    """[Classedge LMS] Create a Semester for tests. Uses valid choice values."""
    today = timezone.now().date()
    sem, _ = Semester.objects.get_or_create(
        semester_name=name,
        defaults={
            "start_date": today,
            "end_date": today.replace(year=today.year + 1),
        },
    )
    return sem


def make_term(name="Prelim", semester=None):
    """[Classedge LMS] Create a Semester + Term for tests. Uses valid Term choice."""
    semester = semester or make_semester()
    term, _ = Term.objects.get_or_create(
        term_name=name,
        semester=semester,
        defaults={"start_date": timezone.now().date()},
    )
    return term


def make_subject(teacher, name="Math 101", term=None):
    """[Classedge LMS] Create a Subject assigned to a teacher.

    Subject has no direct term field; the `term` parameter is stored on the
    subject object as a non-persistent attribute so callers (and helpers
    like make_activity) can reach back to a consistent term.
    """
    term = term or make_term()
    subject = Subject.objects.create(subject_name=name, assign_teacher=teacher)
    subject.term = term  # convenience attr for test helpers; not persisted
    return subject


def make_activity(subject, quiz_type_name="Essay", is_graded=True, max_score=10):
    """[Classedge LMS] Create an Activity plus an ActivityQuestion of the given QuizType.

    The real data model ties `quiz_type` to `ActivityQuestion`, not `Activity`.
    The helper therefore attaches a single ActivityQuestion with the chosen
    QuizType so downstream queries that filter by
    `activity__activityquestion__quiz_type__name` work as expected.
    """
    atype, _ = ActivityType.objects.get_or_create(name="Quiz")
    qtype, _ = QuizType.objects.get_or_create(name=quiz_type_name)
    term = getattr(subject, "term", None) or make_term()
    activity = Activity.objects.create(
        activity_name=f"{quiz_type_name} activity",
        activity_type=atype,
        subject=subject,
        term=term,
        is_graded=is_graded,
        max_score=max_score,
    )
    # Attach a question of the target quiz_type so queries can find it.
    ActivityQuestion.objects.create(
        activity=activity,
        subject=subject,
        question_text="Q1",
        correct_answer="A",
        quiz_type=qtype,
    )
    return activity


def make_submission(student, activity, answer_text="Answer", score=0):
    """Create a StudentActivity + RetakeRecord(retake_number=1) + one
    RetakeRecordDetail submission. RetakeRecordDetail is the canonical source
    of truth post-2026-05-18 port."""
    from activity.models import RetakeRecord, RetakeRecordDetail

    sa = StudentActivity.objects.create(
        student=student,
        activity=activity,
        subject=activity.subject,
        term=activity.term,
        total_score=score,
        is_editable=True,
    )
    question = ActivityQuestion.objects.filter(activity=activity).first()
    if question is None:
        question = ActivityQuestion.objects.create(
            activity=activity,
            subject=activity.subject,
            question_text="Q1",
            correct_answer="A",
        )
    rr = RetakeRecord.objects.create(
        student_activity=sa,
        student=student,
        activity=activity,
        retake_number=1,
        status="submitted",
        score=score,
    )
    RetakeRecordDetail.objects.create(
        retake_record=rr,
        student=student,
        activity_question=question,
        student_answer=answer_text,
        score=score,
        submission_time=timezone.now(),
    )
    return sa
