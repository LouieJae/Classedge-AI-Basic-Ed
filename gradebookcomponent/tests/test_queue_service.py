"""[Classedge LMS] Tests for needs-grading queue service."""
from django.test import TestCase

from gradebookcomponent.services.queue import (
    count_needs_grading_for_subject,
    get_needs_grading_for_teacher,
)
from gradebookcomponent.tests.helpers import (
    make_activity,
    make_subject,
    make_submission,
    make_user,
)


class NeedsGradingQueueTest(TestCase):
    """[Classedge LMS] Covers manual-grade inclusion, auto-grade exclusion, flag rules, ownership, and counting."""

    def setUp(self):
        self.teacher = make_user("t@t.local", "Teacher")
        self.student = make_user("s@t.local", "Student")
        self.subject = make_subject(self.teacher)

    def test_essay_with_zero_score_included(self):
        activity = make_activity(self.subject, quiz_type_name="Essay")
        make_submission(self.student, activity, score=0)
        qs = list(get_needs_grading_for_teacher(self.teacher))
        self.assertEqual(len(qs), 1)

    def test_essay_with_nonzero_score_excluded(self):
        activity = make_activity(self.subject, quiz_type_name="Essay")
        make_submission(self.student, activity, score=5)
        self.assertEqual(list(get_needs_grading_for_teacher(self.teacher)), [])

    def test_multiple_choice_zero_not_flagged_without_answer(self):
        """[Classedge LMS] MCQ with zero total but empty answers is not in queue."""
        activity = make_activity(self.subject, quiz_type_name="Multiple Choice")
        make_submission(self.student, activity, score=0)
        from activity.models.activity_model import StudentQuestion

        StudentQuestion.objects.filter(
            student=self.student, activity=activity
        ).update(student_answer="")
        self.assertEqual(list(get_needs_grading_for_teacher(self.teacher)), [])

    def test_multiple_choice_zero_flagged_with_answer(self):
        """[Classedge LMS] MCQ with zero total AND non-empty answer → flagged as possibly-broken."""
        activity = make_activity(self.subject, quiz_type_name="Multiple Choice")
        make_submission(self.student, activity, score=0, answer_text="picked A")
        qs = list(get_needs_grading_for_teacher(self.teacher))
        self.assertEqual(len(qs), 1)

    def test_not_graded_activity_excluded(self):
        activity = make_activity(
            self.subject, quiz_type_name="Essay", is_graded=False
        )
        make_submission(self.student, activity, score=0)
        self.assertEqual(list(get_needs_grading_for_teacher(self.teacher)), [])

    def test_other_teachers_subject_excluded(self):
        other_teacher = make_user("o@t.local", "Teacher")
        other_subject = make_subject(other_teacher)
        activity = make_activity(other_subject, quiz_type_name="Essay")
        make_submission(self.student, activity, score=0)
        self.assertEqual(list(get_needs_grading_for_teacher(self.teacher)), [])

    def test_collaborator_sees_queue(self):
        collab = make_user("c@t.local", "Teacher")
        self.subject.collaborators.add(collab)
        activity = make_activity(self.subject, quiz_type_name="Essay")
        make_submission(self.student, activity, score=0)
        self.assertEqual(
            len(list(get_needs_grading_for_teacher(collab))), 1
        )

    def test_count_per_subject(self):
        a1 = make_activity(self.subject, quiz_type_name="Essay")
        a2 = make_activity(self.subject, quiz_type_name="Document")
        student2 = make_user("s2@t.local", "Student")
        make_submission(self.student, a1, score=0)
        make_submission(student2, a2, score=0)
        self.assertEqual(
            count_needs_grading_for_subject(self.teacher, self.subject), 2
        )
