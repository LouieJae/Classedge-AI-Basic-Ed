from django.contrib import admin

from gamification.models import (
    StudentGamification,
    XPTransaction,
    BadgeDefinition,
    StudentBadge,
    CodingStats,
)
from gamification.side_activity_models import SideActivity, SideActivityAttempt
from gamification.teacher_models import (
    TeacherGamification,
    IPTransaction,
    TeacherBadgeDefinition,
    TeacherBadge,
    TeacherChallenge,
    TeacherChallengeProgress,
    TeacherRecognition,
    TeacherRating,
)


@admin.register(StudentGamification)
class StudentGamificationAdmin(admin.ModelAdmin):
    list_display = ("student", "current_level", "total_xp", "login_streak", "last_active_date")
    list_filter = ("current_level",)
    search_fields = ("student__username", "student__first_name", "student__last_name")
    ordering = ("-total_xp",)
    autocomplete_fields = ("student",)


@admin.register(XPTransaction)
class XPTransactionAdmin(admin.ModelAdmin):
    list_display = ("student", "amount", "reason", "source_type", "source_id", "created_at")
    list_filter = ("source_type", "created_at")
    search_fields = ("student__username", "reason")
    date_hierarchy = "created_at"
    autocomplete_fields = ("student",)


@admin.register(BadgeDefinition)
class BadgeDefinitionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "tier", "target_role", "is_active")
    list_filter = ("tier", "target_role", "is_active")
    search_fields = ("code", "name", "description")


@admin.register(StudentBadge)
class StudentBadgeAdmin(admin.ModelAdmin):
    list_display = ("student", "badge", "earned_at", "progress_percent", "is_featured", "awarded_by")
    list_filter = ("badge__tier", "is_featured", "earned_at")
    search_fields = ("student__username", "badge__name", "badge__code")
    autocomplete_fields = ("student", "badge", "awarded_by")
    date_hierarchy = "earned_at"


@admin.register(CodingStats)
class CodingStatsAdmin(admin.ModelAdmin):
    list_display = ("student", "total_submissions", "perfect_submissions", "total_katas", "current_streak", "best_streak")
    search_fields = ("student__username",)
    autocomplete_fields = ("student",)


@admin.register(SideActivity)
class SideActivityAdmin(admin.ModelAdmin):
    list_display = [f.name for f in SideActivity._meta.fields if f.name != "id"][:8]
    search_fields = ("title",) if any(f.name == "title" for f in SideActivity._meta.fields) else ()


@admin.register(SideActivityAttempt)
class SideActivityAttemptAdmin(admin.ModelAdmin):
    list_display = [f.name for f in SideActivityAttempt._meta.fields if f.name != "id"][:8]


@admin.register(TeacherGamification)
class TeacherGamificationAdmin(admin.ModelAdmin):
    list_display = [f.name for f in TeacherGamification._meta.fields if f.name != "id"][:8]
    search_fields = ("teacher__username", "teacher__first_name", "teacher__last_name") if any(f.name == "teacher" for f in TeacherGamification._meta.fields) else ()


@admin.register(IPTransaction)
class IPTransactionAdmin(admin.ModelAdmin):
    list_display = [f.name for f in IPTransaction._meta.fields if f.name != "id"][:8]


@admin.register(TeacherBadgeDefinition)
class TeacherBadgeDefinitionAdmin(admin.ModelAdmin):
    list_display = [f.name for f in TeacherBadgeDefinition._meta.fields if f.name != "id"][:8]
    search_fields = ("code", "name") if any(f.name in ("code", "name") for f in TeacherBadgeDefinition._meta.fields) else ()


@admin.register(TeacherBadge)
class TeacherBadgeAdmin(admin.ModelAdmin):
    list_display = [f.name for f in TeacherBadge._meta.fields if f.name != "id"][:8]


@admin.register(TeacherChallenge)
class TeacherChallengeAdmin(admin.ModelAdmin):
    list_display = [f.name for f in TeacherChallenge._meta.fields if f.name != "id"][:8]


@admin.register(TeacherChallengeProgress)
class TeacherChallengeProgressAdmin(admin.ModelAdmin):
    list_display = [f.name for f in TeacherChallengeProgress._meta.fields if f.name != "id"][:8]


@admin.register(TeacherRecognition)
class TeacherRecognitionAdmin(admin.ModelAdmin):
    list_display = [f.name for f in TeacherRecognition._meta.fields if f.name != "id"][:8]


@admin.register(TeacherRating)
class TeacherRatingAdmin(admin.ModelAdmin):
    list_display = [f.name for f in TeacherRating._meta.fields if f.name != "id"][:8]
