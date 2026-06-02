# gradebookcomponent/tests/test_grades_quest_branch.py
from django.contrib.auth import get_user_model
from django.test import TestCase
from course.models.term_model import Term
from gradebookcomponent.models import GradeBookComponents
from gradebookcomponent.services.grades import compute_component_subtotal, compute_weighted_grade
from module.models.module import Module
from subject.models import Subject
from gamification.quest_models import Quest, QuestAttempt

User = get_user_model()


class GradesQuestBranchTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user("t", password="x", email="t@example.com")
        self.student = User.objects.create_user("s", password="x", email="s@example.com")
        self.subject = Subject.objects.create(subject_name="S")
        # Term has term_name field (and possibly other required fields); adjust as needed
        self.term = Term.objects.create(term_name="T")
        self.module = Module.objects.create(file_name="L", subject=self.subject, term=self.term)
        q = Quest.objects.create(module=self.module, order=1, kind="quiz", title="t", body="b",
                                 payload={}, status="published", counts_toward_grade=True)
        QuestAttempt.objects.create(quest=q, student=self.student, is_correct=True, score=1.0)
        self.component = GradeBookComponents.objects.create(
            teacher=self.teacher, subject=self.subject, term=self.term,
            gradebook_name="Quests", gradebook_category="quest_completion",
            percentage=20,
        )

    def test_subtotal_uses_quest_score(self):
        sub = compute_component_subtotal(self.student, self.subject, self.term, self.component)
        self.assertEqual(sub, 100.0)
        self.assertIsInstance(sub, float)

    def test_weighted_grade_applies_component_weight(self):
        grade = compute_weighted_grade(self.student, self.subject, self.term)
        self.assertEqual(grade, 20.0)  # 100 * 20% = 20
