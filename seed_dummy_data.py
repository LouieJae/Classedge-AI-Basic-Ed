"""
seed_dummy_data.py
==================

Idempotent dummy-data loader for ClassEdge-AI.

Run from the project root with the virtualenv active:

    python seed_dummy_data.py

This seeds a Philippine K-12 (DepEd) Grade 7 demo: one "Grade 7 - Rizal"
section, the 8 core subjects, four grading quarters, and DepEd-style
assessment components (Written Work / Performance Task / Quarterly Assessment).

What it creates (or reuses if already present):
  - Roles: Student, Teacher, Admin, Registrar, Academic Director, Program Head, Time Keeper
  - 1 Department (Junior High School) + 1 Course (Grade 7 - Rizal)
  - 4 teacher users + 14 student users + 1 demo per staff role
  - Profile rows for each user
  - Friend relationships (a network among the students)
  - 1-on-1 Chat messages between several pairs
  - 1 Group chat with members + a few group messages
  - A handful of social-media Posts with likes/comments
  - Subjects, enrollments, lessons, activities, grades, attendance,
    calendar entries, gamification, and the Quest Map

Login credentials for the demo accounts (the login form expects EMAIL):
    demo@basiced.dev        / demo123        (Student)
    teacher@basiced.dev     / teacher123     (Teacher)
    (all other seeded users use password: classedge123 — see the Users
     section below for the email of each account.)

Re-running the script is safe: every object is fetched-or-created; chat /
post seeding is skipped if data already exists for that user.
"""

from __future__ import annotations

import os
import random
import sys
import traceback
from datetime import date, datetime, time, timedelta

import django

# ---------------------------------------------------------------------------
# Bootstrap Django so we can use the ORM from a standalone script.
# ---------------------------------------------------------------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lms.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.db import connection, transaction  # noqa: E402
from django.db.models import Q  # noqa: E402
from django.utils import timezone  # noqa: E402

# Allow concurrent runs alongside `manage.py runserver` (SQLite locks).
# busy_timeout=30s tells SQLite to wait instead of immediately raising.
if connection.vendor == "sqlite":
    with connection.cursor() as _c:
        _c.execute("PRAGMA busy_timeout = 30000;")

# Suppress per-row OneSignal push notifications during seeding.
# Module.save() and Activity.save() each trigger an HTTP request to OneSignal
# for every enrolled student, which adds minutes per subject and holds the
# SQLite lock while it waits on the network. We replace the helpers with
# no-ops just for this script.
try:
    import logs.utils as _logs_utils  # noqa: E402

    _logs_utils.create_notification_for_teacher = lambda *a, **kw: None
    _logs_utils.create_notifications_for_subject_students = lambda *a, **kw: None
except Exception:
    pass

from accounts.models.account_models import Profile  # noqa: E402
from accounts.models.course_models import Course  # noqa: E402
from accounts.models.department_models import Department  # noqa: E402
from roles.models import Role  # noqa: E402
from social_media.models import (  # noqa: E402
    Chat,
    Comment,
    Friend,
    GroupChat,
    GroupMessage,
    Like,
    Post,
)

# ---------------------------------------------------------------------------
# Optional model imports — wrapped so a missing app doesn't kill the seeder.
# Each block sets the names to None when the import fails.
# ---------------------------------------------------------------------------
try:
    from subject.models import Subject  # noqa: E402
except Exception:
    Subject = None

try:
    from course.models import (  # noqa: E402
        Semester,
        StudentParticipationScore,
        SubjectEnrollment,
        Term,
    )
except Exception:
    Semester = Term = SubjectEnrollment = StudentParticipationScore = None

try:
    from activity.models import (  # noqa: E402
        Activity,
        ActivityQuestion,
        ActivityType,
        QuestionChoice,
        QuizType,
        StudentActivity,
    )
except Exception:
    Activity = ActivityType = StudentActivity = None
    ActivityQuestion = QuestionChoice = QuizType = None

try:
    from module.models.module import Module  # noqa: E402
except Exception:
    Module = None

try:
    from course.models.attendance_model import (  # noqa: E402
        Attendance,
        AttendanceStatus,
        TeacherAttendancePoints,
    )
except Exception:
    Attendance = AttendanceStatus = TeacherAttendancePoints = None

try:
    from gradebookcomponent.models.gradebook_model import (  # noqa: E402
        ActivityTypePercentage,
        GradeBookComponents,
    )
    from gradebookcomponent.models.termbook_model import (
        TermGradeBookComponents,  # noqa: E402
    )
except Exception:
    GradeBookComponents = ActivityTypePercentage = TermGradeBookComponents = None

try:
    from calendars.models import Announcement, Event, Holiday  # noqa: E402
except Exception:
    Holiday = Event = Announcement = None

try:
    from gamification.models import (  # noqa: E402
        BadgeDefinition,
        StudentBadge,
        StudentGamification,
        XPTransaction,
    )
except Exception:
    StudentGamification = XPTransaction = BadgeDefinition = StudentBadge = None

try:
    from gamification.side_activity_models import (  # noqa: E402
        SideActivity,
        SideActivityAttempt,
    )
except Exception:
    SideActivity = SideActivityAttempt = None

try:
    from logs.models import Notification, StudentActivityLog  # noqa: E402
except Exception:
    StudentActivityLog = Notification = None

User = get_user_model()
DEFAULT_PASSWORD = "classedge123"


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------
def log(section: str, msg: str) -> None:
    print(f"  [{section}] {msg}")


def header(title: str) -> None:
    print(f"\n=== {title} ===")


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------
ROLE_NAMES = [
    "Student",
    "Teacher",
    "Admin",
    "Registrar",
    # NOTE: "Academic Director" and "Program Head" are kept because the app's
    # role-gating logic (CustomUser.is_academic_director / is_program_head, and
    # the views behind them) keys on these exact names. In a Basic-Ed context
    # think of them as "Principal" and "Grade Level Coordinator" — you can
    # relabel them in the admin once equivalent gating exists.
    "Academic Director",
    "Program Head",
    "Time Keeper",
]

STUDENTS = [
    # A single Grade 7 section ("Grade 7 - Rizal"). username, first, last, email
    ("alex_cruz", "Alex", "Cruz", "alex@basiced.dev"),
    ("bea_santos", "Bea", "Santos", "bea@basiced.dev"),
    ("carlo_reyes", "Carlo", "Reyes", "carlo@basiced.dev"),
    ("diane_lim", "Diane", "Lim", "diane@basiced.dev"),
    ("ej_garcia", "EJ", "Garcia", "ej@basiced.dev"),
    ("faye_torres", "Faye", "Torres", "faye@basiced.dev"),
    ("gio_mendoza", "Gio", "Mendoza", "gio@basiced.dev"),
    ("hana_dela_cruz", "Hana", "Dela Cruz", "hana@basiced.dev"),
    ("ivan_chua", "Ivan", "Chua", "ivan@basiced.dev"),
    ("jen_villanueva", "Jen", "Villanueva", "jen@basiced.dev"),
    # The two below are NOT auto-friended with demo_student — they will
    # appear in the Requests tab (pending) and Discover tab respectively.
    ("kara_lopez", "Kara", "Lopez", "kara@basiced.dev"),
    ("leo_pineda", "Leo", "Pineda", "leo@basiced.dev"),
    ("mia_robles", "Mia", "Robles", "mia@basiced.dev"),
    ("nico_tan", "Nico", "Tan", "nico@basiced.dev"),
]

TEACHERS = [
    ("teacher_navarro", "Liza", "Navarro", "navarro@basiced.dev"),
    ("teacher_aquino", "Mario", "Aquino", "aquino@basiced.dev"),
    ("teacher_delacruz", "Grace", "Dela Cruz", "gdelacruz@basiced.dev"),
    ("teacher_ramos", "Ben", "Ramos", "bramos@basiced.dev"),
]

DEMO_STUDENT = ("demo_student", "Demo", "Student", "demo@basiced.dev", "demo123")
DEMO_TEACHER = ("demo_teacher", "Demo", "Teacher", "teacher@basiced.dev", "teacher123")

# One demo account per non-student/non-teacher role. Login with email + password.
# Person names use Basic-Ed labels (Principal / Coordinator) even though the
# underlying functional role name is what the app gates on.
# Tuple shape: (role_name, username, first, last, email, password)
ROLE_DEMOS = [
    ("Admin", "demo_admin", "Demo", "Admin", "admin@basiced.dev", "admin123"),
    (
        "Registrar",
        "demo_registrar",
        "Demo",
        "Registrar",
        "registrar@basiced.dev",
        "registrar123",
    ),
    (
        "Academic Director",
        "demo_principal",
        "Demo",
        "Principal",
        "principal@basiced.dev",
        "principal123",
    ),
    (
        "Program Head",
        "demo_coordinator",
        "Demo",
        "Coordinator",
        "coordinator@basiced.dev",
        "coordinator123",
    ),
    (
        "Time Keeper",
        "demo_timekeeper",
        "Demo",
        "Keeper",
        "timekeeper@basiced.dev",
        "keeper123",
    ),
]

