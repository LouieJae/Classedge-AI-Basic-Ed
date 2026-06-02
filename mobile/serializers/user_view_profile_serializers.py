from rest_framework import serializers
from accounts.models import Profile

class UserViewProfileSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(source='student_photo')
    year_level = serializers.CharField(source='grade_year_level')
    email = serializers.EmailField(source='user.email')
    role = serializers.CharField(source='role.name')
    course = serializers.SerializerMethodField()
    needs_password_setup = serializers.BooleanField(source='user.needs_password_setup')
    needs_onboarding = serializers.BooleanField(source='user.legal_update_required')
    
    def get_course(self, obj):
        return obj.course.name if obj.course else ""

    
    class Meta:
        model = Profile
        fields = ['id', 'phone_number', 'email', 'id_number', 'photo', 'first_name', 'last_name',
                  'date_of_birth', 'gender', 'nationality', 'address', 'year_level',
                  'course', 'department_fields', 'role', 'needs_password_setup', 'needs_onboarding']
        