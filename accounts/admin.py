from django import forms
from django.contrib import admin
from tinymce.widgets import TinyMCE
from .models import CustomUser, Profile, Course, Certificate, DisplayImage, StudentSDG, LoginHistory, Department, APIKey, UserLegalConsent, LegalDocument

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    search_fields = ('id', 'email', 'username')
    list_display = ('id', 'email', 'username', 'last_login')

@admin.register(Profile)
class ProjectAdmin(admin.ModelAdmin):
    search_fields = ('id', 'first_name','last_name')
    list_display = ('id', 'user','role','first_name','last_name','course','department_fields')
    raw_id_fields = ('role', 'course', 'department_fields')
    

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    search_fields = ('id', 'name')
    list_display = ('id', 'name')
    list_filter = ('name',)

@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'login_time', 'ip_address', 'get_user_agent_short')
    list_filter = ('login_time', 'user')
    search_fields = ('user__username', 'user__email', 'ip_address')
    readonly_fields = ('user', 'login_time', 'ip_address', 'user_agent')
    date_hierarchy = 'login_time'
    
    def get_user_agent_short(self, obj):
        """Display a shortened version of user agent"""
        if obj.user_agent:
            return obj.user_agent[:50] + '...' if len(obj.user_agent) > 50 else obj.user_agent
        return '-'
    get_user_agent_short.short_description = 'Browser/Device'


class LegalDocumentForm(forms.ModelForm):
    content = forms.CharField(widget=TinyMCE(attrs={"cols": 100, "rows": 30}))

    class Meta:
        model = LegalDocument
        fields = [
            "doc_type",
            "version",
            "title",
            "content",
            "is_active",
            "effective_date",
        ]


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    form = LegalDocumentForm
    list_display = (
        "doc_type",
        "version",
        "title",
        "is_active",
        "effective_date",
        "created_at",
    )
    list_filter = ("doc_type", "is_active")
    search_fields = ("version", "title")
    readonly_fields = ("created_by", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(UserLegalConsent)
class UserLegalConsentAdmin(admin.ModelAdmin):
    list_display = ("user", "_doc_type", "_version", "accepted_at", "ip_address")
    list_filter = ("document__doc_type",)
    search_fields = ("user__email", "user__username")
    readonly_fields = ("user", "document", "accepted_at", "ip_address", "user_agent")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Doc type", ordering="document__doc_type")
    def _doc_type(self, obj):
        return obj.document.doc_type

    @admin.display(description="Version", ordering="document__version")
    def _version(self, obj):
        return obj.document.version


admin.site.register(Certificate)
admin.site.register(DisplayImage)
admin.site.register(StudentSDG)
admin.site.register(Department)
admin.site.register(APIKey)