CHAT_SCRIPTS = [
    # pair = (username_a, username_b), turns alternate starting with a
    (
        ("demo_student", "alex_cruz"),
        [
            "Hey Alex! Did you finish our Math 7 seatwork?",
            "Almost done — stuck on the last word problem. You?",
            "Same here haha. Want to review together at recess?",
            "Sure, see you at the canteen.",
            "Cool, see you!",
        ],
    ),
    (
        ("demo_student", "bea_santos"),
        [
            "Bea, are we still meeting at the library?",
            "Yes! 4pm sharp. Bring the Science project draft.",
            "Got it. I'll bring baon too 😄",
            "You're the best.",
        ],
    ),
    (
        ("demo_student", "carlo_reyes"),
        [
            "Carlo, did our group submit the Araling Panlipunan report?",
            "Just uploaded the file. Check the group chat.",
            "Awesome, thanks!",
        ],
    ),
    (
        ("alex_cruz", "bea_santos"),
        [
            "Bea, did you get the notes from Teacher Navarro?",
            "Yep, I'll send a copy later.",
            "Thanks 🙏",
        ],
    ),
    (
        ("ej_garcia", "demo_student"),
        [
            "Are you joining the review session tonight?",
            "Yes, what time?",
            "7pm, on Messenger. I'll send the link.",
        ],
    ),
    # ── demo_teacher conversations (so the demo Faculty inbox has data) ──
    (
        ("demo_teacher", "alex_cruz"),
        [
            "Hi Alex — your Written Work 1 was very neat. Keep it up!",
            "Thank you, Sir! I studied hard for it.",
            "If you have time, try the enrichment activity in Lesson 3.",
            "Opo, Sir. Will submit by Friday.",
        ],
    ),
    (
        ("demo_teacher", "bea_santos"),
        [
            "Bea, I noticed you were absent today. Everything okay?",
            "Yes Sir, I had a check-up. I'll catch up tonight.",
            "Got it. Let me know if you need help with the recap activity.",
            "Thank you po, will message if I get stuck.",
        ],
    ),
    (
        ("demo_teacher", "carlo_reyes"),
        [
            "Carlo, please pass your Performance Task portfolio by Monday.",
            "Sure, Sir. I'll submit the draft tomorrow.",
            "Great. Make sure to follow the rubric this time.",
        ],
    ),
    (
        ("demo_teacher", "diane_lim"),
        [
            "Hi Diane — want to be a peer tutor for next week's Math drill?",
            "Yes, I'd love to!",
            "Perfect. I'll add you to the helpers list.",
        ],
    ),
    (
        ("ej_garcia", "demo_teacher"),
        [
            "Sir, could I get a 1-day extension for the assignment?",
            "Sure, just submit by Saturday 11:59 PM.",
            "Salamat po, Sir!",
        ],
    ),
]

POSTS = [
    ("alex_cruz", "Just passed my Math 7 seatwork 📚 finally free!"),
    ("bea_santos", "Library is packed today. Wish me luck sa quiz 😅"),
    (
        "carlo_reyes",
        "Group meeting for our Science project at 4pm — don't be late team!",
    ),
    ("demo_student", "Hello classmates! Excited for our new online classroom 🎉"),
    ("hana_dela_cruz", "Anyone has notes for Science 7? Drop a comment 🙏"),
]

# ---------------------------------------------------------------------------
# Academic structure
# ---------------------------------------------------------------------------
# DepEd-style assessment components.
ACTIVITY_TYPES = [
    "Written Work",
    "Performance Task",
    "Quarterly Assessment",
    "Recitation",
    "Project",
]

# Basic-Ed uses four grading quarters.
TERM_NAMES = ["First Quarter", "Second Quarter", "Third Quarter", "Fourth Quarter"]

# Grade 7 core subjects (Philippine K-12 / DepEd Junior High School curriculum).
# (code, name, short, description, teacher_username, units)
# demo_teacher handles English 7 + Mathematics 7 so the demo Faculty Dashboard has data.
SUBJECTS = [
    (
        "ENG7",
        "English 7",
        "English",
        "Reading, grammar, and literature for Grade 7.",
        "demo_teacher",
        1,
    ),
    (
        "FIL7",
        "Filipino 7",
        "Filipino",
        "Wika, panitikan, at gramatika para sa Baitang 7.",
        "teacher_navarro",
        1,
    ),
    (
        "MATH7",
        "Mathematics 7",
        "Math",
        "Numbers, measurement, algebra, and geometry.",
        "demo_teacher",
        1,
    ),
    (
        "SCI7",
        "Science 7",
        "Science",
        "Matter, living things, force, motion, and energy.",
        "teacher_aquino",
        1,
    ),
    (
        "AP7",
        "Araling Panlipunan 7",
        "AP",
        "Heograpiya at kasaysayan ng Asya.",
        "teacher_delacruz",
        1,
    ),
    (
        "ESP7",
        "Edukasyon sa Pagpapakatao 7",
        "ESP",
        "Values formation at pagpapakatao para sa Baitang 7.",
        "teacher_navarro",
        1,
    ),
    (
        "MAPEH7",
        "MAPEH 7",
        "MAPEH",
        "Music, Arts, Physical Education, and Health.",
        "teacher_ramos",
        1,
    ),
    (
        "TLE7",
        "Technology and Livelihood Education 7",
        "TLE",
        "ICT, home economics, and basic livelihood skills.",
        "teacher_aquino",
        1,
    ),
]

# Activities per subject — (name, type, days_relative_to_today, max_score)
SUBJECT_ACTIVITIES = [
    ("Written Work 1: Vocabulary & Concepts", "Written Work", -20, 20),
    ("Performance Task 1: Group Presentation", "Performance Task", -10, 50),
    ("Quarterly Assessment", "Quarterly Assessment", 5, 50),
    ("Project: Learning Portfolio", "Project", 14, 100),
    ("Recitation: Class Participation", "Recitation", -5, 20),
]

# Philippine 2025 holidays (regular + special)
HOLIDAYS = [
    ("New Year's Day", date(2025, 1, 1), "Regular Holiday", "#E74C3C"),
    ("Araw ng Kagitingan", date(2025, 4, 9), "Regular Holiday", "#E74C3C"),
    ("Maundy Thursday", date(2025, 4, 17), "Regular Holiday", "#9B59B6"),
    ("Good Friday", date(2025, 4, 18), "Regular Holiday", "#9B59B6"),
    ("Labor Day", date(2025, 5, 1), "Regular Holiday", "#3498DB"),
    ("Independence Day", date(2025, 6, 12), "Regular Holiday", "#E74C3C"),
    ("Ninoy Aquino Day", date(2025, 8, 21), "Special Holiday", "#F39C12"),
    ("National Heroes Day", date(2025, 8, 25), "Regular Holiday", "#E74C3C"),
    ("All Saints' Day", date(2025, 11, 1), "Special Holiday", "#F39C12"),
    ("Bonifacio Day", date(2025, 11, 30), "Regular Holiday", "#E74C3C"),
    ("Christmas Day", date(2025, 12, 25), "Regular Holiday", "#27AE60"),
    ("Rizal Day", date(2025, 12, 30), "Regular Holiday", "#E74C3C"),
]

# (title, description, day-offset-from-today, time-or-None, location)
EVENTS = [
    (
        "Opening of Classes",
        "Welcome back, learners! First day of the school year.",
        -28,
        time(7, 30),
        "Covered Court",
    ),
    (
        "Buwan ng Wika Program",
        "Pagdiriwang ng Buwan ng Wikang Pambansa.",
        -7,
        time(13, 0),
        "School Gym",
    ),
    (
        "First Quarterly Exams",
        "Bring your school IDs. Check the schedule on the portal.",
        5,
        time(7, 30),
        "Classrooms",
    ),
    (
        "Science Fair",
        "Class science investigatory project exhibits.",
        12,
        time(9, 0),
        "Science Laboratory",
    ),
    (
        "Parent-Teacher Conference",
        "Distribution of report cards and learner progress updates.",
        18,
        time(8, 0),
        "Advisory Rooms",
    ),
    (
        "Second Quarterly Exams",
        "Second quarter assessment week — good luck!",
        35,
        time(7, 30),
        "Classrooms",
    ),
    (
        "Intramurals / Sports Fest",
        "Inter-section sports competitions and cheering.",
        45,
        time(8, 0),
        "School Grounds",
    ),
]

ANNOUNCEMENTS = [
    (
        "Enrollment Reminder",
        "Late enrollment deadline is approaching — please proceed to the Registrar's Office.",
    ),
    (
        "System Maintenance",
        "The portal will be down Saturday 11pm-1am for scheduled updates.",
    ),
    (
        "Library Hours Update",
        "The school library will be open until 5pm during exam weeks.",
    ),
    (
        "Nutrition Month Menu",
        "The canteen added healthier 'gulay' and fruit options starting Monday.",
    ),
    (
        "Wear Your Complete Uniform",
        "Reminder: wear the complete prescribed uniform and ID daily.",
    ),
    (
        "Faculty Meeting",
        "All advisers are invited to a meeting on the new grading sheet.",
    ),
    (
        "Brigada Eskwela",
        "Volunteers are welcome for this week's school clean-up drive.",
    ),
    (
        "Guidance Wellness Week",
        "Free counseling sessions and homeroom wellness activities next week.",
    ),
]

