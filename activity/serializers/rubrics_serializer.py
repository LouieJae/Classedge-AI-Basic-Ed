from rest_framework import serializers
from activity.models import Rubrics


class RubricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rubrics
        fields = '__all__'
