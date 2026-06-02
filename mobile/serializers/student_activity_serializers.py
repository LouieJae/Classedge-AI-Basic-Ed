from rest_framework import serializers
from activity.models import StudentActivity, Activity
from activity.models import StudentQuestion
from accounts.models import CustomUser
from course.models import Term
from subject.models import Subject
from mobile.serializers.student_question_serializers import StudentQuestionSerializer
from mobile.serializers.retake_record import _validate_uploaded_file

class StudentActivitySerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    questions = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = StudentActivity
        fields = ['local_id', 'student', 'activity','term','student_name', 'retake_count',
                  'total_score', 'is_editable', 'retake_count', 'questions']
        
    def get_questions(self, obj):
        qs = (
            StudentQuestion.objects
            .filter(student=obj.student, activity=obj.activity)
            .select_related('activity', 'activity_question__quiz_type')
            .prefetch_related('activity_question__choices')
        )
        return StudentQuestionSerializer(qs, many=True, context=self.context).data


class StudentActivitySerializers(serializers.ModelSerializer):
    student_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='student'
    )
    activity_id = serializers.PrimaryKeyRelatedField(
        queryset=Activity.objects.all(), source='activity', required=False
    )
    term_id = serializers.PrimaryKeyRelatedField(
        queryset=Term.objects.all(), source='term'
    )
    subject_id = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(), source='subject'
    )

    class Meta:
        model = StudentActivity
        fields = ['student_id', 'activity_id', 'term_id', 'subject_id','file','local_id','activity_local_id',
                  'total_score', 'retake_count', 'is_editable']

    def to_internal_value(self, data):
        # Mobile clients sometimes send `"file": ""` or `"file": null` when the
        # form is reused without re-attaching a file. Strip those before
        # validation so they don't trigger validate_file's rejection.
        if data.get('file') in ('', None):
            try:
                data = data.copy()
            except Exception:
                data = dict(data)
            data.pop('file', None)
        return super().to_internal_value(data)

    def validate_file(self, value):
        return _validate_uploaded_file(value)

    def validate(self, attrs):
        if not attrs.get('activity') and attrs.get('activity_local_id'):
            try:
                attrs['activity'] = Activity.objects.get(pk=attrs['activity_local_id'])
            except Activity.DoesNotExist:
                raise serializers.ValidationError({'activity_local_id': 'Activity not found.'})
        return attrs
        