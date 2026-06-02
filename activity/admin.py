from django.contrib import admin
from activity.models import Activity, ActivityType, QuizType, ActivityQuestion, StudentActivity, StudentQuestion, QuestionChoice, RetakeRecord, RetakeRecordDetail, ScoreChangeLog, Rubrics, RubricsItem


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('activity_name', 'subject', 'activity_type', 'term', 'start_time', 'end_time', 'status', 'max_score', 'passing_score', 'classroom_mode')
    list_filter = ('activity_type', 'status', 'term', 'subject', 'remedial', 'classroom_mode', 'shuffle_questions', 'start_time')
    search_fields = ('activity_name', 'subject__subject_name', 'subject__subject_code', 'activity_instruction')
    filter_horizontal = ('additional_modules', 'remedial_students')
    list_per_page = 25
    date_hierarchy = 'start_time'
    fieldsets = (
        ('Basic Information', {
            'fields': ('activity_name', 'activity_type', 'subject', 'term')
        }),
        ('Schedule', {
            'fields': ('start_time', 'end_time', 'time_duration', 'status')
        }),
        ('Scoring', {
            'fields': ('max_score', 'passing_score', 'passing_score_type', 'show_score')
        }),
        ('Retake Settings', {
            'fields': ('max_retake', 'retake_method')
        }),
        ('Advanced Options', {
            'fields': ('classroom_mode', 'shuffle_questions', 'remedial','is_graded', 'remedial_students', 'additional_modules', 'activity_instruction'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ActivityType)
class ActivityTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    list_per_page = 25


@admin.register(QuizType)
class QuizTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    list_filter = ('name',)
    search_fields = ('name',)
    list_per_page = 25


@admin.register(ActivityQuestion)
class ActivityQuestionAdmin(admin.ModelAdmin):
    list_display = ('get_activity_name', 'quiz_type', 'score', 'question_preview')
    list_filter = ('quiz_type', 'activity__activity_type', 'activity__subject')
    search_fields = ('question_text', 'correct_answer', 'activity__activity_name')
    list_per_page = 25
    
    def get_activity_name(self, obj):
        return obj.activity.activity_name if obj.activity else 'N/A'
    get_activity_name.short_description = 'Activity'
    get_activity_name.admin_order_field = 'activity__activity_name'
    
    def question_preview(self, obj):
        return obj.question_text[:100] + '...' if len(obj.question_text) > 100 else obj.question_text
    question_preview.short_description = 'Question Preview'


@admin.register(StudentActivity)
class StudentActivityAdmin(admin.ModelAdmin):
    list_display = ('student', 'activity', 'term', 'total_score', 'retake_count', 'is_editable', 'attendance_mode', 'start_time')
    list_filter = ('is_editable', 'attendance_mode', 'term', 'activity__activity_type', 'activity__subject', 'start_time')
    search_fields = (
        'student__first_name', 'student__last_name', 'student__email', 'student__student_id',
        'activity__activity_name', 'activity__subject__subject_name'
    )
    raw_id_fields = ('student',)
    list_per_page = 25
    date_hierarchy = 'start_time'
    readonly_fields = ('start_time', 'end_time')


@admin.register(StudentQuestion)
class StudentQuestionAdmin(admin.ModelAdmin):
    list_display = ('student', 'get_activity_name', 'get_question_preview', 'score', 'status', 'submission_time', 'is_participation')
    list_filter = ('status', 'is_participation', 'activity_question__quiz_type', 'submission_time')
    search_fields = (
        'student__first_name', 'student__last_name', 'student__email',
        'activity_question__question_text', 'activity_question__activity__activity_name',
        'student_answer'
    )
    raw_id_fields = ('student',)
    list_per_page = 25
    date_hierarchy = 'submission_time'
    readonly_fields = ('submission_time',)
    
    def get_activity_name(self, obj):
        return obj.activity_question.activity.activity_name if obj.activity_question and obj.activity_question.activity else 'N/A'
    get_activity_name.short_description = 'Activity'
    
    def get_question_preview(self, obj):
        if obj.activity_question:
            text = obj.activity_question.question_text
            return text[:50] + '...' if len(text) > 50 else text
        return 'N/A'
    get_question_preview.short_description = 'Question'


@admin.register(QuestionChoice)
class QuestionChoiceAdmin(admin.ModelAdmin):
    list_display = ('get_activity_name', 'get_question_preview', 'choice_text', 'is_left_side')
    list_filter = ('is_left_side', 'question__quiz_type')
    search_fields = ('choice_text', 'question__question_text', 'question__activity__activity_name')
    list_per_page = 25
    
    def get_activity_name(self, obj):
        return obj.question.activity.activity_name if obj.question and obj.question.activity else 'N/A'
    get_activity_name.short_description = 'Activity'
    
    def get_question_preview(self, obj):
        if obj.question:
            text = obj.question.question_text
            return text[:50] + '...' if len(text) > 50 else text
        return 'N/A'
    get_question_preview.short_description = 'Question'


@admin.register(RetakeRecord)
class RetakeRecordAdmin(admin.ModelAdmin):
    list_display = ('get_student', 'get_activity', 'retake_number', 'score', 'retake_time')
    list_filter = ('retake_number', 'retake_time', 'student_activity__activity__activity_type')
    search_fields = (
        'student_activity__student__first_name',
        'student_activity__student__last_name',
        'student_activity__student__email',
        'student_activity__activity__activity_name'
    )
    list_per_page = 25
    date_hierarchy = 'retake_time'
    readonly_fields = ('retake_time',)
    
    def get_student(self, obj):
        return obj.student_activity.student.get_full_name() if obj.student_activity and obj.student_activity.student else 'N/A'
    get_student.short_description = 'Student'
    get_student.admin_order_field = 'student_activity__student__first_name'
    
    def get_activity(self, obj):
        return obj.student_activity.activity.activity_name if obj.student_activity and obj.student_activity.activity else 'N/A'
    get_activity.short_description = 'Activity'
    get_activity.admin_order_field = 'student_activity__activity__activity_name'


@admin.register(RetakeRecordDetail)
class RetakeRecordDetailAdmin(admin.ModelAdmin):
    list_display = ('student', 'get_activity', 'get_question_preview', 'score', 'submission_time')
    list_filter = ('submission_time', 'activity_question__quiz_type')
    search_fields = (
        'student__first_name', 'student__last_name', 'student__email',
        'activity_question__question_text', 'activity_question__activity__activity_name',
        'student_answer'
    )
    raw_id_fields = ('student',)
    list_per_page = 25
    date_hierarchy = 'submission_time'
    readonly_fields = ('submission_time',)
    
    def get_activity(self, obj):
        return obj.activity_question.activity.activity_name if obj.activity_question and obj.activity_question.activity else 'N/A'
    get_activity.short_description = 'Activity'
    
    def get_question_preview(self, obj):
        if obj.activity_question:
            text = obj.activity_question.question_text
            return text[:50] + '...' if len(text) > 50 else text
        return 'N/A'
    get_question_preview.short_description = 'Question'


@admin.register(ScoreChangeLog)
class ScoreChangeLogAdmin(admin.ModelAdmin):
    list_display = ('get_student', 'get_activity', 'previous_score', 'new_score', 'changed_by', 'change_date')
    list_filter = ('change_date', 'changed_by')
    search_fields = (
        'student_activity__student__first_name',
        'student_activity__student__last_name',
        'student_activity__student__email',
        'student_activity__activity__activity_name',
        'changed_by__first_name',
        'changed_by__last_name'
    )
    raw_id_fields = ('changed_by',)
    list_per_page = 25
    date_hierarchy = 'change_date'
    readonly_fields = ('change_date',)
    
    def get_student(self, obj):
        return obj.student_activity.student.get_full_name() if obj.student_activity and obj.student_activity.student else 'N/A'
    get_student.short_description = 'Student'
    get_student.admin_order_field = 'student_activity__student__first_name'
    
    def get_activity(self, obj):
        return obj.student_activity.activity.activity_name if obj.student_activity and obj.student_activity.activity else 'N/A'
    get_activity.short_description = 'Activity'
    get_activity.admin_order_field = 'student_activity__activity__activity_name'


@admin.register(Rubrics)
class RubricsAdmin(admin.ModelAdmin):
    list_display = ('rubric_name', 'description_preview')
    search_fields = ('rubric_name', 'description')
    list_per_page = 25
    
    def description_preview(self, obj):
        if obj.description:
            return obj.description[:100] + '...' if len(obj.description) > 100 else obj.description
        return 'N/A'
    description_preview.short_description = 'Description'


@admin.register(RubricsItem)
class RubricsItemAdmin(admin.ModelAdmin):
    list_display = ('rubric', 'get_activity', 'get_question_preview', 'point')
    list_filter = ('rubric', 'activity_question__activity__activity_type')
    search_fields = (
        'rubric__rubric_name',
        'activity_question__question_text',
        'activity_question__activity__activity_name'
    )
    list_per_page = 25
    
    def get_activity(self, obj):
        return obj.activity_question.activity.activity_name if obj.activity_question and obj.activity_question.activity else 'N/A'
    get_activity.short_description = 'Activity'
    
    def get_question_preview(self, obj):
        if obj.activity_question:
            text = obj.activity_question.question_text
            return text[:50] + '...' if len(text) > 50 else text
        return 'N/A'
    get_question_preview.short_description = 'Question'