# Institution-wide news (department=None) so they appear for every user
# regardless of department assignment.
INSTITUTION_ANNOUNCEMENTS = [
    (
        "Academic Calendar Update",
        "Reminder: First Quarter exam week starts soon. Check your class schedule.",
    ),
    (
        "Supreme Pupil/Student Government Elections",
        "Filing of candidacy is open until next Friday.",
    ),
    (
        "Holiday Reminder",
        "Classes are suspended on the upcoming national holiday — see calendar.",
    ),
]
INSTITUTION_EVENTS = [
    (
        "Flag Ceremony",
        "Weekly Monday flag-raising for all learners and teachers.",
        -2,
        time(7, 15),
        "Quadrangle",
    ),
    (
        "Recognition Day",
        "Awarding of honor learners and achievers, open to parents.",
        22,
        time(8, 0),
        "Covered Court",
    ),
    (
        "Foundation Day",
        "Celebration of the school's founding anniversary.",
        28,
        time(8, 30),
        "School Grounds",
    ),
]

# Side activities (Quest Map). (sub_type, title, xp_reward, estimated_minutes)
SIDE_ACTIVITIES = [
    ("daily_challenge", "Daily Math Challenge", 15, 5),
    ("flashcard", "English Vocabulary Flashcards", 10, 3),
    ("daily_challenge", "Science Quick Quiz", 20, 7),
    ("flashcard", "Filipino Talasalitaan", 10, 4),
    ("daily_challenge", "Mental Math Speed Round", 25, 10),
]

# Badges — `icon` is rendered as plain text (template uses {{ icon }} not <i>),
# so we store an emoji rather than a FontAwesome class name.
# Each row: (code, name, desc, tier, icon, criteria_json, family, family_rank).
# `family` groups tiered badges; rows in the same family share a slug and the
# UI shows only the highest tier the student has earned plus progress toward
# the next. `family_rank` orders tiers within a family (1=lowest).
BADGES = [
    (
        "first_steps",
        "First Steps",
        "Complete your first graded activity.",
        "bronze",
        "👣",
        {"type": "activity_score", "min_pct": 1, "count": 1},
        "",
        0,
    ),
    (
        "quick_learner",
        "Quick Learner",
        "Score 90% or higher on 3 activities.",
        "silver",
        "⚡",
        {"type": "activity_score", "min_pct": 90, "count": 3},
        "",
        0,
    ),
    (
        "perfectionist",
        "Perfectionist",
        "Score a perfect 100% on any activity.",
        "gold",
        "💯",
        {"type": "activity_score", "min_pct": 100, "count": 1},
        "",
        0,
    ),
    (
        "top_of_class",
        "Top of Class",
        "Be the top scorer on 5 activities in one subject.",
        "platinum",
        "👑",
        {"type": "top_scorer", "threshold": 5},
        "",
        0,
    ),
    # Scholar family — score 75%+ on more and more activities
    (
        "scholar_bronze",
        "Scholar — Apprentice",
        "Score 75% or higher on 5 activities.",
        "bronze",
        "📖",
        {"type": "activity_score", "min_pct": 75, "count": 5},
        "scholar",
        1,
    ),
    (
        "scholar_silver",
        "Scholar — Adept",
        "Score 75% or higher on 15 activities.",
        "silver",
        "📚",
        {"type": "activity_score", "min_pct": 75, "count": 15},
        "scholar",
        2,
    ),
    (
        "scholar_gold",
        "Scholar — Master",
        "Score 75% or higher on 30 activities.",
        "gold",
        "🎓",
        {"type": "activity_score", "min_pct": 75, "count": 30},
        "scholar",
        3,
    ),
    # Streak family — login streak
    (
        "streak_bronze",
        "Streak — Spark",
        "Maintain a 3-day login streak.",
        "bronze",
        "🔥",
        {"type": "streak", "streak": "login", "threshold": 3},
        "streak",
        1,
    ),
    (
        "streak_silver",
        "Streak — Blaze",
        "Maintain a 7-day login streak.",
        "silver",
        "🌋",
        {"type": "streak", "streak": "login", "threshold": 7},
        "streak",
        2,
    ),
    (
        "streak_gold",
        "Streak — Inferno",
        "Maintain a 30-day login streak.",
        "gold",
        "☄️",
        {"type": "streak", "streak": "login", "threshold": 30},
        "streak",
        3,
    ),
]

# Staff (non-student, non-teacher) badges — Admin, Registrar, Academic Director,
# Program Head, Coil Admin, Time Keeper. Auto-awarded set is intentionally small;
# richer recognition should be granted manually via admin.
# Staff (non-student, non-teacher) badges — Admin, Registrar, Academic Director,
# Program Head, Coil Admin, Time Keeper. Tenure family uses the same `family`
# grouping pattern as student badges.
STAFF_BADGES = [
    (
        "staff_welcome",
        "Welcome Aboard",
        "Sign in to ClassEdge for the first time.",
        "bronze",
        "👋",
        {"type": "first_sign_in"},
        "",
        0,
    ),
    (
        "staff_profile_complete",
        "Profile Complete",
        "Fill in your full name and email.",
        "bronze",
        "🪪",
        {"type": "profile_complete"},
        "",
        0,
    ),
    (
        "staff_active_week",
        "Currently Active",
        "Signed in within the last 7 days.",
        "bronze",
        "🔆",
        {"type": "recently_active", "within_days": 7},
        "",
        0,
    ),
    (
        "staff_active_month",
        "Engaged",
        "Signed in within the last 30 days.",
        "silver",
        "🌟",
        {"type": "recently_active", "within_days": 30},
        "",
        0,
    ),
    (
        "staff_role_admin",
        "System Operator",
        "Hold administrator privileges.",
        "gold",
        "⚙️",
        {"type": "role_admin"},
        "",
        0,
    ),
    # Tenure family
    (
        "staff_tenured_30",
        "Tenure — Month One",
        "Account active for 30 days.",
        "bronze",
        "📅",
        {"type": "tenure_days", "threshold": 30},
        "staff_tenure",
        1,
    ),
    (
        "staff_tenured_90",
        "Tenure — Quarter",
        "Account active for 90 days.",
        "silver",
        "📆",
        {"type": "tenure_days", "threshold": 90},
        "staff_tenure",
        2,
    ),
    (
        "staff_tenured_180",
        "Tenure — Half Year",
        "Account active for 180 days.",
        "gold",
        "🗓️",
        {"type": "tenure_days", "threshold": 180},
        "staff_tenure",
        3,
    ),
    (
        "staff_tenured_365",
        "Tenure — Anniversary",
        "Account active for 365 days.",
        "platinum",
        "🏛️",
        {"type": "tenure_days", "threshold": 365},
        "staff_tenure",
        4,
    ),
]


# ---------------------------------------------------------------------------
# Seeders
# ---------------------------------------------------------------------------
def seed_roles() -> dict:
    header("Roles")
    out = {}
    for name in ROLE_NAMES:
        role, created = Role.objects.get_or_create(name=name)
        out[name] = role
        log("role", f"{'created' if created else 'exists'}: {name}")
    return out


def seed_department_course():
    header("Department + Course")
    dept, created_d = Department.objects.get_or_create(
        name="Junior High School",
    )
    log("dept", f"{'created' if created_d else 'exists'}: {dept.name}")

    course, created_c = Course.objects.get_or_create(
        name="Grade 7 - Rizal",
        defaults={"short_name": "G7-Rizal"},
    )
    log("course", f"{'created' if created_c else 'exists'}: {course.name}")
    return dept, course


def _ensure_user(
    username, first, last, email, password, role, dept, course, year, is_staff=False
):
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "first_name": first,
            "last_name": last,
            "email": email,
            "needs_password_setup": False,
            "needs_onboarding": False,
            "is_staff": is_staff,
        },
    )
    if created:
        user.set_password(password)
        user.first_name = first
        user.last_name = last
        user.email = email
        user.is_staff = is_staff
        user.save()
    elif user.is_staff != is_staff:
        # Keep staff flag in sync when re-running the seeder.
        user.is_staff = is_staff
        user.save(update_fields=["is_staff"])
    # Profile is OneToOne; create if missing.
    profile, p_created = Profile.objects.get_or_create(
        user=user,
        defaults={
            "first_name": first,
            "last_name": last,
            "role": role,
            "status": True,
            "student_status": "Regular",
            "grade_year_level": year,
            "course": course,
            "department_fields": dept,
        },
    )
    if not p_created and profile.role_id != role.id:
        profile.role = role
        profile.save(update_fields=["role"])

    log("user", f"{'created' if created else 'exists'}: {username} ({role.name})")
    return user


