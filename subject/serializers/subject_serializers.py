from rest_framework import serializers
from subject.models import Subject


class SubjectSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()
    assign_teacher_name = serializers.SerializerMethodField()

    @staticmethod
    def _teacher_first_last(user):
        if not user:
            return "", ""
        profile = getattr(user, "profile", None)
        first = (getattr(profile, "first_name", "") or user.first_name or "").strip()
        last = (getattr(profile, "last_name", "") or user.last_name or "").strip()
        return first, last

    def get_teacher_name(self, obj):
        first, _ = self._teacher_first_last(obj.assign_teacher)
        return first or None

    def get_assign_teacher_name(self, obj):
        if not obj.assign_teacher:
            return None
        first, last = self._teacher_first_last(obj.assign_teacher)
        full = f"{first} {last}".strip()
        return full or obj.assign_teacher.get_username()
    
    class Meta:
        model = Subject
        fields = (
            'id', 'subject_name', 'subject_code', 'subject_photo','teacher_name', 'assign_teacher_name',
            'room_number', 'subject_description', 'is_coil', 'is_hali','is_cte', 'subject_type'
        )
