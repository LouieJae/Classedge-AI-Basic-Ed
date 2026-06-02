from rest_framework import serializers
from accounts.models import APIKey

class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = '__all__'
        # Owner & key are controlled by the server, not the client
        read_only_fields = ("key", "owner", "created_at", "last_used_at")