def seed_users(roles, dept, course):
    header("Users")
    student_role = roles["Student"]
    teacher_role = roles["Teacher"]

    users = {}

    # Demo accounts (well-known passwords)
    u_username, u_first, u_last, u_email, u_pw = DEMO_STUDENT
    users[u_username] = _ensure_user(
        u_username,
        u_first,
        u_last,
        u_email,
        u_pw,
        student_role,
        dept,
        course,
        "Grade 7",
    )
    t_username, t_first, t_last, t_email, t_pw = DEMO_TEACHER
    users[t_username] = _ensure_user(
        t_username,
        t_first,
        t_last,
        t_email,
        t_pw,
        teacher_role,
        dept,
        course,
        None,
    )

    # Bulk students
    for username, first, last, email in STUDENTS:
        users[username] = _ensure_user(
            username,
            first,
            last,
            email,
            DEFAULT_PASSWORD,
            student_role,
            dept,
            course,
            "Grade 7",
        )

    # Bulk teachers
    for username, first, last, email in TEACHERS:
        users[username] = _ensure_user(
            username,
            first,
            last,
            email,
            DEFAULT_PASSWORD,
            teacher_role,
            dept,
            course,
            None,
        )

    # One demo account per remaining role (Admin, Registrar, Academic Director,
    # Program Head, Coil Admin, Time Keeper). The staff flag is on for Admin
    # so it satisfies the `user.is_staff` checks in the operations sidebar.
    for role_name, username, first, last, email, password in ROLE_DEMOS:
        role = roles.get(role_name)
        if role is None:
            log("user", f"⚠ skipping {username}: role '{role_name}' missing")
            continue
        users[username] = _ensure_user(
            username,
            first,
            last,
            email,
            password,
            role,
            dept,
            course,
            None,
            is_staff=(role_name == "Admin"),
        )

    return users


def seed_friendships(users):
    header("Friendships")
    demo = users["demo_student"]

    # demo_student is auto-friends with the first 10 students (the original list).
    auto_friend_unames = [u for u, *_ in STUDENTS[:10]]
    for uname in auto_friend_unames:
        other = users[uname]
        friend, created = Friend.objects.get_or_create(
            from_user=demo,
            to_user=other,
            defaults={"status": "accepted"},
        )
        if not created and friend.status != "accepted":
            friend.status = "accepted"
            friend.save(update_fields=["status"])
        log("friend", f"{'created' if created else 'exists'}: demo_student ↔ {uname}")

    # A handful of cross-friendships among the bulk students.
    pairs = [
        ("alex_cruz", "bea_santos"),
        ("alex_cruz", "carlo_reyes"),
        ("bea_santos", "diane_lim"),
        ("carlo_reyes", "ej_garcia"),
        ("ej_garcia", "faye_torres"),
        ("gio_mendoza", "hana_dela_cruz"),
        ("ivan_chua", "jen_villanueva"),
        ("kara_lopez", "alex_cruz"),
        ("leo_pineda", "bea_santos"),
    ]
    for a, b in pairs:
        Friend.objects.get_or_create(
            from_user=users[a],
            to_user=users[b],
            defaults={"status": "accepted"},
        )

    # Pending requests SENT TO demo_student → populates the Requests tab.
    for sender_name in ("kara_lopez", "leo_pineda"):
        if (
            not Friend.objects.filter(
                from_user=users[sender_name], to_user=demo
            ).exists()
            and not Friend.objects.filter(
                from_user=demo, to_user=users[sender_name]
            ).exists()
        ):
            Friend.objects.create(
                from_user=users[sender_name],
                to_user=demo,
                status="pending",
            )
            log("friend", f"pending: {sender_name} → demo_student")
        else:
            log("friend", f"pending exists: {sender_name} → demo_student")

    # mia_robles and nico_tan stay unconnected → they appear in Discover.


def seed_chats(users):
    header("One-on-one chats")
    # Per-pair check so new pairs added later (e.g., demo_teacher conversations)
    # still get seeded even if the original demo_student chats already exist.
    now = timezone.now()
    for (a_name, b_name), turns in CHAT_SCRIPTS:
        a, b = users[a_name], users[b_name]
        existing = Chat.objects.filter(
            Q(sender=a, receiver=b) | Q(sender=b, receiver=a),
        ).exists()
        if existing:
            log("chat", f"exists: {a_name} ↔ {b_name} — skipping")
            continue
        for i, msg in enumerate(turns):
            sender, receiver = (a, b) if i % 2 == 0 else (b, a)
            Chat.objects.create(
                sender=sender,
                receiver=receiver,
                message=msg,
                is_read=True,
                created_at=now - timedelta(minutes=(len(turns) - i) * 3),
            )
        log("chat", f"seeded {len(turns)} messages: {a_name} ↔ {b_name}")


def seed_group_chat(users):
    header("Group chat")
    name = "Grade 7 - Rizal Study Group"
    group, created = GroupChat.objects.get_or_create(
        name=name,
        defaults={"created_by": users["demo_student"]},
    )
    if created:
        members = [
            users["demo_student"],
            users["alex_cruz"],
            users["bea_santos"],
            users["carlo_reyes"],
            users["diane_lim"],
        ]
        group.members.add(*members)
        log("group", f"created: {name} ({len(members)} members)")
    else:
        log("group", f"exists: {name}")

    # Seed messages only if none exist yet.
    if not GroupMessage.objects.filter(group=group).exists():
        scripted = [
            ("demo_student", "Hey team! Welcome to our study group 👋"),
            ("alex_cruz", "Glad to be here! When are we meeting?"),
            ("bea_santos", "Let's do every Tuesday and Thursday after class."),
            ("carlo_reyes", "Works for me. I'll bring the past quizzes."),
            ("diane_lim", "I'll handle the slides 📊"),
            ("demo_student", "You guys rock 🚀"),
        ]
        now = timezone.now()
        for i, (uname, msg) in enumerate(scripted):
            GroupMessage.objects.create(
                group=group,
                sender=users[uname],
                message=msg,
                is_read=True,
                created_at=now - timedelta(minutes=(len(scripted) - i) * 4),
            )
        log("group", f"seeded {len(scripted)} messages")
    else:
        log("group", "messages already seeded — skipping")


def seed_posts(users):
    header("Social-media posts")
    if Post.objects.exists():
        log("post", "posts already seeded — skipping")
        return

    student_unames = [u for u, *_ in STUDENTS] + ["demo_student"]
    for uname, content in POSTS:
        post = Post.objects.create(user=users[uname], content=content, privacy="public")
        # Random likes from 2-5 friends
        likers = random.sample(student_unames, k=random.randint(2, 5))
        for liker in likers:
            if liker == uname:
                continue
            Like.objects.get_or_create(post=post, user=users[liker])
        # 1-2 comments
        commenters = random.sample(student_unames, k=random.randint(1, 2))
        comments = ["Nice one!", "Same here 😅", "Goodluck!", "Tara!", "🔥🔥🔥"]
        for commenter in commenters:
            if commenter == uname:
                continue
            Comment.objects.create(
                post=post,
                user=users[commenter],
                content=random.choice(comments),
            )
        log("post", f'created post by {uname}: "{content[:40]}..."')


# ---------------------------------------------------------------------------
# Academic / Activity / Calendar / Gamification seeders
# ---------------------------------------------------------------------------
def _safe(section, label, fn):
    """Run a seeder block in its own transaction; log warnings on failure."""
    try:
        with transaction.atomic():
            fn()
    except Exception as exc:  # noqa: BLE001
        log(section, f"⚠ skipped {label}: {exc.__class__.__name__}: {exc}")
        if os.environ.get("SEED_DEBUG"):
            traceback.print_exc()


def _student_users(users):
    """Return only the seeded student User objects (excluding teachers/demo_teacher)."""
    teacher_unames = {DEMO_TEACHER[0]} | {u for u, *_ in TEACHERS}
    return [u for uname, u in users.items() if uname not in teacher_unames]


def seed_activity_types():
    header("Activity Types")
    if ActivityType is None:
        log("activity-type", "model not available — skipping")
        return {}
    out = {}
    for name in ACTIVITY_TYPES:
        obj, created = ActivityType.objects.get_or_create(name=name)
        out[name] = obj
        log("activity-type", f"{'created' if created else 'exists'}: {name}")
    return out


def seed_semester_terms(dept):
    header("Semester + Terms")
    if Semester is None or Term is None:
        log("semester", "models not available — skipping")
        return None, []

    today = timezone.localdate()
    sem, created = Semester.objects.get_or_create(
        semester_name="School Year 2025-2026",
        department=dept,
        defaults={
            "start_date": today - timedelta(days=60),
            "end_date": today + timedelta(days=120),
            "passing_grade": 75,
            "end_semester": False,
        },
    )
    log("semester", f"{'created' if created else 'exists'}: {sem.semester_name}")

    # Spread the four quarters across the school year duration.
    terms = []
    span = (sem.end_date - sem.start_date) // 4
    for idx, name in enumerate(TERM_NAMES):
        t_start = sem.start_date + span * idx
        t_end = sem.start_date + span * (idx + 1) - timedelta(days=1)
        term, t_created = Term.objects.get_or_create(
            term_name=name,
            semester=sem,
            defaults={"start_date": t_start, "end_date": t_end},
        )
        terms.append(term)
        log("term", f"{'created' if t_created else 'exists'}: {name}")
    return sem, terms


