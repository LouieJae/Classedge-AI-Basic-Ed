from django.contrib import admin

from .models.gradebook_model import ActivityTypePercentage, GradeBookComponents
from .models.grade_visibility_model import GradeVisibilitySettings
from .models.termbook_model import TermGradeBookComponents
from .models.transmutation_model import TransmutationRule


class ActivityTypePercentageInline(admin.TabularInline):
    model = ActivityTypePercentage
    extra = 0
    autocomplete_fields = ('activity_type',)
    readonly_fields = ('created_at', 'updated_at')
    fields = ('activity_type', 'percentage', 'created_at', 'updated_at')


@admin.register(GradeBookComponents)
class GradeBookComponentsAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'gradebook_category', 'gradebook_name', 'subject', 'term',
        'teacher', 'percentage_display', 'updated_at',
    )
    list_display_links = ('id', 'gradebook_category')
    list_filter = ('term', 'term__semester', 'subject', 'teacher', 'created_at')
    search_fields = (
        'gradebook_name', 'gradebook_category',
        'subject__subject_name', 'subject__subject_type',
        'term__term_name',
        'teacher__username', 'teacher__first_name', 'teacher__last_name',
    )
    autocomplete_fields = ('teacher', 'subject', 'term', 'activity_type')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    ordering = ('-updated_at',)
    list_per_page = 25
    inlines = [ActivityTypePercentageInline]
    fieldsets = (
        ('Ownership', {'fields': ('teacher', 'subject', 'term')}),
        ('Component', {'fields': ('gradebook_category', 'gradebook_name', 'percentage')}),
        ('Legacy', {'fields': ('activity_type',), 'classes': ('collapse',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('teacher', 'subject', 'term', 'term__semester')


@admin.register(ActivityTypePercentage)
class ActivityTypePercentageAdmin(admin.ModelAdmin):
    list_display = ('id', 'gradebook_component', 'activity_type', 'percentage', 'updated_at')
    list_display_links = ('id', 'gradebook_component')
    list_filter = ('activity_type', 'gradebook_component__term', 'gradebook_component__subject')
    search_fields = (
        'gradebook_component__gradebook_category',
        'gradebook_component__gradebook_name',
        'gradebook_component__subject__subject_name',
        'activity_type__type_name',
    )
    autocomplete_fields = ('gradebook_component', 'activity_type')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-updated_at',)
    list_per_page = 25

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'gradebook_component', 'gradebook_component__subject',
            'gradebook_component__term', 'activity_type',
        )


@admin.register(TermGradeBookComponents)
class TermGradeBookComponentsAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'term', 'semester_name', 'subject_list', 'teacher',
        'percentage', 'base_grade', 'updated_at',
    )
    list_display_links = ('id', 'term')
    list_filter = ('term', 'term__semester', 'teacher', 'created_at')
    search_fields = (
        'term__term_name',
        'subjects__subject_name', 'subjects__subject_type',
        'teacher__username', 'teacher__first_name', 'teacher__last_name',
    )
    autocomplete_fields = ('teacher', 'term', 'subjects')
    filter_horizontal = ('subjects',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    ordering = ('-updated_at',)
    list_per_page = 25

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('teacher', 'term', 'term__semester').prefetch_related('subjects')

    @admin.display(description='Semester', ordering='term__semester__semester_name')
    def semester_name(self, obj):
        return getattr(obj.term.semester, 'semester_name', '—') if obj.term_id else '—'

    @admin.display(description='Courses')
    def subject_list(self, obj):
        names = [s.subject_name for s in obj.subjects.all()[:3]]
        more = obj.subjects.count() - len(names)
        suffix = f' +{more} more' if more > 0 else ''
        return (', '.join(names) or '—') + suffix


@admin.register(GradeVisibilitySettings)
class GradeVisibilitySettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'teacher', 'subject', 'term', 'is_visible', 'updated_at')
    list_display_links = ('id', 'teacher')
    list_editable = ('is_visible',)
    list_filter = ('is_visible', 'term', 'subject', 'teacher')
    search_fields = (
        'teacher__username', 'teacher__first_name', 'teacher__last_name',
        'subject__subject_name', 'term__term_name',
    )
    autocomplete_fields = ('teacher', 'subject', 'term')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-updated_at',)
    list_per_page = 25

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('teacher', 'subject', 'term')


@admin.register(TransmutationRule)
class TransmutationRuleAdmin(admin.ModelAdmin):
    list_display = ('id', 'transmutation_table_name', 'min_grade', 'max_grade', 'transmuted_value')
    list_display_links = ('id', 'transmutation_table_name')
    list_filter = ('transmutation_table_name',)
    search_fields = ('transmutation_table_name', 'transmuted_value')
    ordering = ('transmutation_table_name', '-max_grade')
    list_per_page = 50
