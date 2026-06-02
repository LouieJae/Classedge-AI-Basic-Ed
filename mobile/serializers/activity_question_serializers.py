
from rest_framework import serializers
from activity.models import ActivityQuestion, StudentQuestion
from .question_choices_serializers import QuestionChoiceSerializer

class ActivityQuestionListSerializer(serializers.ModelSerializer):
    quiz_type = serializers.StringRelatedField()
    choices = serializers.SerializerMethodField()
    subject_id = serializers.IntegerField(source='activity.subject.id', read_only=True)
    activity_id = serializers.CharField(source='activity.pk', read_only=True)
    student_answer = serializers.SerializerMethodField()
    student_score = serializers.SerializerMethodField()

    class Meta:
        model = ActivityQuestion
        fields = [
            'id', 'quiz_type', 'choices', 'activity_id', 'subject_id',
            'question_text', 'score', 'student_answer', 'student_score'
        ]

    def get_choices(self, obj):
        if not obj.quiz_type:
            return None
        name = obj.quiz_type.name.lower()
        if name in ('multiple choice', 'matching type'):
            qs = obj.choices.all()
            return QuestionChoiceSerializer(qs, many=True).data
        return None

    def _get_student_question(self, obj):
        request = self.context.get('request')
        if not request or not getattr(request, 'user', None) or not request.user.is_authenticated:
            return None

        cache = getattr(self, '_student_question_cache', None)
        if cache is None:
            cache = {}
            setattr(self, '_student_question_cache', cache)

        key = obj.id
        if key in cache:
            return cache[key]

        sq = (StudentQuestion.objects
              .filter(student=request.user, activity_question=obj)
              .order_by('-id')
              .first())
        cache[key] = sq
        return sq

    def get_student_answer(self, obj):
        sq = self._get_student_question(obj)
        return sq.student_answer if sq else None

    def get_student_score(self, obj):
        sq = self._get_student_question(obj)
        return sq.score if sq else None
