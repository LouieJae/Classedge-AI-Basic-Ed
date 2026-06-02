"""Display metadata for each entry in DEPENDENCY_ORDER.

Keeps the pipeline tasks free of UI concerns. The sequence view consumes this.
"""
from migration.tasks import DEPENDENCY_ORDER


METADATA = {
    ("roles", "Role"): {
        "label": "Roles",
        "description": "Import role definitions and their permission assignments.",
        "icon": "fa-user-shield",
        "color": "sky",
    },
    ("accounts", "CustomUser"): {
        "label": "Users",
        "description": "Import user accounts. Password hashes are preserved; existing users are skipped.",
        "icon": "fa-users",
        "color": "emerald",
    },
    ("accounts", "Department"): {
        "label": "Departments",
        "description": "Import academic departments (College of Computing, College of Arts, etc.).",
        "icon": "fa-building-columns",
        "color": "sky",
    },
    ("accounts", "Course"): {
        "label": "Programs",
        "description": "Import degree programs catalog (table is named accounts.Course internally). Department FK left NULL — sim doesn't track it.",
        "icon": "fa-graduation-cap",
        "color": "amber",
    },
    ("accounts", "Profile"): {
        "label": "Profiles",
        "description": "Import user profiles (OneToOne with User). 4 FKs (User, Role, Course, Department) soft-resolved. share_token is rotated per migration; share_enabled resets to False. Photos skipped.",
        "icon": "fa-id-card",
        "color": "sky",
    },
    ("course", "Semester"): {
        "label": "Semesters",
        "description": "Import semester definitions with date ranges, passing grade, and grade calc method.",
        "icon": "fa-calendar-days",
        "color": "emerald",
    },
    ("course", "Term"): {
        "label": "Terms",
        "description": "Import grading terms (Prelim, Midterm, Pre-Final, Final). Links to Semester via IDMap; missing semester left NULL.",
        "icon": "fa-calendar-week",
        "color": "sky",
    },
    ("subject", "Subject"): {
        "label": "Courses",
        "description": "Import courses (table is named subject.Subject internally). Teacher + substitute teacher FKs soft-resolved via IDMap. Photos skipped.",
        "icon": "fa-book",
        "color": "amber",
    },
    ("subject", "Schedule"): {
        "label": "Schedules",
        "description": "Import class schedules (time-of-day + days-of-week). Course FK required; rows referencing un-migrated courses fail with missing_fk.",
        "icon": "fa-clock",
        "color": "sky",
    },
    ("course", "SubjectEnrollment"): {
        "label": "Course Enrollments",
        "description": "Import student × course × semester enrollments (table is course.SubjectEnrollment internally). All three FKs nullable; un-migrated targets leave NULL. enrollment_date is reset to today on the new side (auto_now_add).",
        "icon": "fa-user-graduate",
        "color": "emerald",
    },
    ("classroom", "Teacher_Attendance"): {
        "label": "Teacher Sessions",
        "description": "Import in-class teacher session records (time_started/time_ended). Course + Teacher FKs soft-resolved.",
        "icon": "fa-chalkboard-user",
        "color": "amber",
    },
    ("classroom", "Screenshot"): {
        "label": "Screenshots",
        "description": "Import session screenshots — image files skipped (separate pipeline). teacher_attendance FK soft-resolved. timestamp reset to today.",
        "icon": "fa-camera",
        "color": "sky",
    },
    ("classroom", "Classroom_mode"): {
        "label": "Classroom Mode Settings",
        "description": "Import per-course Classroom Mode toggle (OneToOne with Course). Soft-resolved course FK; unique constraint may surface db_error on conflicts.",
        "icon": "fa-toggle-on",
        "color": "slate",
    },
    ("activity", "ActivityType"): {
        "label": "Activity Types",
        "description": "Lookup table for activity categories (Quiz, Assignment, etc.). No FKs.",
        "icon": "fa-tags",
        "color": "slate",
    },
    ("activity", "QuizType"): {
        "label": "Quiz Types",
        "description": "Lookup table for question types (Multiple Choice, Essay, True/False, etc.). No FKs.",
        "icon": "fa-list-check",
        "color": "slate",
    },
    ("activity", "Activity"): {
        "label": "Activities",
        "description": "Import teacher-authored activities (quizzes, assignments). FKs to ActivityType, Course, Term — soft-resolved. Instruction files skipped.",
        "icon": "fa-clipboard-list",
        "color": "amber",
    },
    ("activity", "ActivityQuestion"): {
        "label": "Activity Questions",
        "description": "Import individual questions belonging to activities. FKs to Activity, Course, QuizType — soft-resolved. Question instruction files skipped.",
        "icon": "fa-circle-question",
        "color": "sky",
    },
    ("activity", "QuestionChoice"): {
        "label": "Question Choices",
        "description": "Import multiple-choice / matching options. FK to ActivityQuestion soft-resolved. Choice images skipped. is_left_side preserved for Matching questions.",
        "icon": "fa-list-ol",
        "color": "emerald",
    },
    ("activity", "Rubrics"): {
        "label": "Rubrics",
        "description": "Import rubric definitions (per teacher × course). Teacher and Course FKs soft-resolved.",
        "icon": "fa-table-list",
        "color": "amber",
    },
    ("activity", "RubricsItem"): {
        "label": "Rubric Items",
        "description": "Import individual rubric criteria attached to questions. FKs to ActivityQuestion + Rubrics soft-resolved. Must precede StudentActivity for rubric-based grading.",
        "icon": "fa-list-check",
        "color": "sky",
    },
    ("activity", "StudentActivity"): {
        "label": "Student Activities",
        "description": "Import each student's attempt at an Activity (total_score, timing, retake count). 4 FKs soft-resolved. total_score copied verbatim (invariant assumed to hold on sim).",
        "icon": "fa-user-pen",
        "color": "amber",
    },
    ("activity", "StudentQuestion"): {
        "label": "Student Question Answers",
        "description": "Import per-question student answers + scores. CI grep-guard exempts migration/ — this is the legitimate writer. Uploaded files skipped.",
        "icon": "fa-pen-to-square",
        "color": "emerald",
    },
    ("activity", "RetakeRecord"): {
        "label": "Retake Records",
        "description": "Import retake attempts (rolled-up per attempt). 3 soft-resolved FKs. retake_time preserved via post-save update (bypasses auto_now_add).",
        "icon": "fa-rotate-right",
        "color": "sky",
    },
    ("activity", "RetakeRecordDetail"): {
        "label": "Retake Question Details",
        "description": "Import per-question details inside a retake attempt. 3 soft-resolved FKs. Uploaded files skipped.",
        "icon": "fa-clipboard-question",
        "color": "amber",
    },
    ("activity", "ScoreChangeLog"): {
        "label": "Score Change Log",
        "description": "Audit trail of score edits. change_date preserved via post-save update. FKs (student_activity, changed_by) are non-nullable — missing targets surface as db_error.",
        "icon": "fa-clock-rotate-left",
        "color": "slate",
    },
    ("gradebookcomponent", "TransmutationRule"): {
        "label": "Transmutation Rules",
        "description": "Grade transmutation tables (min_grade/max_grade → transmuted_value). No FKs, pure config.",
        "icon": "fa-table",
        "color": "slate",
    },
    ("gradebookcomponent", "GradeBookComponents"): {
        "label": "Gradebook Components",
        "description": "Per-teacher × course × term × activity-type gradebook weighting. All 4 FKs soft-resolved.",
        "icon": "fa-table-cells",
        "color": "amber",
    },
    ("gradebookcomponent", "ActivityTypePercentage"): {
        "label": "Activity Type Percentages",
        "description": "Child weighting under a GradeBookComponent. Both FKs required — missing parent surfaces as missing_fk.",
        "icon": "fa-percent",
        "color": "sky",
    },
    ("gradebookcomponent", "TermGradeBookComponents"): {
        "label": "Term Gradebook Components",
        "description": "Term-level gradebook config (percentage + base_grade per term). teacher nullable, term required.",
        "icon": "fa-square-poll-vertical",
        "color": "emerald",
    },
    ("gradebookcomponent", "GradeVisibilitySettings"): {
        "label": "Grade Visibility Settings",
        "description": "Per teacher × course × term grade visibility toggle. teacher + course required, term nullable.",
        "icon": "fa-eye",
        "color": "sky",
    },
    ("course", "AttendanceStatus"): {
        "label": "Attendance Statuses",
        "description": "Lookup table for attendance states (Present, Absent, Late, etc.). No FKs.",
        "icon": "fa-list",
        "color": "slate",
    },
    ("course", "Attendance"): {
        "label": "Attendance Records",
        "description": "Per-student × course attendance rows. student + course required; status/teacher/schedule soft-resolved.",
        "icon": "fa-clipboard-check",
        "color": "emerald",
    },
    ("course", "TeacherAttendancePoints"): {
        "label": "Teacher Attendance Points",
        "description": "Point values per teacher × attendance-status. Both FKs required.",
        "icon": "fa-star",
        "color": "amber",
    },
    ("module", "Module"): {
        "label": "Modules",
        "description": "Course content modules. Course (Subject) FK required, Term nullable. PDF/doc files DOWNLOADED from sim's MEDIA_ROOT via media-blob endpoint — files land under new MEDIA_ROOT/module/.",
        "icon": "fa-folder-open",
        "color": "sky",
    },
    ("module", "StudentProgress"): {
        "label": "Student Progress",
        "description": "Per-student progress on modules / activities. Student required; module + activity nullable.",
        "icon": "fa-chart-line",
        "color": "emerald",
    },
    ("logs", "UserActivityLog"): {
        "label": "User Activity Log (archive)",
        "description": "Source table dropped on new side. Each row is archived into migration.LegacyAuditLog as raw JSON. 210k+ rows on sim — uses heavier throttle.",
        "icon": "fa-box-archive",
        "color": "slate",
    },
}


def get_cards():
    """Return the ordered list of card descriptors for the sequence view."""
    out = []
    for app, model in DEPENDENCY_ORDER:
        meta = METADATA.get((app, model), {})
        out.append({
            "app": app,
            "model": model,
            "key": f"{app}.{model}",
            "label": meta.get("label", f"{app}.{model}"),
            "description": meta.get("description", ""),
            "icon": meta.get("icon", "fa-database"),
            "color": meta.get("color", "slate"),
        })
    return out
