from rest_framework import serializers
from .models import Notification
class NotificationSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()
    created_by_photo = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = ('id', 'entity_id','user_id', 'entity_type', 'message', 'is_read', 'created_at', 'created_by', 'created_by_photo')
        
    def get_created_by(self, obj):
        try:
            user = obj.created_by
            if not user:
                return "Unknown User"
            
            # Try to get profile
            if hasattr(user, 'profile'):
                profile = user.profile
                if profile and profile.first_name and profile.last_name:
                    return f"{profile.first_name} {profile.last_name}"
                elif profile and profile.first_name:
                    return profile.first_name
                elif profile and profile.last_name:
                    return profile.last_name
            
            # Fallback to username
            return user.username if user.username else "Unknown User"
        except AttributeError:
            return "Unknown User"
        
    def get_created_by_photo(self, obj):
        try:
            user = obj.created_by
            if not user:
                return None
            
            if hasattr(user, 'profile') and user.profile:
                photo = user.profile.student_photo
                if photo:
                    request = self.context.get('request')
                    if request:
                        return request.build_absolute_uri(photo.url)
                    return photo.url
            return None
        except AttributeError:
            return None