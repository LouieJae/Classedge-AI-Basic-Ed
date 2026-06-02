from rest_framework import serializers
from activity.models import RetakeRecord
from django.utils import timezone


class RetakeRecordSerializers(serializers.ModelSerializer):
    attempt_number = serializers.IntegerField(source='retake_number', read_only=True)
    is_submitted = serializers.SerializerMethodField()
    remaining_seconds = serializers.SerializerMethodField()

    class Meta:
        model = RetakeRecord
        fields = ['id', 'attempt_number', 'is_submitted', 'score', 'status',
                  'started_at', 'will_end_at', 'remaining_seconds']

    def get_is_submitted(self, obj):
        """Return True if status is 'submitted', False otherwise."""
        return obj.status == 'submitted'

    def get_remaining_seconds(self, obj):
        """Calculate remaining seconds for ongoing attempts."""
        if obj.status != 'ongoing' or not obj.will_end_at:
            return 0
        
        now = timezone.now()
        
        if obj.will_end_at > now:
            remaining = (obj.will_end_at - now).total_seconds()
            return int(remaining)
        return 0