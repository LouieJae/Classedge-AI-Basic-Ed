from django.core.management.base import BaseCommand

from gamification.side_activity_models import SideActivity
from subject.models import Subject

SAMPLE_ACTIVITIES = [
    {
        "sub_type": "daily_challenge",
        "title": "Daily Science Challenge",
        "xp_reward": 5,
        "estimated_minutes": 2,
        "content_json": {
            "question": "What is the chemical symbol for water?",
            "choices": ["H2O", "CO2", "NaCl", "O2"],
            "correct": 0,
        },
    },
    {
        "sub_type": "flashcard",
        "title": "Key Science Terms",
        "xp_reward": 5,
        "estimated_minutes": 3,
        "content_json": {
            "cards": [
                {"term": "Photosynthesis", "definition": "Process by which plants convert light energy into chemical energy"},
                {"term": "Mitosis", "definition": "Cell division producing two identical daughter cells"},
                {"term": "Atom", "definition": "The smallest unit of an element that retains its properties"},
                {"term": "Gravity", "definition": "A force that attracts objects with mass toward each other"},
                {"term": "Ecosystem", "definition": "A community of living organisms interacting with their environment"},
            ]
        },
    },
    {
        "sub_type": "speed_round",
        "title": "Quick Math Speed Round",
        "xp_reward": 10,
        "estimated_minutes": 1,
        "content_json": {
            "time_limit_seconds": 60,
            "questions": [
                {"question": "7 × 8 = ?", "choices": ["54", "56", "58", "64"], "correct": 1},
                {"question": "144 ÷ 12 = ?", "choices": ["10", "11", "12", "14"], "correct": 2},
                {"question": "25 + 37 = ?", "choices": ["52", "62", "72", "63"], "correct": 1},
                {"question": "100 − 47 = ?", "choices": ["43", "53", "57", "63"], "correct": 1},
                {"question": "9² = ?", "choices": ["72", "81", "90", "99"], "correct": 1},
            ],
        },
    },
    {
        "sub_type": "match_pair",
        "title": "Chemistry Formula Match",
        "xp_reward": 10,
        "estimated_minutes": 3,
        "content_json": {
            "pairs": [
                {"left": "NaCl", "right": "Sodium Chloride"},
                {"left": "H2SO4", "right": "Sulfuric Acid"},
                {"left": "CaCO3", "right": "Calcium Carbonate"},
                {"left": "NH3", "right": "Ammonia"},
                {"left": "CH4", "right": "Methane"},
            ]
        },
    },
    {
        "sub_type": "practice_quiz",
        "title": "General Science Practice",
        "xp_reward": 5,
        "estimated_minutes": 3,
        "content_json": {
            "questions": [
                {"question": "What planet is known as the Red Planet?", "choices": ["Venus", "Mars", "Jupiter", "Saturn"], "correct": 1},
                {"question": "What gas do plants absorb from the atmosphere?", "choices": ["Oxygen", "Nitrogen", "Carbon Dioxide", "Hydrogen"], "correct": 2},
                {"question": "What is the boiling point of water in Celsius?", "choices": ["90°C", "100°C", "110°C", "120°C"], "correct": 1},
            ],
        },
    },
    {
        "sub_type": "fill_blank",
        "title": "Biology Fill in the Blank",
        "xp_reward": 10,
        "estimated_minutes": 1,
        "content_json": {
            "sentence": "The process by which green plants make their own food using sunlight is called ____.",
            "answer": "photosynthesis",
            "accept": ["photosynthesis"],
        },
    },
    {
        "sub_type": "drag_order",
        "title": "Life Cycle Order",
        "xp_reward": 10,
        "estimated_minutes": 2,
        "content_json": {
            "instruction": "Arrange the butterfly life cycle in the correct order.",
            "items": ["Egg", "Larva (Caterpillar)", "Pupa (Chrysalis)", "Adult Butterfly"],
            "correct_order": [0, 1, 2, 3],
        },
    },
    {
        "sub_type": "word_scramble",
        "title": "Science Word Scramble",
        "xp_reward": 5,
        "estimated_minutes": 2,
        "content_json": {
            "words": [
                {"scrambled": "LCEULMO", "answer": "MOLECULE"},
                {"scrambled": "TOOMCYSE", "answer": "CYTOSME"},
            ]
        },
    },
    {
        "sub_type": "equation_balance",
        "title": "Balance: Hydrogen + Oxygen",
        "xp_reward": 15,
        "estimated_minutes": 2,
        "content_json": {
            "equation": "H2 + O2 → H2O",
            "balanced": "2H2 + O2 → 2H2O",
            "reactants": [{"formula": "H2", "coefficient": 2}, {"formula": "O2", "coefficient": 1}],
            "products": [{"formula": "H2O", "coefficient": 2}],
        },
    },
    {
        "sub_type": "math_drill",
        "title": "Arithmetic Drill",
        "xp_reward": 10,
        "estimated_minutes": 2,
        "content_json": {
            "time_limit_seconds": 120,
            "problems": [
                {"expression": "15 + 28", "answer": 43},
                {"expression": "64 - 37", "answer": 27},
                {"expression": "12 × 6", "answer": 72},
                {"expression": "96 ÷ 8", "answer": 12},
                {"expression": "23 + 49", "answer": 72},
            ],
        },
    },
    {
        "sub_type": "geo_map",
        "title": "Geography Map Challenge",
        "xp_reward": 10,
        "estimated_minutes": 3,
        "content_json": {
            "image_url": "/static/gamification/placeholder_map.png",
            "points": [
                {"label": "Sahara Desert", "x": 48, "y": 32},
                {"label": "Amazon Rainforest", "x": 28, "y": 55},
            ],
        },
    },
    {
        "sub_type": "timeline_sort",
        "title": "History Timeline Sort",
        "xp_reward": 10,
        "estimated_minutes": 2,
        "content_json": {
            "events": [
                {"event": "Invention of the Printing Press", "year": 1440},
                {"event": "Discovery of America", "year": 1492},
                {"event": "French Revolution", "year": 1789},
                {"event": "First Moon Landing", "year": 1969},
            ],
            "correct_order": [0, 1, 2, 3],
        },
    },
    {
        "sub_type": "code_kata",
        "title": "Simple Addition Function",
        "xp_reward": 15,
        "estimated_minutes": 3,
        "content_json": {
            "instruction": "Write a function called 'add' that takes two numbers and returns their sum.",
            "starter_code": "def add(a, b):\n    # your code here\n    pass",
            "test_cases": [
                {"input": [2, 3], "expected": 5},
                {"input": [-1, 1], "expected": 0},
                {"input": [0, 0], "expected": 0},
            ],
        },
    },
    {
        "sub_type": "typing_drill",
        "title": "Typing Speed Drill",
        "xp_reward": 5,
        "estimated_minutes": 1,
        "content_json": {
            "text": "The quick brown fox jumps over the lazy dog near the riverbank.",
        },
    },
    {
        "sub_type": "reading_mini",
        "title": "Mini Reading Comprehension",
        "xp_reward": 10,
        "estimated_minutes": 3,
        "content_json": {
            "passage": (
                "Water covers about 71% of the Earth's surface. Most of this water is found "
                "in oceans, which contain about 96.5% of all Earth's water. Only a small "
                "percentage exists as freshwater in rivers, lakes, and underground aquifers."
            ),
            "questions": [
                {
                    "question": "What percentage of Earth's surface is covered by water?",
                    "choices": ["51%", "61%", "71%", "81%"],
                    "correct": 2,
                },
            ],
        },
    },
]


class Command(BaseCommand):
    help = "Seed sample side activities for every subject in the database."

    def handle(self, *args, **options):
        subjects = Subject.objects.all()
        if not subjects.exists():
            self.stdout.write(self.style.WARNING("No subjects found. Skipping."))
            return

        created_count = 0
        for subject in subjects:
            for data in SAMPLE_ACTIVITIES:
                _, created = SideActivity.objects.get_or_create(
                    subject=subject,
                    sub_type=data["sub_type"],
                    title=data["title"],
                    defaults={
                        "content_json": data["content_json"],
                        "xp_reward": data["xp_reward"],
                        "estimated_minutes": data["estimated_minutes"],
                    },
                )
                if created:
                    created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created {created_count} side activities across {subjects.count()} subjects."
            )
        )
