from rest_framework import serializers
from course.models import SubjectEnrollment, Semester
from subject.models import Subject

class SubjectEnrollmentSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    subject_code = serializers.CharField(source='subject.subject_code', read_only=True)
    subject_description = serializers.CharField(source='subject.subject_description', read_only=True)
    subject_image = serializers.SerializerMethodField()
    teacher_name = serializers.SerializerMethodField()
    teacher_email = serializers.SerializerMethodField()
    semester_name = serializers.CharField(source='semester.semester_name', read_only=True)
    
    class Meta:
        model = SubjectEnrollment
        fields = ['id', 'subject_id','subject_name', 'subject_code', 'subject_description',
                  'subject_image', 'teacher_name', 'teacher_email', 'semester', 
                  'semester_name', 'enrollment_date', 'status', 'can_view_grade']
    
    def get_subject(self, obj):
        if obj.subject:
            request = self.context.get('request')
            image_url = None
            if obj.subject.subject_photo:
                if request:
                    image_url = request.build_absolute_uri(obj.subject.subject_photo.url)
                else:
                    image_url = obj.subject.subject_photo.url
            
            return {
                'id': obj.subject.id,
                'name': obj.subject.subject_name,
                'code': obj.subject.subject_code,
                'description': obj.subject.subject_description,
                'image': image_url,
                'teacher_name': self.get_teacher_name(obj),
                'teacher_email': self.get_teacher_email(obj)
            }
        return None
    
    def get_subject_image(self, obj):
        if obj.subject and obj.subject.subject_photo:
            request = self.context.get('request')
            if request and obj.subject.subject_photo:
                return request.build_absolute_uri(obj.subject.subject_photo.url)
            return obj.subject.subject_photo.url
        return None
    
    def get_teacher_name(self, obj):
        if obj.subject and obj.subject.assign_teacher:
            return obj.subject.assign_teacher.get_full_name()
        return None
    
    def get_teacher_email(self, obj):
        if obj.subject and obj.subject.assign_teacher:
            return obj.subject.assign_teacher.email
        return None