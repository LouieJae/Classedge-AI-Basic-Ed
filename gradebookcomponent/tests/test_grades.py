"""[Classedge LMS] Tests for compute_weighted_grade service."""
from decimal import Decimal

from django.test import TestCase

from gradebookcomponent.models import ActivityTypePercentage, GradeBookComponents
from gradebookcomponent.services.grades import compute_weighted_grade
from gradebookcomponent.tests.helpers import (
    make_activity,
    make_subject,
    make_submission,
    make_user,
)


class ComputeWeightedGradeTest(TestCase):
    """[Classedge LMS] Validates parity with the existing studentTotalScore math."""

    def test_no_components_returns_zero(self):
        """[Classedge LMS] No gradebook components → weighted grade is 0.0."""
        teacher = make_user("t@t.local", "Teacher")
        student = make_user("s@t.local", "Student")
        subject = make_subject(teacher)
        result = compute_weighted_grade(student, subject, subject.term)
        self.assertEqual(result, 0.0)

    def test_single_activity_full_score(self):
        """[Classedge LMS] One 100%-weighted component + one full-score activity → 100.0."""
        teacher = make_user("t@t.local", "Teacher")
        student = make_user("s@t.local", "Student")
        subject = make_subject(teacher)
        activity = make_activity(subject, quiz_type_name="Essay", max_score=10)
        make_submission(student, activity, score=10)
        component = GradeBookComponents.objects.create(
            teacher=teacher,
            subject=subject,
            term=subject.term,
            gradebook_name="Exam",
            percentage=Decimal("100"),
        )
        ActivityTypePercentage.objects.create(
            gradebook_component=component,
            activity_type=activity.activity_type,
            percentage=Decimal("100"),
        )
        result = compute_weighted_grade(student, subject, subject.term)
        self.assertAlmostEqual(result, 100.0, places=1)
