from django.test import TestCase
from gamification.templatetags.level_tier import level_tier


class LevelTierTests(TestCase):
    def test_level_one_has_no_tier(self):
        self.assertEqual(level_tier(1), 'none')

    def test_bronze_band(self):
        self.assertEqual(level_tier(2), 'bronze')
        self.assertEqual(level_tier(9), 'bronze')

    def test_silver_band(self):
        self.assertEqual(level_tier(10), 'silver')
        self.assertEqual(level_tier(19), 'silver')

    def test_gold_band(self):
        self.assertEqual(level_tier(20), 'gold')
        self.assertEqual(level_tier(29), 'gold')

    def test_platinum_band(self):
        self.assertEqual(level_tier(30), 'platinum')
        self.assertEqual(level_tier(49), 'platinum')

    def test_diamond_band(self):
        self.assertEqual(level_tier(50), 'diamond')
        self.assertEqual(level_tier(999), 'diamond')

    def test_zero_or_none_falls_back_to_none(self):
        self.assertEqual(level_tier(0), 'none')
        self.assertEqual(level_tier(None), 'none')
        self.assertEqual(level_tier('not-a-number'), 'none')