def seed_subjects(users):
    header("Subjects")
    if Subject is None:
        log("subject", "model not available — skipping")
        return {}
    out = {}
    for code, name, short, desc, teacher_uname, units in SUBJECTS:
        teacher = users.get(teacher_uname)
        subj, created = Subject.objects.get_or_create(
            subject_code=code,
            defaults={
                "subject_name": name,
                "subject_short_name": short,
                "subject_description": desc,
                "subject_descriptive_title": name,
                "assign_teacher": teacher,
                "unit": units,
                "status": "Ongoing",
                "subject_type": "Lec",
            },
        )
        # Always sync the assigned teacher to what SUBJECTS declares so re-runs
        # (after we move ownership, e.g., to demo_teacher) converge correctly.
        if not created and teacher is not None and subj.assign_teacher_id != teacher.id:
            subj.assign_teacher = teacher
            subj.save(update_fields=["assign_teacher"])
        out[code] = subj
        log(
            "subject",
            f"{'created' if created else 'exists'}: {code} — {name} ({teacher_uname})",
        )
    return out


def seed_enrollments(users, subjects, semester):
    header("Enrollments")
    if SubjectEnrollment is None:
        log("enrollment", "model not available — skipping")
        return
    if not subjects:
        log("enrollment", "no subjects — skipping")
        return

    students = _student_users(users)
    subject_codes = list(subjects.keys())
    rng = random.Random(7)

    for student in students:
        # A Grade 7 section takes ALL core subjects together.
        picks = subject_codes

        for code in picks:
            subj = subjects[code]
            enr, created = SubjectEnrollment.objects.get_or_create(
                student=student,
                subject=subj,
                semester=semester,
                defaults={
                    "status": "enrolled",
                    "can_view_grade": True,
                    "is_active_semester": True,
                    "student_name": f"{student.first_name} {student.last_name}".strip(),
                },
            )
            if created:
                log("enrollment", f"+ {student.username} → {code}")


def seed_assignments(subjects, activity_types, terms):
    header("Assignments (Activities)")
    if Activity is None:
        log("activity", "model not available — skipping")
        return []
    if not subjects or not terms:
        return []

    # Use the term whose date range currently covers today (fallback: midterm).
    today = timezone.localdate()
    term = next(
        (
            t
            for t in terms
            if t.start_date and t.end_date and t.start_date <= today <= t.end_date
        ),
        terms[1] if len(terms) > 1 else terms[0],
    )

    created_activities = []
    for subj_code, subj in subjects.items():
        for name, type_name, day_offset, max_score in SUBJECT_ACTIVITIES:
            atype = activity_types.get(type_name)
            start = timezone.now() + timedelta(days=day_offset - 7)
            end = timezone.now() + timedelta(days=day_offset)
            act, created = Activity.objects.get_or_create(
                activity_name=f"{subj.subject_short_name or subj_code} — {name}",
                subject=subj,
                defaults={
                    "activity_type": atype,
                    "term": term,
                    "start_time": start,
                    "end_time": end,
                    "max_score": max_score,
                    "passing_score": 60,
                    "status": True,
                    "is_graded": True,
                    "activity_instruction": f"Auto-seeded {type_name.lower()} for {subj.subject_name}.",
                },
            )
            created_activities.append(act)
            if created:
                log("activity", f"+ {subj_code}: {name}")
    return created_activities


def seed_grades(users, subjects, terms, activities, semester):
    header("Grades / Student Activity scores")
    if StudentActivity is None:
        log("grade", "model not available — skipping")
        return
    if not activities or not subjects or not terms:
        log("grade", "missing prerequisites — skipping")
        return

    # Map activity → its subject for fast lookup
    students = _student_users(users)
    rng = random.Random(13)

    # Only create grades for activities whose due date has passed
    now = timezone.now()
    past_activities = [a for a in activities if a.end_time and a.end_time <= now]
    log(
        "grade",
        f"considering {len(past_activities)} past activities for {len(students)} students",
    )

    for student in students:
        # Find the subjects this student is enrolled in
        if SubjectEnrollment is not None:
            enrolled_ids = set(
                SubjectEnrollment.objects.filter(student=student).values_list(
                    "subject_id", flat=True
                )
            )
        else:
            enrolled_ids = {s.id for s in subjects.values()}

        # Profile-tier skill: each student has a baseline "skill" 60-95
        baseline = rng.randint(60, 95)

        for act in past_activities:
            if act.subject_id not in enrolled_ids:
                continue
            # Score: baseline + jitter, clamped 40-100, scaled to max_score
            pct = max(40, min(100, baseline + rng.randint(-12, 8)))
            score = round((pct / 100.0) * float(act.max_score or 100), 2)

            sa, created = StudentActivity.objects.get_or_create(
                student=student,
                activity=act,
                defaults={
                    "subject": act.subject,
                    "term": act.term,
                    "total_score": score,
                    "start_time": act.start_time,
                    "end_time": act.end_time,
                    "is_editable": False,
                },
            )
            if created and StudentActivityLog is not None:
                try:
                    StudentActivityLog.objects.create(
                        student=student,
                        activity=act,
                        subject=act.subject,
                        total_score=score,
                    )
                except Exception:
                    pass

    # Participation scores per (student, subject, current term)
    if StudentParticipationScore is not None:
        cur_term = next((t for t in terms if t.term_name == "Second Quarter"), terms[0])
        for student in students:
            enrolled_subjects = (
                SubjectEnrollment.objects.filter(student=student).values_list(
                    "subject", flat=True
                )
                if SubjectEnrollment is not None
                else [s.id for s in subjects.values()]
            )
            for subj_id in enrolled_subjects:
                StudentParticipationScore.objects.get_or_create(
                    student=student,
                    subject_id=subj_id,
                    term=cur_term,
                    defaults={
                        "score": rng.randint(70, 100),
                        "max_score": 100,
                    },
                )

    log("grade", f"seeded grades for {len(students)} students")


def seed_calendar(users, dept):
    header("Calendar — Holidays + Events + Announcements")
    creator = (
        users.get("demo_teacher")
        or users.get("teacher_navarro")
        or next(iter(users.values()))
    )

    if Holiday is not None:
        for title, d, htype, color in HOLIDAYS:
            obj, created = Holiday.objects.get_or_create(
                title=title,
                date=d,
                defaults={"holiday_type": htype, "color": color, "department": dept},
            )
            if created:
                log("holiday", f"+ {title} ({d.isoformat()})")
    else:
        log("holiday", "model not available — skipping")

    if Event is not None:
        today = timezone.localdate()
        for title, desc, day_offset, t, location in EVENTS:
            ev_date = today + timedelta(days=day_offset)
            obj, created = Event.objects.get_or_create(
                title=title,
                start_date=ev_date,
                defaults={
                    "description": desc,
                    "end_date": ev_date,
                    "time": t,
                    "location": location,
                    "created_by": creator,
                    "department": dept,
                },
            )
            if created:
                log("event", f"+ {title} ({ev_date.isoformat()})")
    else:
        log("event", "model not available — skipping")

    if Announcement is not None:
        today = timezone.localdate()
        for title, desc in ANNOUNCEMENTS:
            obj, created = Announcement.objects.get_or_create(
                title=title,
                defaults={
                    "description": desc,
                    "date": today,
                    "created_by": creator,
                    "department": dept,
                },
            )
            if created:
                log("announce", f"+ {title}")

        # Institution-wide announcements (no department), so every user sees them.
        for title, desc in INSTITUTION_ANNOUNCEMENTS:
            obj, created = Announcement.objects.get_or_create(
                title=title,
                defaults={
                    "description": desc,
                    "date": today,
                    "created_by": creator,
                    "department": None,
                },
            )
            if created:
                log("announce", f"+ (school-wide) {title}")
    else:
        log("announce", "model not available — skipping")

    # Institution-wide events (no department)
    if Event is not None:
        today = timezone.localdate()
        for title, desc, day_offset, t, location in INSTITUTION_EVENTS:
            ev_date = today + timedelta(days=day_offset)
            obj, created = Event.objects.get_or_create(
                title=title,
                start_date=ev_date,
                defaults={
                    "description": desc,
                    "end_date": ev_date,
                    "time": t,
                    "location": location,
                    "created_by": creator,
                    "department": None,
                },
            )
            if created:
                log("event", f"+ (school-wide) {title} ({ev_date.isoformat()})")


