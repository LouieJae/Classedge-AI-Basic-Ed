import logging

from celery import shared_task
from django.conf import settings

from migration.models import MigrationJob
from .batch import migrate_model_batch

logger = logging.getLogger(__name__)

DEPENDENCY_ORDER: list[tuple[str, str]] = [
    # ─── Layer 1: Identity (people + their containers) ───
    ("roles", "Role"),
    ("accounts", "CustomUser"),
    ("accounts", "Department"),
    ("accounts", "Course"),            # display label: "Programs"
    ("accounts", "Profile"),           # FKs: User, Role, Course (Program), Department

    # ─── Layer 2: Time/Calendar ───
    ("course", "Semester"),
    ("course", "Term"),                # FK: Semester, CustomUser

    # ─── Layer 3: Lookups (small enum tables used by many later layers) ───
    ("activity", "ActivityType"),
    ("activity", "QuizType"),
    ("gradebookcomponent", "TransmutationRule"),

    # ─── Layer 4: Course (Subject) structure ───
    ("subject", "Subject"),            # display label: "Courses". FK: CustomUser (teacher)
    ("subject", "Schedule"),           # FK: Subject (required), Semester
    ("course", "SubjectEnrollment"),   # display label: "Course Enrollments". FK: Student, Subject, Semester

    # ─── Layer 5: Gradebook config (must precede student-side scores) ───
    ("gradebookcomponent", "GradeBookComponents"),       # FK: Teacher, Subject, ActivityType, Term
    ("gradebookcomponent", "ActivityTypePercentage"),    # FK: GradeBookComponents (req), ActivityType (req)
    ("gradebookcomponent", "TermGradeBookComponents"),   # FK: Teacher, Term (req)
    ("gradebookcomponent", "GradeVisibilitySettings"),   # FK: Teacher (req), Subject (req), Term

    # ─── Layer 6: Classroom (depends on Course + Teacher) ───
    ("classroom", "Teacher_Attendance"),   # FK: Subject, Teacher
    ("classroom", "Screenshot"),           # FK: Teacher_Attendance
    ("classroom", "Classroom_mode"),       # FK: Subject (OneToOne)

    # ─── Layer 6.5: Attendance (depends on Course + Schedule + Teacher) ───
    ("course", "AttendanceStatus"),                # lookup (Present/Absent/Late/...)
    ("course", "Attendance"),                      # required FKs: student, subject. nullable: status, teacher, schedule
    ("course", "TeacherAttendancePoints"),         # required FKs: teacher, status

    # ─── Layer 6.7: Course content (Modules) ───
    ("module", "Module"),                  # FK: Subject (req), Term. Downloads files from sim's MEDIA_ROOT.
    ("module", "StudentProgress"),         # FK: student (req), module, activity

    # ─── Layer 7: Activity authoring (teacher-created assessment content) ───
    ("activity", "Activity"),              # FK: ActivityType, Subject, Term
    ("activity", "ActivityQuestion"),      # FK: Activity, Subject, QuizType
    ("activity", "QuestionChoice"),        # FK: ActivityQuestion
    ("activity", "Rubrics"),               # FK: Teacher, Subject
    ("activity", "RubricsItem"),           # FK: ActivityQuestion, Rubrics

    # ─── Layer 8: Student-side assessment data (heaviest by volume) ───
    ("activity", "StudentActivity"),       # FK: Student, Activity, Term, Subject — invariant total_score
    ("activity", "StudentQuestion"),       # FK: Student, ActivityQuestion, Activity (CI grep guard exempt)
    ("activity", "RetakeRecord"),          # FK: StudentActivity, Student, Activity. retake_time preserved
    ("activity", "RetakeRecordDetail"),    # FK: RetakeRecord, Student, ActivityQuestion
    ("activity", "ScoreChangeLog"),        # FK: StudentActivity, ChangedBy. change_date preserved (append-only audit)

    # ─── Layer 9: Archives (source models dropped on new side) ───
    ("logs", "UserActivityLog"),           # archived into migration.LegacyAuditLog as raw JSON

    # Future entries (TBD): calendars.*, message.*, social_media.*, logs.Notification,
    # logs.UserSubjectLog, logs.SubjectLog, module.*, gamification.*,
    # subject.Evaluation*, coil.*, mobile.*
]


@shared_task(name="migration.tasks.run_migration_pipeline")
def run_migration_pipeline() -> dict:
    if not getattr(settings, "MIGRATION_ENABLED", False):
        return {"enabled": False}

    enqueued = []
    for app_label, model_name in DEPENDENCY_ORDER:
        job, _ = MigrationJob.objects.get_or_create(app_label=app_label, model_name=model_name)
        if job.status in ("pending", "running"):
            migrate_model_batch.delay(job_id=job.id)
            enqueued.append(job.id)
    return {"enabled": True, "enqueued_job_ids": enqueued}
