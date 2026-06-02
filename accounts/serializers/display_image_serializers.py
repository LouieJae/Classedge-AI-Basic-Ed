from rest_framework import serializers
from accounts.models import DisplayImage
    
class DisplayImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisplayImage
        fields = ['id', 'name', 'image', 'is_displayed']