def seed_gamification(users, subjects):
    header("Gamification — XP, Leaderboard, Badges")
    students = _student_users(users)

    if StudentGamification is None:
        log("xp", "model not available — skipping")
        return

    rng = random.Random(99)
    today = timezone.localdate()

    # XP per student — give demo_student a top-tier rank
    for student in students:
        if student.username == "demo_student":
            xp, level, login_streak, sub_streak = 4250, 12, 14, 9
        else:
            xp = rng.randint(450, 3800)
            level = max(1, xp // 350)
            login_streak = rng.randint(0, 12)
            sub_streak = rng.randint(0, 8)

        gam, created = StudentGamification.objects.get_or_create(
            student=student,
            defaults={
                "total_xp": xp,
                "current_level": level,
                "login_streak": login_streak,
                "submission_streak": sub_streak,
                "accuracy_streak": rng.randint(0, 6),
                "streak_freezes_available": 1,
                "last_active_date": today - timedelta(days=rng.randint(0, 2)),
            },
        )
        # Refresh values on existing rows so re-running gives a fresh leaderboard
        if not created:
            gam.total_xp = xp
            gam.current_level = level
            gam.login_streak = login_streak
            gam.submission_streak = sub_streak
            gam.last_active_date = today - timedelta(days=rng.randint(0, 2))
            gam.save()

        # Add a few XP transactions so the audit trail isn't empty.
        if (
            XPTransaction is not None
            and not XPTransaction.objects.filter(student=student).exists()
        ):
            for i, (amount, reason, src) in enumerate(
                [
                    (50, "Completed Daily Challenge", "side_activity"),
                    (120, "Submitted Assignment", "activity"),
                    (75, "Login Streak Bonus", "streak"),
                    (200, "Top Quiz Score", "activity"),
                ]
            ):
                XPTransaction.objects.create(
                    student=student,
                    amount=amount,
                    reason=reason,
                    source_type=src,
                )
        log("xp", f"{student.username}: {xp} XP (lvl {level})")

    # Badge definitions — refresh icon/desc on existing rows so re-runs pick up
    # template-friendly emoji values instead of stale FontAwesome strings.
    if BadgeDefinition is not None:
        all_defs = [(*row, "student") for row in BADGES]
        all_defs += [(*row, "staff") for row in STAFF_BADGES]
        active_codes = {row[0] for row in all_defs}
        # Drop legacy badges that have been removed/renamed.
        BadgeDefinition.objects.filter(target_role__in=["student", "staff"]).exclude(
            code__in=active_codes
        ).delete()

        for (
            code,
            name,
            desc,
            tier,
            icon,
            criteria,
            family,
            family_rank,
            target_role,
        ) in all_defs:
            obj, created = BadgeDefinition.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": desc,
                    "tier": tier,
                    "icon": icon,
                    "target_role": target_role,
                    "criteria_json": criteria,
                    "family": family,
                    "family_rank": family_rank,
                },
            )
            needs_update = not created and (
                obj.icon != icon
                or obj.description != desc
                or obj.criteria_json != criteria
                or obj.target_role != target_role
                or obj.tier != tier
                or obj.name != name
                or obj.family != family
                or obj.family_rank != family_rank
            )
            if needs_update:
                obj.icon = icon
                obj.description = desc
                obj.tier = tier
                obj.name = name
                obj.target_role = target_role
                obj.criteria_json = criteria
                obj.family = family
                obj.family_rank = family_rank
                obj.save(
                    update_fields=[
                        "icon",
                        "description",
                        "tier",
                        "name",
                        "target_role",
                        "criteria_json",
                        "family",
                        "family_rank",
                    ]
                )
            if created:
                log("badge", f"+ definition: {name} ({tier}, {target_role})")

    # Award badges (demo_student gets several; others get random 1-2)
    if BadgeDefinition is not None and StudentBadge is not None:
        all_defs = list(BadgeDefinition.objects.all())
        for student in students:
            if student.username == "demo_student":
                awarded = all_defs[:4]
            else:
                awarded = rng.sample(all_defs, k=min(2, len(all_defs)))
            for b in awarded:
                StudentBadge.objects.get_or_create(student=student, badge=b)


