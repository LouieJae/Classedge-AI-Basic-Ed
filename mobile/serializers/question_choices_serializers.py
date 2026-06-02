from rest_framework import serializers
from activity.models import QuestionChoice

class QuestionChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionChoice
        fields = ['id', 'choice_text', 'is_left_side']