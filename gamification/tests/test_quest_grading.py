from django.contrib.auth import get_user_model
from django.test import TestCase
from course.models.term_model import Term
from course.models.semester_model import Semester
from module.models.module import Module
from subject.models import Subject
from gamification.quest_models import Quest, QuestAttempt
from gamification.quest_grading import get_student_quest_score

User = get_user_model()


class QuestGradingTests(TestCase):
    def setUp(self):
        self.semester = Semester.objects.create(
            semester_name="First Semester", start_date="2024-01-01", end_date="2024-12-31"
        )
        self.subject = Subject.objects.create(subject_name="S")
        self.term = Term.objects.create(
            term_name="Prelim", semester=self.semester,
            start_date="2024-01-01", end_date="2024-03-31"
        )
        self.module = Module.objects.create(
            file_name="L", subject=self.subject, term=self.term
        )
        self.student = User.objects.create_user("s", password="x", email="s@example.com")

    def _q(self, order=1, status="published", grade=True):
        return Quest.objects.create(
            module=self.module, order=order, kind="quiz",
            title=f"t{order}", body="b", payload={},
            status=status, counts_toward_grade=grade,
        )

    def test_no_quests_returns_zero(self):
        self.assertEqual(get_student_quest_score(self.student, self.subject, self.term), 0.0)

    def test_unattempted_counts_as_zero(self):
        self._q()
        self.assertEqual(get_student_quest_score(self.student, self.subject, self.term), 0.0)

    def test_full_correct_returns_100(self):
        q = self._q()
        QuestAttempt.objects.create(quest=q, student=self.student, is_correct=True, score=1.0)
        self.assertEqual(get_student_quest_score(self.student, self.subject, self.term), 100.0)

    def test_partial_average(self):
        q1 = self._q(order=1)
        q2 = self._q(order=2)
        QuestAttempt.objects.create(quest=q1, student=self.student, is_correct=True, score=1.0)
        QuestAttempt.objects.create(quest=q2, student=self.student, is_correct=False, score=0.5)
        self.assertEqual(get_student_quest_score(self.student, self.subject, self.term), 75.0)

    def test_draft_excluded(self):
        q = self._q(status="draft")
        QuestAttempt.objects.create(quest=q, student=self.student, is_correct=True, score=1.0)
        self.assertEqual(get_student_quest_score(self.student, self.subject, self.term), 0.0)

    def test_counts_toward_grade_false_excluded(self):
        q = self._q(grade=False)
        QuestAttempt.objects.create(quest=q, student=self.student, is_correct=True, score=1.0)
        self.assertEqual(get_student_quest_score(self.student, self.subject, self.term), 0.0)

    def test_return_is_float_two_dp(self):
        q1 = self._q(order=1)
        q2 = self._q(order=2)
        q3 = self._q(order=3)
        QuestAttempt.objects.create(quest=q1, student=self.student, is_correct=True, score=1.0)
        result = get_student_quest_score(self.student, self.subject, self.term)
        self.assertIsInstance(result, float)
        self.assertEqual(result, 33.33)
