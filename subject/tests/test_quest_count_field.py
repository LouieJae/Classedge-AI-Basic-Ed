from django.test import TestCase
from subject.models import Subject


class QuestCountFieldTests(TestCase):
    def test_default_is_5(self):
        s = Subject.objects.create(subject_name="Math")
        self.assertEqual(s.quest_count_per_lesson, 5)

    def test_can_set_custom(self):
        s = Subject.objects.create(subject_name="Sci", quest_count_per_lesson=8)
        self.assertEqual(s.quest_count_per_lesson, 8)
