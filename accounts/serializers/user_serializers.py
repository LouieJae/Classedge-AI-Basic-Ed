
from rest_framework import serializers
from accounts.models import CustomUser, Profile, UserLegalConsent

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'date_joined']

class ProfileSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(source='student_photo')
    year_level = serializers.CharField(source='grade_year_level')
    email = serializers.EmailField(source='user.email')
    role = serializers.CharField(source='role.name')
    course = serializers.SerializerMethodField()
    
    def get_course(self, obj):
        return obj.course.name if obj.course else ""

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=255)
    password = serializers.CharField(max_length=128, write_only=True)
    token = serializers.CharField(max_length=255, read_only=True)

    def validate(self, data):
        return data


class OTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True, min_length=6, max_length=6)

    def validate_otp(self, value):
        # Ensure OTP is numeric and exactly 6 digits
        if not value.isdigit():
            raise serializers.ValidationError("OTP must contain only digits.")
        return value


class SetNewPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=1)


class ProfileSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(source='student_photo')
    year_level = serializers.CharField(source='grade_year_level')
    email = serializers.EmailField(source='user.email')
    role = serializers.CharField(source='role.name')
    course = serializers.SerializerMethodField()
    
    def get_course(self, obj):
        return obj.course.name if obj.course else ""

    
    class Meta:
        model = Profile
        fields = ['id', 'phone_number','email', 'id_number','photo', 'first_name', 'last_name',
                  'date_of_birth', 'gender', 'nationality', 'address', 'id_number', 'year_level',
                  'course', 'department','role']


from accounts.serializers.legal_serializers import (
    UserLegalConsentSerializer,  # noqa: F401  re-exported for backwards compatibility
)
