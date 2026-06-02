from django.contrib import admin
from django.utils.html import format_html

from .models import Attachment


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "file_link",
        "kind",
        "profile",
        "subject",
        "lesson",
        "activity",
        "activity_question",
        "question_choice",
        "student_question",
        "student_activity",
        "record_details",
    )
    list_select_related = (
        "profile",
        "subject",
        "lesson",
        "activity",
        "activity_question",
        "question_choice",
        "student_question",
        "student_activity",
        "record_details",
    )
    list_filter = (
        ("lesson", admin.EmptyFieldListFilter),
        ("activity", admin.EmptyFieldListFilter),
        ("activity_question", admin.EmptyFieldListFilter),
        ("question_choice", admin.EmptyFieldListFilter),
        ("student_question", admin.EmptyFieldListFilter),
        ("student_activity", admin.EmptyFieldListFilter),
        ("record_details", admin.EmptyFieldListFilter),
        ("profile", admin.EmptyFieldListFilter),
        ("subject", admin.EmptyFieldListFilter),
    )
    search_fields = (
        "id",
        "file",
        "lesson__file_name",
        "activity__activity_name",
        "subject__subject_name",
    )
    raw_id_fields = (
        "profile",
        "subject",
        "lesson",
        "activity",
        "activity_question",
        "question_choice",
        "student_question",
        "student_activity",
        "record_details",
    )
    readonly_fields = ("file_link",)
    ordering = ("-id",)
    list_per_page = 50

    @admin.display(description="File")
    def file_link(self, obj):
        if not obj.file:
            return "—"
        return format_html('<a href="{}" target="_blank">{}</a>', obj.file.url, obj.file.name)

    @admin.display(description="Kind")
    def kind(self, obj):
        if obj.lesson_id:
            return "lesson"
        if obj.activity_id:
            return "activity instruction"
        if obj.activity_question_id:
            return "question instruction"
        if obj.question_choice_id:
            return "choice image"
        if obj.student_question_id:
            return "student question"
        if obj.student_activity_id:
            return "student activity"
        if obj.record_details_id:
            return "retake detail"
        if obj.profile_id:
            return "profile"
        if obj.subject_id:
            return "subject"
        return "—"
