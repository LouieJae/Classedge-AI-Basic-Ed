from subject.models import Subject, Schedule
from rest_framework import serializers
from accounts.models import CustomUser
from django.conf import settings

class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'subject_name', 'subject_descriptive_title', 'subject_short_name', 
                  'subject_photo', 'subject_description', 'subject_code', 'room_number', 
                  'unit', 'status', 'duration', 'highlight', 'target_sdgs', 'country']


class StudentNameSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    student_photo = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ("id", "name", "student_photo")

    def get_name(self, obj):
        # Prefer get_full_name if available, else fallback
        full = getattr(obj, "get_full_name", lambda: "")() or ""
        if full.strip():
            return full.strip()
        first = getattr(obj, "first_name", "") or ""
        last  = getattr(obj, "last_name", "") or ""
        base  = (last + ", " + first).strip()
        return base or getattr(obj, "username", str(obj.id))
    
    def _absolute(self, path: str) -> str:
        if not path:
            return None
        req = self.context.get("request")
        if req:
            return req.build_absolute_uri(path)
        base = getattr(settings, "BASE_URL", "").rstrip("/")
        return f"{base}{path}" if base else path

    def get_student_photo(self, obj):
        try:
            photo = getattr(getattr(obj, "profile", None), "student_photo", None)
            if photo:
                return self._absolute(photo.url)
            return None
        except Exception:
            return None


class CurrentNextScheduleSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    subject_id = serializers.IntegerField(source='subject.id', read_only=True)
    assign_teacher = serializers.SerializerMethodField()
    room = serializers.CharField(source='subject.room_number', read_only=True)
    next_occurrence = serializers.SerializerMethodField()

    class Meta:
        model = Schedule
        fields = [
            'id', 'subject', 'subject_id', 'subject_name', 
            'schedule_start_time', 'schedule_end_time', 'days_of_week',
            'assign_teacher', 'room', 'next_occurrence'
        ]

    def get_assign_teacher(self, obj):
        """Get the active teacher for this subject."""
        subject = obj.subject
        if subject.allow_substitute_teacher and subject.substitute_teacher:
            teacher = subject.substitute_teacher
        else:
            teacher = subject.assign_teacher
        
        if teacher:
            return f"{teacher.first_name} {teacher.last_name}"
        return None

    def get_next_occurrence(self, obj):
        """Get next occurrence date from context if provided."""
        next_occurrence = self.context.get('next_occurrence')
        if next_occurrence:
            return next_occurrence.strftime('%Y-%m-%d')
        return None
