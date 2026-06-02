from migration.mappers.base import MapperResult, MissingFKError, register_mapper, require_fk
from migration.models import IDMap


@register_mapper("course", "AttendanceStatus")
def map_attendance_status(payload: dict) -> MapperResult:
    """Tiny lookup table — just the status string."""
    return MapperResult(
        fields={
            "status": payload.get("status"),
        },
    )


@register_mapper("course", "Attendance")
def map_attendance(payload: dict) -> MapperResult:
    """Per-student × course attendance row. Required FKs: student, subject.
    Nullable: status, teacher, schedule.
    """
    student_old = payload.get("student")
    subject_old = payload.get("subject")
    if not student_old:
        raise MissingFKError("accounts", "CustomUser", "(none)", field_name="student")
    if not subject_old:
        raise MissingFKError("subject", "Subject", "(none)", field_name="subject")
    return MapperResult(
        fields={
            "date": payload.get("date"),
            "remark": payload.get("remark"),
            "graded": payload.get("graded", False),
            "marked_at": payload.get("marked_at"),
            "self_marked": payload.get("self_marked", False),
            "student_id": require_fk("accounts", "CustomUser", student_old, field_name="student"),
            "subject_id": require_fk("subject", "Subject", subject_old, field_name="subject"),
            "status_id": IDMap.resolve("course", "AttendanceStatus", payload.get("status")) if payload.get("status") else None,
            "teacher_id": IDMap.resolve("accounts", "CustomUser", payload.get("teacher")) if payload.get("teacher") else None,
            "schedule_id": IDMap.resolve("subject", "Schedule", payload.get("schedule")) if payload.get("schedule") else None,
        },
    )


@register_mapper("course", "TeacherAttendancePoints")
def map_teacher_attendance_points(payload: dict) -> MapperResult:
    """Per teacher × attendance-status point value. Both FKs required."""
    teacher_old = payload.get("teacher")
    status_old = payload.get("status")
    if not teacher_old:
        raise MissingFKError("accounts", "CustomUser", "(none)", field_name="teacher")
    if not status_old:
        raise MissingFKError("course", "AttendanceStatus", "(none)", field_name="status")
    return MapperResult(
        fields={
            "points": payload.get("points", 0),
            "teacher_id": require_fk("accounts", "CustomUser", teacher_old, field_name="teacher"),
            "status_id": require_fk("course", "AttendanceStatus", status_old, field_name="status"),
        },
    )
