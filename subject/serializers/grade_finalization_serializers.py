from rest_framework import serializers
from subject.models import SubjectGradeFinalization, Subject
from course.models import Semester
from django.utils import timezone


class SubjectGradeFinalizationSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    semester_name = serializers.CharField(source='semester.semester_name', read_only=True)
    finalized_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = SubjectGradeFinalization
        fields = [
            'id',
            'subject',
            'subject_name',
            'semester',
            'semester_name',
            'is_finalized',
            'finalized_at',
            'finalized_by',
            'finalized_by_name',
        ]
        read_only_fields = ['finalized_at', 'finalized_by']
    
    def get_finalized_by_name(self, obj):
        if obj.finalized_by:
            return f"{obj.finalized_by.profile.first_name} {obj.finalized_by.profile.last_name}" if hasattr(obj.finalized_by, 'profile') else str(obj.finalized_by)
        return None
    
    def update(self, instance, validated_data):
        # If is_finalized is being set to True, record the timestamp and user
        if validated_data.get('is_finalized', False) and not instance.is_finalized:
            instance.finalized_at = timezone.now()
            instance.finalized_by = self.context['request'].user
        # If is_finalized is being set to False, clear the timestamp and user
        elif not validated_data.get('is_finalized', True) and instance.is_finalized:
            instance.finalized_at = None
            instance.finalized_by = None
        
        instance.is_finalized = validated_data.get('is_finalized', instance.is_finalized)
        instance.save()
        return instance


class SubjectGradeFinalizationListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list views"""
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    semester_name = serializers.CharField(source='semester.semester_name', read_only=True)
    
    class Meta:
        model = SubjectGradeFinalization
        fields = [
            'id',
            'subject',
            'subject_name',
            'semester',
            'semester_name',
            'is_finalized',
            'finalized_at',
        ]
