from rest_framework import serializers
from .models import *
from django.utils.html import strip_tags

class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ['id', 'title', 'date', 'color','holiday_type']


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'title', 'description', 'start_date','end_date', 'time', 'location', 'created_at']
    
    def create(self, validated_data):
        # Strip HTML tags from description
        if 'description' in validated_data and validated_data['description']:
            validated_data['description'] = strip_tags(validated_data['description'])
        
        return Event.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        # Strip HTML tags from description
        if 'description' in validated_data and validated_data['description']:
            validated_data['description'] = strip_tags(validated_data['description'])
        
        # Update event fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        return instance

    
class AnnouncementSerializer(serializers.ModelSerializer):
    events = EventSerializer(many=True, read_only=True)
    event_ids = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=Event.objects.all(), 
        write_only=True, 
        required=False,
        source='events'
    )
    events_data = EventSerializer(many=True, write_only=True, required=False)
    created_by = serializers.SerializerMethodField()
    
    class Meta:
        model = Announcement
        fields = ['id', 'title', 'description', 'date', 'events', 'event_ids', 'events_data','created_at', 'created_by']
    
    def _absolute(self, path: str) -> str:
        if not path:
            return None
        req = self.context.get("request")
        if req:
            return req.build_absolute_uri(path)
        base = getattr(settings, "BASE_URL", "").rstrip("/")
        return f"{base}{path}" if base else path

    def get_created_by(self, obj):
        if not obj.created_by:
            return None
        
        name = f"{obj.created_by.first_name} {obj.created_by.last_name}"
        
        try:
            photo = getattr(getattr(obj.created_by, "profile", None), "student_photo", None)
            if photo:
                photo_url = self._absolute(photo.url)
                return {"name": name, "photo": photo_url}
        except Exception:
            pass
        
        return {"name": name, "photo": None}
    
    def create(self, validated_data):
        # Extract events_data if provided
        events_data = validated_data.pop('events_data', None)
        events = validated_data.pop('events', [])
        
        # Strip HTML tags from description
        if 'description' in validated_data and validated_data['description']:
            validated_data['description'] = strip_tags(validated_data['description'])
        
        # Create the announcement
        announcement = Announcement.objects.create(**validated_data)
        
        # Create new events if events_data is provided
        if events_data:
            created_events = []
            for event_data in events_data:
                event = Event.objects.create(
                    created_by=self.context['request'].user,
                    **event_data
                )
                created_events.append(event)
            announcement.events.set(created_events)
        
        # Link existing events if event_ids is provided
        if events:
            announcement.events.add(*events)
        
        return announcement
    
    def update(self, instance, validated_data):
        # Extract events_data if provided
        events_data = validated_data.pop('events_data', None)
        events = validated_data.pop('events', None)
        
        # Strip HTML tags from description
        if 'description' in validated_data and validated_data['description']:
            validated_data['description'] = strip_tags(validated_data['description'])
        
        # Update announcement fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Create new events if events_data is provided
        if events_data:
            created_events = []
            for event_data in events_data:
                event = Event.objects.create(
                    created_by=self.context['request'].user,
                    **event_data
                )
                created_events.append(event)
            instance.events.add(*created_events)
        
        # Update linked events if event_ids is provided
        if events is not None:
            instance.events.set(events)
        
        return instance

