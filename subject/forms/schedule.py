from django import forms
from subject.models import Schedule


class scheduleForm(forms.ModelForm):
    days_of_week = forms.MultipleChoiceField(
        choices=Schedule.DAYS_OF_WEEK,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control js-choice',
            'multiple': 'multiple',
            'data-style': 'btn-outline-secondary',
        }),
    )

    class Meta:
        model = Schedule
        fields = ['subject', 'schedule_start_time', 'schedule_end_time', 'days_of_week', 'schedule_type']
        widgets = {
            'subject': forms.Select(attrs={'class': 'form-select select2', 'data-live-search': 'true'}),
            'schedule_start_time': forms.TimeInput(format='%H:%M', attrs={'class': 'form-control', 'type': 'time'}),
            'schedule_end_time': forms.TimeInput(format='%H:%M', attrs={'class': 'form-control', 'type': 'time'}),
            'schedule_type': forms.Select(attrs={'class': 'form-control'}),
        }
