from rest_framework import serializers
from mobile.models import Attachment
import base64

class AttachmentSerializer(serializers.ModelSerializer):
    binary_file = serializers.SerializerMethodField()

    class Meta:
        model =  Attachment
        fields = '__all__'

    def get_binary_file(self, obj):
        if obj.file:
            try:
                with obj.file.open('rb') as f:
                    return base64.b64encode(f.read()).decode('utf-8')
            except Exception:
                return None
        return None
