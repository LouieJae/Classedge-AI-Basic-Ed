from django.contrib import admin
from .models import SubjectEnrollment, Semester, Term, StudentParticipationScore, Attendance, AttendanceStatus, Retake, TeacherAttendancePoints, StudentInvite


@admin.register(SubjectEnrollment)
class SubjectEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'semester', 'status', 'enrollment_date', 'can_view_grade','is_active_semester','student_name')
    list_filter = ('status', 'semester', 'can_view_grade', 'enrollment_date', 'drop_date','is_active_semester')
    search_fields = (
        'student__first_name', 'student__last_name', 'student__email', 'student__profile__id',
        'subject__subject_name', 'subject__subject_code','is_active_semester','student_name'
    )
    raw_id_fields = ('student', 'subject')
    list_per_page = 25
    date_hierarchy = 'enrollment_date'
    readonly_fields = ('enrollment_date',)
    fieldsets = (
        ('Enrollment Information', {
            'fields': ('student', 'subject', 'semester', 'enrollment_date','student_name')
        }),
        ('Status', {
            'fields': ('status', 'drop_date', 'can_view_grade')
        }),
    )


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ('semester_name', 'start_date', 'end_date', 'end_semester', 'passing_grade', 'grade_calculation_method', 'create_at')
    list_filter = ('end_semester', 'grade_calculation_method', 'semester_name', 'create_at')
    search_fields = ('semester_name',)
    list_per_page = 25
    date_hierarchy = 'start_date'
    readonly_fields = ('create_at',)
    fieldsets = (
        ('Semester Information', {
            'fields': ('semester_name', 'start_date', 'end_date', 'end_semester')
        }),
        ('Grading Configuration', {
            'fields': ('passing_grade', 'grade_calculation_method')
        }),
        ('Metadata', {
            'fields': ('create_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ('term_name', 'semester', 'start_date', 'end_date', 'created_by')
    list_filter = ('term_name', 'semester', 'start_date', 'end_date')
    search_fields = ('term_name', 'semester__semester_name', 'created_by__first_name', 'created_by__last_name')
    raw_id_fields = ('created_by',)
    list_per_page = 25
    date_hierarchy = 'start_date'


@admin.register(StudentParticipationScore)
class StudentParticipationScoreAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'term', 'score', 'max_score', 'percentage')
    list_filter = ('term', 'subject')
    search_fields = (
        'student__first_name', 'student__last_name', 'student__email', 'student__profile__id',
        'subject__subject_name', 'subject__subject_code'
    )
    raw_id_fields = ('student', 'subject')
    list_per_page = 25
    
    def percentage(self, obj):
        if obj.max_score > 0:
            return f"{(obj.score / obj.max_score * 100):.2f}%"
        return "N/A"
    percentage.short_description = 'Percentage'


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'date', 'status', 'graded', 'teacher', 'schedule')
    list_filter = ('status', 'graded', 'date', 'subject', 'teacher')
    search_fields = (
        'student__first_name', 'student__last_name', 'student__email', 'student__profile__id',
        'subject__subject_name', 'subject__subject_code',
        'teacher__first_name', 'teacher__last_name',
        'remark'
    )
    raw_id_fields = ('student', 'teacher')
    list_per_page = 25
    date_hierarchy = 'date'
    fieldsets = (
        ('Attendance Information', {
            'fields': ('student', 'subject', 'date', 'status', 'schedule')
        }),
        ('Grading & Teacher', {
            'fields': ('graded', 'teacher')
        }),
        ('Additional Information', {
            'fields': ('remark',),
            'classes': ('collapse',)
        }),
    )


@admin.register(AttendanceStatus)
class AttendanceStatusAdmin(admin.ModelAdmin):
    list_display = ('status',)
    search_fields = ('status',)
    list_per_page = 25


@admin.register(Retake)
class RetakeAdmin(admin.ModelAdmin):
    list_display = ('subject_enrollment', 'retake_date', 'get_student', 'get_subject')
    list_filter = ('retake_date',)
    search_fields = (
        'subject_enrollment__student__first_name',
        'subject_enrollment__student__last_name',
        'subject_enrollment__student__email',
        'subject_enrollment__subject__subject_name',
        'subject_enrollment__subject__subject_code',
        'reason'
    )
    list_per_page = 25
    date_hierarchy = 'retake_date'
    readonly_fields = ('retake_date',)
    
    def get_student(self, obj):
        return obj.subject_enrollment.student.get_full_name() if obj.subject_enrollment.student else 'N/A'
    get_student.short_description = 'Student'
    get_student.admin_order_field = 'subject_enrollment__student__first_name'
    
    def get_subject(self, obj):
        return obj.subject_enrollment.subject.subject_name if obj.subject_enrollment.subject else 'N/A'
    get_subject.short_description = 'Subject'
    get_subject.admin_order_field = 'subject_enrollment__subject__subject_name'


@admin.register(TeacherAttendancePoints)
class TeacherAttendancePointsAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'status', 'points')
    list_filter = ('status', 'teacher')
    search_fields = ('teacher__first_name', 'teacher__last_name', 'teacher__email', 'status__status')
    raw_id_fields = ('teacher',)
    list_per_page = 25


@admin.register(StudentInvite)
class StudentInviteAdmin(admin.ModelAdmin):
    list_display = ('email', 'subject', 'accepted', 'invited_at')
    list_filter = ('accepted', 'invited_at', 'subject')
    search_fields = ('email', 'subject__subject_name', 'subject__subject_code')
    readonly_fields = ('token', 'invited_at')
    list_per_page = 25
    date_hierarchy = 'invited_at'
    fieldsets = (
        ('Invite Information', {
            'fields': ('email', 'subject', 'accepted')
        }),
        ('Metadata', {
            'fields': ('token', 'invited_at'),
            'classes': ('collapse',)
        }),
    )