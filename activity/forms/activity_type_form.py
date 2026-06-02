from django import forms
from activity.models import ActivityType


class activityTypeForm(forms.ModelForm):
    class Meta:
        model = ActivityType
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }
