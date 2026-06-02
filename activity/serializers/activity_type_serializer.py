from rest_framework import serializers
from activity.models import ActivityType


class ActivityTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityType
        fields = '__all__'
