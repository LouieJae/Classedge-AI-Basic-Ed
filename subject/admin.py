from django.contrib import admin
from .models import Subject, Schedule, EvaluationQuestion, EvaluationAssignment, TeacherEvaluation, TeacherEvaluationResponse, SubjectCollaborator, SDG, SubjectGradeFinalization


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('subject_name', 'subject_code', 'assign_teacher', 'room_number', 'unit', 'is_coil', 'is_hali', 'status','subject_sync_id','subject_type' )
    list_filter = ('is_coil', 'is_hali', 'status', 'unit')
    search_fields = ('subject_name', 'subject_code', 'subject_short_name', 'subject_description', 'assign_teacher__first_name', 'assign_teacher__last_name', 'assign_teacher__email', 'room_number')
    filter_horizontal = ('collaborators', 'target_sdgs')
    list_per_page = 25
    fieldsets = (
        ('Basic Information', {
            'fields': ('subject_name', 'subject_descriptive_title', 'subject_short_name', 'subject_code', 'subject_photo', 'subject_description', 'subject_type','unit','subject_sync_id')
        }),
        ('Teacher Assignment', {
            'fields': ('assign_teacher', 'substitute_teacher', 'allow_substitute_teacher', 'collaborators')
        }),
        ('Location & Status', {
            'fields': ('room_number', 'status')
        }),
        ('COIL/HALI Information', {
            'fields': ('is_coil', 'is_hali', 'max_number_of_enrollees', 'number_of_enrollees', 'duration', 'industry_partners', 'highlight', 'target_sdgs', 'country'),
            'classes': ('collapse',)
        }),
        ('Issuance Information', {
            'fields': ('issued_by', 'issued_under', 'issued_on'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('subject', 'get_teacher_name', 'days_of_week', 'schedule_start_time', 'schedule_end_time', 'schedule_type', 'semester')
    list_filter = ('schedule_type', 'semester', 'days_of_week')
    search_fields = ('subject__subject_name', 'subject__subject_code', 'subject__assign_teacher__first_name', 'subject__assign_teacher__last_name')
    list_per_page = 25
    raw_id_fields = ('subject',)

    def get_teacher_name(self, obj):
        if obj.subject and obj.subject.assign_teacher:
            return f"{obj.subject.assign_teacher.first_name} {obj.subject.assign_teacher.last_name}"
        return "-"
    get_teacher_name.short_description = 'Teacher'
    get_teacher_name.admin_order_field = 'subject__assign_teacher'


@admin.register(EvaluationQuestion)
class EvaluationQuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('question_text',)
    list_per_page = 25


@admin.register(EvaluationAssignment)
class EvaluationAssignmentAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'subject', 'semester', 'is_visible')
    list_filter = ('is_visible', 'semester')
    search_fields = ('teacher__first_name', 'teacher__last_name', 'teacher__email', 'subject__subject_name', 'subject__subject_code')
    filter_horizontal = ('questions',)
    list_per_page = 25


@admin.register(TeacherEvaluation)
class TeacherEvaluationAdmin(admin.ModelAdmin):
    list_display = ('student', 'assignment', 'submitted_at')
    list_filter = ('submitted_at', 'assignment__semester')
    search_fields = ('student__first_name', 'student__last_name', 'student__email', 'assignment__teacher__first_name', 'assignment__teacher__last_name', 'general_feedback')
    readonly_fields = ('submitted_at',)
    list_per_page = 25


@admin.register(TeacherEvaluationResponse)
class TeacherEvaluationResponseAdmin(admin.ModelAdmin):
    list_display = ('evaluation', 'question', 'rating')
    list_filter = ('rating',)
    search_fields = ('evaluation__student__first_name', 'evaluation__student__last_name', 'question__question_text')
    list_per_page = 25


@admin.register(SubjectCollaborator)
class SubjectCollaboratorAdmin(admin.ModelAdmin):
    list_display = ('email', 'subject', 'user', 'accepted', 'invited_at')
    list_filter = ('accepted', 'invited_at')
    search_fields = ('email', 'subject__subject_name', 'user__first_name', 'user__last_name')
    readonly_fields = ('token', 'invited_at')
    list_per_page = 25


@admin.register(SDG)
class SDGAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25


@admin.register(SubjectGradeFinalization)
class SubjectGradeFinalizationAdmin(admin.ModelAdmin):
    list_display = ('subject', 'semester', 'is_finalized', 'finalized_at', 'finalized_by')
    list_filter = ('is_finalized', 'semester', 'finalized_at')
    search_fields = ('subject__subject_name', 'subject__subject_code', 'semester__semester_name', 'finalized_by__email')
    readonly_fields = ('finalized_at', 'finalized_by')
    list_per_page = 25
    raw_id_fields = ('subject', 'semester')
    
    fieldsets = (
        ('Subject & Semester', {
            'fields': ('subject', 'semester')
        }),
        ('Finalization Status', {
            'fields': ('is_finalized', 'finalized_at', 'finalized_by')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        # Auto-set finalized_by when marking as finalized
        if obj.is_finalized and not obj.finalized_by:
            obj.finalized_by = request.user
            from django.utils import timezone
            obj.finalized_at = timezone.now()
        # Clear finalized_by when unmarking
        elif not obj.is_finalized:
            obj.finalized_by = None
            obj.finalized_at = None
        super().save_model(request, obj, form, change)