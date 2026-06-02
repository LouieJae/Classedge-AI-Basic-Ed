from django.contrib import admin
from django.utils.html import format_html
from .models import Teacher_Attendance, Classroom_mode, Screenshot


@admin.register(Teacher_Attendance)
class TeacherAttendanceAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "teacher",
        "time_started",
        "time_ended",
        "is_active",
        "manual_ended",
    )
    list_filter = ("is_active", "manual_ended", "subject", "teacher")
    search_fields = (
        "subject__subject_name",
        "teacher__first_name",
        "teacher__last_name",
    )
    readonly_fields = ("celery_task_id",)
    ordering = ("-time_started",)


@admin.register(Classroom_mode)
class ClassroomModeAdmin(admin.ModelAdmin):
    list_display = ("subject", "is_classroom_mode")
    list_filter = ("is_classroom_mode",)
    search_fields = ("subject__subject_name",)


@admin.register(Screenshot)
class ScreenshotAdmin(admin.ModelAdmin):
    list_display = ("teacher_attendance", "timestamp", "thumbnail")
    list_filter = ("timestamp", "teacher_attendance__teacher")
    search_fields = (
        "teacher_attendance__teacher__first_name",
        "teacher_attendance__teacher__last_name",
        "teacher_attendance__subject__subject_name",
    )

    def thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="80" height="80" style="object-fit:cover;" />', obj.image.url)
        return "—"

    thumbnail.short_description = "Screenshot"
