from rest_framework import serializers
from module.models import Module

class LessonSerializer(serializers.ModelSerializer):
    lesson_name = serializers.CharField(source='file_name', read_only=True)
    lesson_description = serializers.CharField(source='description', read_only=True)
    lesson_file = serializers.SerializerMethodField()
    lesson_url = serializers.SerializerMethodField()
    lesson_type = serializers.SerializerMethodField()
    subject_id = serializers.IntegerField(source='subject.id', read_only=True)

    class Meta:
        model = Module
        fields = ['id', 'subject_id', 'lesson_name', 'lesson_description',
                  'lesson_file', 'lesson_url', 'lesson_type',
                  'start_date', 'end_date', 'allow_download']

    def get_lesson_file(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request and obj.file:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url if obj.file else None
        return None

    def get_lesson_url(self, obj):
        if obj.url:
            return obj.url
        elif obj.iframe_code:
            return obj.iframe_code
        return None

    def get_lesson_type(self, obj):
        if obj.file:
            file_extension = obj.file.name.lower().split('.')[-1]
            if file_extension in ['jpg', 'jpeg', 'png', 'gif']:
                return 'image'
            elif file_extension in ['mp4', '.avi', '.mov', '.wmv']:
                return 'video'
            elif file_extension in ['pdf', 'doc', 'docx', 'txt']:
                return 'document'
            else:
                return 'file'
        elif obj.url:
            return 'external_link'
        elif obj.iframe_code:
            return 'embedded_content'
        return 'unknown'
