from rest_framework import serializers
from activity.models import Activity, StudentActivity, RetakeRecord
from .retake_serializers import RetakeRecordSerializers


class LessonActivityListSerializer(serializers.ModelSerializer):
    # `id` is retained for API backward-compatibility; it now mirrors local_id (cuid string).
    id = serializers.CharField(source='local_id', read_only=True)
    activity_type_name = serializers.CharField(source='activity_type.name', read_only=True)
    student_retake_count = serializers.SerializerMethodField()
    remaining_attempts = serializers.SerializerMethodField()
    attempts = serializers.SerializerMethodField()
    ongoing_attempt = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = ['id', 'activity_name', 'activity_type', 'activity_type_name', 'subject_id',
                  'start_time', 'end_time',
                  'show_score', 'max_score', 'passing_score', 'passing_score_type',
                  'time_duration', 'max_retake', 'show_score',
                  'retake_method', 'activity_instruction', 'classroom_mode', 'shuffle_questions',
                  'student_retake_count', 'remaining_attempts', 'attempts', 'ongoing_attempt'
                  ]

    def get_student(self, obj):
        req = self.context.get('request')
        if req and req.user and req.user.is_authenticated:
            return req.user.id
        return None

    def get_student_retake_count(self, obj):
        """
        Prefer an annotated value (my_retake_count) if the view added it.
        Otherwise do a safe fallback lookup.
        """
        annotated = getattr(obj, 'my_retake_count', None)
        if annotated is not None:
            return annotated

        req = self.context.get('request')
        if not req or not req.user or not req.user.is_authenticated:
            return 0

        sa = (StudentActivity.objects
              .filter(student=req.user, activity=obj)
              .only('retake_count').order_by('-id').first())
        return sa.retake_count if sa else 0

    def get_student_retake_count(self, obj):
        """Return the number of retakes/attempts the student has made."""
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return 0
        
        # Count how many attempts the student has made
        return RetakeRecord.objects.filter(
            student_activity__activity=obj,
            student_activity__student=user
        ).count()

    def get_remaining_attempts(self, obj):
        """Calculate remaining attempts for the student."""
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return obj.max_retake
        
        # Count how many attempts the student has made
        attempt_count = RetakeRecord.objects.filter(
            student_activity__activity=obj,
            student_activity__student=user
        ).count()
        
        # Calculate remaining attempts
        remaining = obj.max_retake - attempt_count
        return max(0, remaining)  # Ensure it doesn't go negative

    def get_attempts(self, obj):
        """Return this student's RetakeRecord list for this activity, using the existing serializer."""
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return []

        # Same filter as your RetakeView: only this student + this activity
        retakes = (
            RetakeRecord.objects
            .filter(student_activity__activity=obj, student_activity__student=user)
            .order_by('-retake_number')
        )

        return RetakeRecordSerializers(retakes, many=True, context=self.context).data

    def get_ongoing_attempt(self, obj):
        """Return the ongoing attempt if one exists."""
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return None
        
        # Find ongoing attempt
        try:
            ongoing_retake = RetakeRecord.objects.get(
                student_activity__activity=obj,
                student_activity__student=user,
                status='ongoing'
            )
            return RetakeRecordSerializers(ongoing_retake, context=self.context).data
        except RetakeRecord.DoesNotExist:
            return None
        except RetakeRecord.MultipleObjectsReturned:
            # If multiple ongoing attempts exist, return the latest one
            ongoing_retake = RetakeRecord.objects.filter(
                student_activity__activity=obj,
                student_activity__student=user,
                status='ongoing'
            ).order_by('-retake_number').first()
            return RetakeRecordSerializers(ongoing_retake, context=self.context).data if ongoing_retake else None

