"""Canonical badge catalog.

Single source of truth for every badge definition shipped with the system.
Imported by both the seed data migration (0007) and the post_migrate signal
in ``apps.py`` so a fresh DB — even after a full migration reset — comes up
with the catalog populated.

Each row: (code, name, description, tier, icon, criteria_json, family, family_rank).
"""

STUDENT_BADGES = [
    ("first_steps",    "First Steps",          "Complete your first graded activity.",             "bronze",   "👣", {"type": "activity_score", "min_pct": 1,   "count": 1},  "", 0),
    ("quick_learner",  "Quick Learner",        "Score 90% or higher on 3 activities.",             "silver",   "⚡", {"type": "activity_score", "min_pct": 90,  "count": 3},  "", 0),
    ("perfectionist",  "Perfectionist",        "Score a perfect 100% on any activity.",            "gold",     "💯", {"type": "activity_score", "min_pct": 100, "count": 1},  "", 0),
    ("top_of_class",   "Top of Class",         "Be the top scorer on 5 activities in one subject.","platinum", "👑", {"type": "top_scorer",     "threshold": 5},             "", 0),
    ("scholar_bronze", "Scholar — Apprentice", "Score 75% or higher on 5 activities.",             "bronze",   "📖", {"type": "activity_score", "min_pct": 75,  "count": 5},  "scholar", 1),
    ("scholar_silver", "Scholar — Adept",      "Score 75% or higher on 15 activities.",            "silver",   "📚", {"type": "activity_score", "min_pct": 75,  "count": 15}, "scholar", 2),
    ("scholar_gold",   "Scholar — Master",     "Score 75% or higher on 30 activities.",            "gold",     "🎓", {"type": "activity_score", "min_pct": 75,  "count": 30}, "scholar", 3),
    ("streak_bronze",  "Streak — Spark",       "Maintain a 3-day login streak.",                   "bronze",   "🔥", {"type": "streak", "streak": "login", "threshold": 3},   "streak",  1),
    ("streak_silver",  "Streak — Blaze",       "Maintain a 7-day login streak.",                   "silver",   "🌋", {"type": "streak", "streak": "login", "threshold": 7},   "streak",  2),
    ("streak_gold",    "Streak — Inferno",     "Maintain a 30-day login streak.",                  "gold",     "☄️", {"type": "streak", "streak": "login", "threshold": 30},  "streak",  3),
]

STAFF_BADGES = [
    ("staff_welcome",          "Welcome Aboard",       "Sign in to ClassEdge for the first time.",     "bronze",   "👋", {"type": "first_sign_in"},                       "", 0),
    ("staff_profile_complete", "Profile Complete",     "Fill in your full name and email.",            "bronze",   "🪪", {"type": "profile_complete"},                    "", 0),
    ("staff_active_week",      "Currently Active",     "Signed in within the last 7 days.",            "bronze",   "🔆", {"type": "recently_active", "within_days": 7},   "", 0),
    ("staff_active_month",     "Engaged",              "Signed in within the last 30 days.",           "silver",   "🌟", {"type": "recently_active", "within_days": 30},  "", 0),
    ("staff_role_admin",       "System Operator",      "Hold administrator privileges.",               "gold",     "⚙️", {"type": "role_admin"},                          "", 0),
    ("staff_tenured_30",       "Tenure — Month One",   "Account active for 30 days.",                  "bronze",   "📅", {"type": "tenure_days", "threshold": 30},        "staff_tenure", 1),
    ("staff_tenured_90",       "Tenure — Quarter",     "Account active for 90 days.",                  "silver",   "📆", {"type": "tenure_days", "threshold": 90},        "staff_tenure", 2),
    ("staff_tenured_180",      "Tenure — Half Year",   "Account active for 180 days.",                 "gold",     "🗓️", {"type": "tenure_days", "threshold": 180},       "staff_tenure", 3),
    ("staff_tenured_365",      "Tenure — Anniversary", "Account active for 365 days.",                 "platinum", "🏛️", {"type": "tenure_days", "threshold": 365},       "staff_tenure", 4),
]

TEACHER_BADGES = [
    ("first_impact",         "First Impact",           "Earn your first 10 Impact Points.",            "bronze",   "⚡",  {"type": "teacher_ip_total",          "threshold": 10},                       "", 0),
    ("class_champion",       "Class Champion",         "Achieve 85%+ class average in 3 subjects.",    "gold",     "🏆", {"type": "teacher_class_avg",         "threshold": 85, "count": 3},          "", 0),
    ("student_favorite",     "Student Favorite",       "4.5★+ average with at least 10 ratings.",      "gold",     "⭐", {"type": "teacher_star_avg",          "min_avg": 4.5, "min_ratings": 10},     "", 0),
    ("legendary_educator",   "Legendary Educator",     "Reach the Platinum Legend rank.",              "platinum", "👑", {"type": "teacher_rank",              "rank": "platinum_legend"},             "", 0),
    ("badge_bestower",       "Badge Bestower",         "Manually award 25 badges to students.",        "gold",     "🎖️", {"type": "teacher_manual_awards",     "threshold": 25},                       "", 0),
    ("grading_bronze",       "Grading — Steady",       "Grade 50 activities on time.",                 "bronze",   "📝", {"type": "teacher_grading_count",     "threshold": 50},                       "grading", 1),
    ("grading_silver",       "Grading — Tireless",     "Grade 200 activities on time.",                "silver",   "📋", {"type": "teacher_grading_count",     "threshold": 200},                      "grading", 2),
    ("grading_gold",         "Grading — Machine",      "Grade 500 activities on time.",                "gold",     "🏅", {"type": "teacher_grading_count",     "threshold": 500},                      "grading", 3),
    ("mentors_touch_bronze", "Mentor's Touch — Kind",  "Send 20 recognition shoutouts.",               "bronze",   "🤝", {"type": "teacher_recognition_count", "threshold": 20},                       "mentors_touch", 1),
    ("mentors_touch_silver", "Mentor's Touch — Caring","Send 50 recognition shoutouts.",               "silver",   "💌", {"type": "teacher_recognition_count", "threshold": 50},                       "mentors_touch", 2),
]


def seed_catalog(get_model):
    """Upsert every badge definition. ``get_model`` is either Django's app
    registry ``apps.get_model`` (real or historical) so this works from both
    a data migration and a post_migrate signal handler.
    """
    BadgeDefinition = get_model("gamification", "BadgeDefinition")
    TeacherBadgeDefinition = get_model("gamification", "TeacherBadgeDefinition")

    def _upsert(model, rows, target_role=None):
        for code, name, desc, tier, icon, criteria, family, family_rank in rows:
            defaults = {
                "name": name, "description": desc, "tier": tier, "icon": icon,
                "criteria_json": criteria, "family": family,
                "family_rank": family_rank, "is_active": True,
            }
            if target_role is not None:
                defaults["target_role"] = target_role
            model.objects.update_or_create(code=code, defaults=defaults)

    _upsert(BadgeDefinition, STUDENT_BADGES, target_role="student")
    _upsert(BadgeDefinition, STAFF_BADGES, target_role="staff")
    _upsert(TeacherBadgeDefinition, TEACHER_BADGES)


def all_codes():
    return {
        "student": [r[0] for r in STUDENT_BADGES],
        "staff":   [r[0] for r in STAFF_BADGES],
        "teacher": [r[0] for r in TEACHER_BADGES],
    }
