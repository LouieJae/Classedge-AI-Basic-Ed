from django.core.management.base import BaseCommand
from gamification.teacher_models import TeacherBadgeDefinition

# Each entry includes `family` + `family_rank` so tiered badges (Grading,
# Mentor's Touch, IP Collector) can be grouped in the UI and shown as a single
# upgrading slot.
BADGES = [
    # Singles
    {"code": "first_impact",        "name": "First Impact",        "description": "Earn your first 10 Impact Points.",        "tier": "bronze",   "icon": "⚡",  "criteria_json": {"type": "teacher_ip_total", "threshold": 10},                  "family": "", "family_rank": 0},
    {"code": "class_champion",      "name": "Class Champion",      "description": "Achieve 85%+ class average in 3 subjects.","tier": "gold",     "icon": "🏆", "criteria_json": {"type": "teacher_class_avg", "threshold": 85, "count": 3},     "family": "", "family_rank": 0},
    {"code": "student_favorite",    "name": "Student Favorite",    "description": "4.5★+ average with at least 10 ratings.",  "tier": "gold",     "icon": "⭐", "criteria_json": {"type": "teacher_star_avg", "min_avg": 4.5, "min_ratings": 10},"family": "", "family_rank": 0},
    {"code": "legendary_educator",  "name": "Legendary Educator",  "description": "Reach the Platinum Legend rank.",          "tier": "platinum", "icon": "👑", "criteria_json": {"type": "teacher_rank", "rank": "platinum_legend"},            "family": "", "family_rank": 0},
    {"code": "badge_bestower",      "name": "Badge Bestower",      "description": "Manually award 25 badges to students.",    "tier": "gold",     "icon": "🎖️", "criteria_json": {"type": "teacher_manual_awards", "threshold": 25},             "family": "", "family_rank": 0},

    # Grading family
    {"code": "grading_bronze",      "name": "Grading — Steady",    "description": "Grade 50 activities on time.",             "tier": "bronze",   "icon": "📝", "criteria_json": {"type": "teacher_grading_count", "threshold": 50},             "family": "grading", "family_rank": 1},
    {"code": "grading_silver",      "name": "Grading — Tireless",  "description": "Grade 200 activities on time.",            "tier": "silver",   "icon": "📋", "criteria_json": {"type": "teacher_grading_count", "threshold": 200},            "family": "grading", "family_rank": 2},
    {"code": "grading_gold",        "name": "Grading — Machine",   "description": "Grade 500 activities on time.",            "tier": "gold",     "icon": "🏅", "criteria_json": {"type": "teacher_grading_count", "threshold": 500},            "family": "grading", "family_rank": 3},

    # Mentor's Touch family
    {"code": "mentors_touch_bronze","name": "Mentor's Touch — Kind","description": "Send 20 recognition shoutouts.",          "tier": "bronze",   "icon": "🤝", "criteria_json": {"type": "teacher_recognition_count", "threshold": 20},         "family": "mentors_touch", "family_rank": 1},
    {"code": "mentors_touch_silver","name": "Mentor's Touch — Caring","description": "Send 50 recognition shoutouts.",        "tier": "silver",   "icon": "💌", "criteria_json": {"type": "teacher_recognition_count", "threshold": 50},         "family": "mentors_touch", "family_rank": 2},
]


class Command(BaseCommand):
    help = "Seed the teacher badge definitions (10 total, including tiered families)."

    def handle(self, *args, **options):
        active_codes = {b["code"] for b in BADGES}
        removed = TeacherBadgeDefinition.objects.exclude(code__in=active_codes).delete()[0]
        created_count = 0
        updated_count = 0
        for badge_data in BADGES:
            obj, created = TeacherBadgeDefinition.objects.get_or_create(
                code=badge_data["code"], defaults=badge_data,
            )
            if created:
                created_count += 1
                continue
            changed = False
            for field, value in badge_data.items():
                if getattr(obj, field) != value:
                    setattr(obj, field, value)
                    changed = True
            if changed:
                obj.save()
                updated_count += 1
        self.stdout.write(
            f"Teacher badges: {created_count} created, {updated_count} updated, "
            f"{removed} removed, {len(BADGES) - created_count - updated_count} unchanged."
        )