def seed_quest_map(users, subjects):
    header("Quest Map — Side Activities + Attempts")
    if SideActivity is None:
        log("quest", "model not available — skipping")
        return
    if not subjects:
        log("quest", "no subjects available — skipping")
        return

    creator = users.get("demo_teacher") or users.get("teacher_navarro")
    rng = random.Random(31)
    side_acts = []

    for subj_code, subj in subjects.items():
        for sub_type, title, xp, mins in SIDE_ACTIVITIES:
            obj, created = SideActivity.objects.get_or_create(
                subject=subj,
                title=f"{subj.subject_short_name or subj_code}: {title}",
                defaults={
                    "sub_type": sub_type,
                    "content_json": {"questions": [], "seed": True},
                    "estimated_minutes": mins,
                    "xp_reward": xp,
                    "is_active": True,
                    "created_by": creator,
                },
            )
            side_acts.append(obj)
            if created:
                log("quest", f"+ {subj_code}: {title}")

    if SideActivityAttempt is None or not side_acts:
        return

    # Each student completes ~half the side activities for their subjects
    students = _student_users(users)
    for student in students:
        # Pick subjects the student is enrolled in, fall back to all
        if SubjectEnrollment is not None:
            enrolled_ids = set(
                SubjectEnrollment.objects.filter(student=student).values_list(
                    "subject_id", flat=True
                )
            )
            relevant = [a for a in side_acts if a.subject_id in enrolled_ids]
        else:
            relevant = side_acts

        sample_size = max(1, len(relevant) // 2)
        for sa in rng.sample(relevant, k=sample_size):
            attempt, created = SideActivityAttempt.objects.get_or_create(
                student=student,
                side_activity=sa,
                defaults={
                    "completed_at": timezone.now() - timedelta(days=rng.randint(0, 30)),
                    "score": rng.uniform(0.7, 1.0) * 100,
                    "time_taken_seconds": sa.estimated_minutes * 60,
                    "xp_awarded": sa.xp_reward,
                    "details_json": {"seed": True},
                },
            )


def seed_attendance(users, subjects, semester):
    """Seed attendance records for each enrolled student across past sessions.

    Creates ~3 sessions/week (Mon/Wed/Fri) for the past 6 weeks, weighted toward
    Present so the analytics rollups look realistic. Also seeds default
    TeacherAttendancePoints (Present=1.0, Late=0.5, Absent=0.0, Excused=1.0).
    """
    header("Attendance — sessions + status records")
    if (
        Attendance is None
        or AttendanceStatus is None
        or TeacherAttendancePoints is None
    ):
        log("attendance", "models not available — skipping")
        return
    if SubjectEnrollment is None:
        log("attendance", "SubjectEnrollment unavailable — skipping")
        return
    if not subjects or not semester:
        log("attendance", "missing prerequisites — skipping")
        return

    # 1. Status rows
    statuses = {}
    for s in ["Present", "Present_Online", "Late", "Absent", "Excused"]:
        obj, _ = AttendanceStatus.objects.get_or_create(status=s)
        statuses[s] = obj

    # 2. Per-teacher grading scale (used by Attendance.get_status_points)
    point_map = [
        ("Present", 1.0),
        ("Present_Online", 1.0),
        ("Late", 0.5),
        ("Absent", 0.0),
        ("Excused", 1.0),
    ]
    seen_teachers = set()
    for subj in subjects.values():
        teacher = subj.assign_teacher
        if not teacher or teacher.id in seen_teachers:
            continue
        seen_teachers.add(teacher.id)
        for status_name, pts in point_map:
            TeacherAttendancePoints.objects.get_or_create(
                teacher=teacher,
                status=statuses[status_name],
                defaults={"points": pts},
            )

    # 3. Build session dates: Mon/Wed/Fri for the past 6 weeks (skipping today).
    today = timezone.localdate()
    sessions = []
    for week in range(6):
        # Anchor to start of the current ISO week
        monday = today - timedelta(days=today.weekday()) - timedelta(weeks=week)
        for offset in (0, 2, 4):  # Mon, Wed, Fri
            d = monday + timedelta(days=offset)
            if d < today:
                sessions.append(d)
    sessions = sorted(set(sessions))

    # 4. Weighted choice distribution (sums to 1.0)
    distribution = [
        ("Present", 0.78),
        ("Late", 0.10),
        ("Absent", 0.07),
        ("Excused", 0.05),
    ]
    rng = random.Random(57)

    def pick_status():
        r = rng.random()
        cumulative = 0.0
        for status_name, weight in distribution:
            cumulative += weight
            if r <= cumulative:
                return status_name
        return "Present"

    # 5. Create attendance records — only for subjects + their enrolled students.
    total = 0
    for subj in subjects.values():
        teacher = subj.assign_teacher
        enrolled = SubjectEnrollment.objects.filter(
            subject=subj,
            semester=semester,
            status="enrolled",
        ).select_related("student")

        for enr in enrolled:
            for session_date in sessions:
                _, created = Attendance.objects.get_or_create(
                    student=enr.student,
                    subject=subj,
                    date=session_date,
                    defaults={
                        "status": statuses[pick_status()],
                        "teacher": teacher,
                        "graded": True,
                    },
                )
                if created:
                    total += 1
        log(
            "attendance",
            f"+ {subj.subject_code}: {enrolled.count()} students × {len(sessions)} sessions",
        )

    log(
        "attendance",
        f"seeded {total} new attendance records across {len(sessions)} session days",
    )


def seed_dashboard_notifications(users, activities):
    header("Dashboard — Notifications")
    if Notification is None:
        log("notif", "model not available — skipping")
        return
    if not activities:
        log("notif", "no activities — skipping")
        return

    students = _student_users(users)
    creator = (
        users.get("demo_teacher")
        or users.get("teacher_navarro")
        or next(iter(users.values()))
    )
    upcoming = [a for a in activities if a.end_time and a.end_time > timezone.now()][:3]
    if not upcoming:
        return

    for student in students:
        for act in upcoming:
            Notification.objects.get_or_create(
                user_id=student,
                entity_id=act.id,
                entity_type="activity",
                defaults={
                    "name": act.activity_name,
                    "message": f"Upcoming: {act.activity_name} due {act.end_time.strftime('%b %d')}.",
                    "due_at": act.end_time,
                    "is_read": False,
                    "created_by": creator,
                },
            )
    log("notif", f"seeded reminders for {len(students)} students")

-------------------------------------------------------------
# Lessons (Modules) per subject
# ---------------------------------------------------------------------------
LESSONS_BY_SUBJECT = {
    "ENG7": [
        (
            "Lesson 1: Parts of Speech",
            "https://www.britannica.com/dictionary/eb/3000-words",
        ),
        (
            "Lesson 2: Reading Comprehension",
            "https://en.wikipedia.org/wiki/Reading_comprehension",
        ),
        (
            "Lesson 3: Subject-Verb Agreement",
            "https://en.wikipedia.org/wiki/Agreement_(linguistics)",
        ),
        (
            "Lesson 4: Short Story Elements",
            "https://en.wikipedia.org/wiki/Plot_(narrative)",
        ),
        ("Lesson 5: Writing a Paragraph", "https://en.wikipedia.org/wiki/Paragraph"),
    ],
    "FIL7": [
        (
            "Aralin 1: Mga Bahagi ng Pananalita",
            "https://tl.wikipedia.org/wiki/Bahagi_ng_pananalita",
        ),
        ("Aralin 2: Pang-uri at Pandiwa", "https://tl.wikipedia.org/wiki/Pandiwa"),
        ("Aralin 3: Maikling Kwento", "https://tl.wikipedia.org/wiki/Maikling_kwento"),
        ("Aralin 4: Tula at Bugtong", "https://tl.wikipedia.org/wiki/Tula"),
        ("Aralin 5: Pagsulat ng Talata", "https://tl.wikipedia.org/wiki/Talata"),
    ],
    "MATH7": [
        ("Lesson 1: Sets", "https://en.wikipedia.org/wiki/Set_(mathematics)"),
        ("Lesson 2: Integers", "https://en.wikipedia.org/wiki/Integer"),
        ("Lesson 3: Fractions & Decimals", "https://en.wikipedia.org/wiki/Fraction"),
        (
            "Lesson 4: Algebraic Expressions",
            "https://en.wikipedia.org/wiki/Algebraic_expression",
        ),
        ("Lesson 5: Basic Geometry", "https://en.wikipedia.org/wiki/Geometry"),
    ],
    "SCI7": [
        (
            "Lesson 1: Scientific Method",
            "https://en.wikipedia.org/wiki/Scientific_method",
        ),
        ("Lesson 2: Matter & Its Properties", "https://en.wikipedia.org/wiki/Matter"),
        (
            "Lesson 3: Living Things & Cells",
            "https://en.wikipedia.org/wiki/Cell_(biology)",
        ),
        ("Lesson 4: Force and Motion", "https://en.wikipedia.org/wiki/Motion"),
        ("Lesson 5: Energy", "https://en.wikipedia.org/wiki/Energy"),
    ],
    "AP7": [
        ("Aralin 1: Heograpiya ng Asya", "https://en.wikipedia.org/wiki/Asia"),
        (
            "Aralin 2: Sinaunang Kabihasnan",
            "https://en.wikipedia.org/wiki/Civilization",
        ),
        (
            "Aralin 3: Relihiyon sa Asya",
            "https://en.wikipedia.org/wiki/Religion_in_Asia",
        ),
        ("Aralin 4: Kolonyalismo", "https://en.wikipedia.org/wiki/Colonialism"),
        (
            "Aralin 5: Kontemporaryong Isyu",
            "https://en.wikipedia.org/wiki/Southeast_Asia",
        ),
    ],
    "ESP7": [
        (
            "Aralin 1: Pagpapahalaga sa Sarili",
            "https://en.wikipedia.org/wiki/Self-esteem",
        ),
        ("Aralin 2: Pamilya at Tahanan", "https://en.wikipedia.org/wiki/Family"),
        ("Aralin 3: Pakikipagkapwa", "https://en.wikipedia.org/wiki/Empathy"),
        ("Aralin 4: Konsiyensya", "https://en.wikipedia.org/wiki/Conscience"),
        ("Aralin 5: Mabuting Mamamayan", "https://en.wikipedia.org/wiki/Citizenship"),
    ],
    "MAPEH7": [
        ("Lesson 1: Music — Rhythm & Melody", "https://en.wikipedia.org/wiki/Rhythm"),
        (
            "Lesson 2: Arts — Elements of Art",
            "https://en.wikipedia.org/wiki/Elements_of_art",
        ),
        (
            "Lesson 3: PE — Physical Fitness",
            "https://en.wikipedia.org/wiki/Physical_fitness",
        ),
        ("Lesson 4: Health — Nutrition", "https://en.wikipedia.org/wiki/Nutrition"),
        ("Lesson 5: Personal Hygiene", "https://en.wikipedia.org/wiki/Hygiene"),
    ],
    "TLE7": [
        (
            "Lesson 1: Intro to ICT",
            "https://en.wikipedia.org/wiki/Information_and_communications_technology",
        ),
        ("Lesson 2: Computer Basics", "https://en.wikipedia.org/wiki/Computer"),
        ("Lesson 3: Home Economics", "https://en.wikipedia.org/wiki/Home_economics"),
        (
            "Lesson 4: Basic Cooking & Safety",
            "https://en.wikipedia.org/wiki/Food_safety",
        ),
        (
            "Lesson 5: Simple Livelihood Skills",
            "https://en.wikipedia.org/wiki/Entrepreneurship",
        ),
    ],
}


def seed_lessons(subjects, terms):
    header("Lessons (Modules)")
    if Module is None:
        log("lesson", "model not available — skipping")
        return
    if not subjects:
        log("lesson", "no subjects — skipping")
        return

    # Tie lessons to the First Quarter so they appear in the active school year.
    prelim = next(
        (t for t in terms if t.term_name == "First Quarter"),
        terms[0] if terms else None,
    )

    for code, subj in subjects.items():
        defs = LESSONS_BY_SUBJECT.get(code, [])
        for order, (title, url) in enumerate(defs, start=1):
            obj, created = Module.objects.get_or_create(
                file_name=title,
                subject=subj,
                defaults={
                    "url": url,
                    "term": prelim,
                    "description": f"{title} — auto-seeded reference material.",
                    "start_date": timezone.now() - timedelta(days=14),
                    "order": order,
                    "allow_download": True,
                },
            )
            if created:
                log("lesson", f"+ {code}: {title}")


# ---------------------------------------------------------------------------
# Activity Question bank
# ---------------------------------------------------------------------------
QUIZ_TYPE_NAMES = ["Multiple Choice", "Essay", "True/False", "Fill in the Blank"]

# (question, correct_answer, [choices])  -- choices are only used for MC.
# Grade 7 general-knowledge items across the core subjects.
SAMPLE_MC_QUESTIONS = [
    ("What is the value of 7 × 8?", "56", ["54", "56", "63", "48"]),
    (
        "Which planet is known as the Red Planet?",
        "Mars",
        ["Venus", "Mars", "Jupiter", "Saturn"],
    ),
    (
        "What is the past tense of the verb 'go'?",
        "went",
        ["goed", "gone", "went", "going"],
    ),
    (
        "Ano ang pambansang bayani ng Pilipinas?",
        "Jose Rizal",
        ["Andres Bonifacio", "Jose Rizal", "Emilio Aguinaldo", "Apolinario Mabini"],
    ),
    (
        "Which is the largest continent by land area?",
        "Asia",
        ["Africa", "Asia", "Europe", "North America"],
    ),
]
SAMPLE_TF_QUESTIONS = [
    ("Water boils at 100 degrees Celsius at sea level.", "True"),
    ("A triangle has four sides.", "False"),
    ("The Philippines is located in Asia.", "True"),
]
SAMPLE_FILL_QUESTIONS = [
    (
        "The process by which plants make their own food is called ____.",
        "photosynthesis",
    ),
    ("The sum of the angles in a triangle is ____ degrees.", "180"),
]
SAMPLE_ESSAY_QUESTIONS = [
    ("In your own words, explain why we should take care of the environment.", ""),
    ("Describe one Filipino value that is important to your family.", ""),
]


def seed_quiz_types():
    header("Quiz Types")
    if QuizType is None:
        log("quiz-type", "model not available — skipping")
        return {}
    out = {}
    for name in QUIZ_TYPE_NAMES:
        obj, created = QuizType.objects.get_or_create(name=name)
        out[name] = obj
        log("quiz-type", f"{'created' if created else 'exists'}: {name}")
    return out


def seed_question_bank(activities, quiz_types):
    header("Activity Questions + Choices")
    if ActivityQuestion is None or not activities:
        log("question", "model/data unavailable — skipping")
        return
    if not quiz_types:
        log("question", "quiz types missing — skipping")
        return

    rng = random.Random(101)
    mc_type = quiz_types.get("Multiple Choice")
    tf_type = quiz_types.get("True/False")
    fill_type = quiz_types.get("Fill in the Blank")
    essay_type = quiz_types.get("Essay")

    for act in activities:
        # Skip if questions already exist for this activity (idempotent).
        if ActivityQuestion.objects.filter(activity=act).exists():
            continue

        per_q_score = max(1, round(float(act.max_score or 100) / 5, 2))

        # Build a small mixed bank: 3 MC, 1 TF, 1 fill-in for quiz/exam style;
        # essays for "Project" / "Recitation".
        is_essay = act.activity_type and act.activity_type.name in (
            "Project",
            "Recitation",
        )

        if is_essay and essay_type is not None:
            for prompt, _ in SAMPLE_ESSAY_QUESTIONS:
                ActivityQuestion.objects.create(
                    activity=act,
                    subject=act.subject,
                    question_text=prompt,
                    correct_answer="",
                    quiz_type=essay_type,
                    score=per_q_score,
                )
            continue

        if mc_type is not None:
            for prompt, correct, choices in rng.sample(SAMPLE_MC_QUESTIONS, k=3):
                q = ActivityQuestion.objects.create(
                    activity=act,
                    subject=act.subject,
                    question_text=prompt,
                    correct_answer=correct,
                    quiz_type=mc_type,
                    score=per_q_score,
                )
                for choice in choices:
                    QuestionChoice.objects.create(
                        subject=act.subject,
                        question=q,
                        choice_text=choice,
                    )
        if tf_type is not None:
            prompt, correct = rng.choice(SAMPLE_TF_QUESTIONS)
            ActivityQuestion.objects.create(
                activity=act,
                subject=act.subject,
                question_text=prompt,
                correct_answer=correct,
                quiz_type=tf_type,
                score=per_q_score,
            )
        if fill_type is not None:
            prompt, correct = rng.choice(SAMPLE_FILL_QUESTIONS)
            ActivityQuestion.objects.create(
                activity=act,
                subject=act.subject,
                question_text=prompt,
                correct_answer=correct,
                quiz_type=fill_type,
                score=per_q_score,
            )
        log("question", f"+ {act.activity_name} (5 questions)")


# ---------------------------------------------------------------------------
# Gradebook configuration  (drives the My Grades page percentages)
# ---------------------------------------------------------------------------
# Per-quarter overall weight: numbers must sum to 100. The four DepEd quarters
# are weighted equally toward the final grade.
TERM_WEIGHTS = {
    "First Quarter": 25,
    "Second Quarter": 25,
    "Third Quarter": 25,
    "Fourth Quarter": 25,
}

# DepEd component weights within a quarter (general/typical). Sum must = 100.
CATEGORY_WEIGHTS = [
    ("Written Work", 30),
    ("Performance Task", 50),
    ("Quarterly Assessment", 20),
]

# Activity type → component + within-component weight (so the calc helper
# can derive (term, activity_type_name) → percentage from ATP rows).
# Within-component percentages must sum to the component's weight.
ACTIVITY_TYPE_TO_CATEGORY = [
    # (activity_type_name, gradebook_category, percentage_of_quarter)
    ("Written Work", "Written Work", 20),
    ("Recitation", "Written Work", 10),
    ("Performance Task", "Performance Task", 35),
    ("Project", "Performance Task", 15),
    ("Quarterly Assessment", "Quarterly Assessment", 20),
]


def seed_gradebook(subjects, terms, activity_types):
    header("Gradebook Components (drives student grade percentages)")
    if GradeBookComponents is None or TermGradeBookComponents is None:
        log("gradebook", "models not available — skipping")
        return
    if not subjects or not terms:
        log("gradebook", "subjects/terms missing — skipping")
        return

    for subj in subjects.values():
        teacher = subj.assign_teacher
        for term in terms:
            # Per-term overall weight (across the semester).
            t_pct = TERM_WEIGHTS.get(term.term_name, 25)
            tgb, _ = TermGradeBookComponents.objects.get_or_create(
                term=term,
                percentage=t_pct,
                defaults={"teacher": teacher, "base_grade": 50},
            )
            tgb.subjects.add(subj)

            # Three top-level components per (subject, term): Exam / Major / Part.
            cat_components = {}
            for cat_name, cat_pct in CATEGORY_WEIGHTS:
                comp, _ = GradeBookComponents.objects.get_or_create(
                    subject=subj,
                    term=term,
                    gradebook_category=cat_name,
                    defaults={
                        "teacher": teacher,
                        "gradebook_name": f"{cat_name} — {term.term_name}",
                        "percentage": cat_pct,
                    },
                )
                cat_components[cat_name] = comp

            # Per activity-type ATP rows live under the appropriate category.
            for at_name, cat_name, pct in ACTIVITY_TYPE_TO_CATEGORY:
                atype = activity_types.get(at_name)
                comp = cat_components.get(cat_name)
                if not atype or not comp:
                    continue
                ActivityTypePercentage.objects.get_or_create(
                    gradebook_component=comp,
                    activity_type=atype,
                    defaults={"percentage": pct},
                )
        log("gradebook", f"configured weights for {subj.subject_code}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    random.seed(42)  # deterministic likes/comments

    # ── Speed + offline: suppress network side-effects for the whole run ──
    # Creating activities / lessons / grades / badges cascades into Notification
    # rows whose post_save fires a OneSignal push — a blocking ~1–2s HTTPS call
    # dispatched on a thread that holds a SQLite connection. With no creds (and
    # no reachable network) those calls hang and starve the writer, turning a
    # ~10s seed into many minutes. The app already ships a thread-local
    # suppressor (used by the data-migration writer); we reuse it so seeding is
    # fast and fully offline. RAG embedding (OpenAI) on content save is
    # suppressed for the same reason. The guards are entered for the lifetime of
    # this single-threaded script — kept referenced so they aren't GC'd, and not
    # exited because the process ends right after main() returns.
    try:
        from migration.side_effects import (
            suppress_push_notifications,
            suppress_rag_indexing,
        )

        _push_guard = suppress_push_notifications()
        _push_guard.__enter__()
        _rag_guard = suppress_rag_indexing()
        _rag_guard.__enter__()
    except Exception as exc:  # pragma: no cover - defensive
        print(f"  [setup] could not enable side-effect suppression: {exc}")

    print("ClassEdge Basic Ed — dummy data seeder (Grade 7 demo)")
    print("=====================================================")

    roles = seed_roles()
    dept, course = seed_department_course()
    users = seed_users(roles, dept, course)
    seed_friendships(users)
    seed_chats(users)
    seed_group_chat(users)
    seed_posts(users)

    # ── Academic / activity data ────────────────────────────────────────────
    activity_types = {}
    semester, terms = None, []
    subjects = {}
    activities = []

    _safe(
        "activity-type",
        "activity types",
        lambda: activity_types.update(seed_activity_types()),
    )

    try:
        semester, terms = seed_semester_terms(dept)
    except Exception as exc:  # noqa: BLE001
        log("semester", f"⚠ skipped: {exc.__class__.__name__}: {exc}")

    quiz_types = {}

    _safe("subject", "subjects", lambda: subjects.update(seed_subjects(users)))
    _safe(
        "enrollment", "enrollments", lambda: seed_enrollments(users, subjects, semester)
    )
    _safe("lesson", "lessons (modules)", lambda: seed_lessons(subjects, terms))
    _safe(
        "gradebook",
        "gradebook config",
        lambda: seed_gradebook(subjects, terms, activity_types),
    )
    _safe(
        "activity",
        "assignments",
        lambda: activities.extend(seed_assignments(subjects, activity_types, terms)),
    )
    _safe("quiz-type", "quiz types", lambda: quiz_types.update(seed_quiz_types()))
    _safe(
        "question", "question bank", lambda: seed_question_bank(activities, quiz_types)
    )
    _safe(
        "grade",
        "grades / participation",
        lambda: seed_grades(users, subjects, terms, activities, semester),
    )
    _safe(
        "attendance", "attendance", lambda: seed_attendance(users, subjects, semester)
    )

    # ── Calendar / Gamification / Dashboard ─────────────────────────────────
    _safe("calendar", "calendar", lambda: seed_calendar(users, dept))
    _safe("gamification", "gamification", lambda: seed_gamification(users, subjects))
    _safe("quest", "quest map", lambda: seed_quest_map(users, subjects))
    _safe(
        "notif",
        "notifications",
        lambda: seed_dashboard_notifications(users, activities),
    )

    print("\n=== Done ===")
    print("Login uses EMAIL + password (not username).\n")
    print("Demo accounts (one per role):")
    print(f"  Student            → demo@basiced.dev          / demo123")
    print(f"  Teacher            → teacher@basiced.dev       / teacher123")
    for role_name, _u, _f, _l, email, password in ROLE_DEMOS:
        print(f"  {role_name:<18} → {email:<26}/ {password}")
    print()
    print(f"All other seeded users → password: {DEFAULT_PASSWORD}")
    print("Student emails follow the pattern <firstname>@basiced.dev, e.g.:")
    print("  alex@basiced.dev, bea@basiced.dev, carlo@basiced.dev,")
    print("  diane@basiced.dev, ej@basiced.dev, faye@basiced.dev,")
    print("  gio@basiced.dev, hana@basiced.dev, ivan@basiced.dev,")
    print("  jen@basiced.dev, kara@basiced.dev, leo@basiced.dev,")
    print("  mia@basiced.dev, nico@basiced.dev")
    print("Teacher emails: navarro@basiced.dev, aquino@basiced.dev,")
    print("  gdelacruz@basiced.dev, bramos@basiced.dev")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
