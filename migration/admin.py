from django.contrib import admin

from .models import IDMap, MigrationErrorRecord, MigrationJob, MigrationRunLog


@admin.register(MigrationJob)
class MigrationJobAdmin(admin.ModelAdmin):
    list_display = ("app_label", "model_name", "status", "rows_written", "rows_errored", "updated_at")
    list_filter = ("status",)


@admin.register(IDMap)
class IDMapAdmin(admin.ModelAdmin):
    list_display = ("app_label", "model_name", "old_pk", "new_pk", "created_at")
    search_fields = ("old_pk", "new_pk")


@admin.register(MigrationRunLog)
class MigrationRunLogAdmin(admin.ModelAdmin):
    list_display = ("job", "started_at", "rows_in_page", "rows_written", "rows_errored", "http_status")


@admin.register(MigrationErrorRecord)
class MigrationErrorRecordAdmin(admin.ModelAdmin):
    list_display = ("occurred_at", "job", "category", "old_pk", "resolved")
    list_filter = ("category", "resolved")
    search_fields = ("old_pk", "message")
