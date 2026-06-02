from django import forms
from activity.models import Activity, ActivityType
from course.models import Term
from accounts.models import CustomUser
from module.models.module import Module
from django.core.exceptions import ValidationError


class ActivityForm(forms.ModelForm):
    PASSING_SCORE_TYPE_CHOICES = [
        ('number', 'Number'),
        ('percentage', 'Percentage'),
    ]

    passing_score_type = forms.ChoiceField(
        choices=PASSING_SCORE_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    # Hidden field for module to maintain backward compatibility
    module = forms.ModelChoiceField(
        queryset=Module.objects.all(),
        required=False,
        widget=forms.HiddenInput()
    )
    

    class Meta:
        model = Activity
        fields = ['activity_name', 'activity_type', 'subject', 'term', 'module', 'additional_modules',
                 'start_time', 'end_time', 'show_score', 'remedial', 'remedial_students', 'time_duration',
                 'max_retake', 'retake_method','passing_score', 'passing_score_type', 'activity_instruction',
                 'activity_file_instruction', 'is_graded', 'shuffle_questions',
                 'allow_late_submission', 'late_submission_days', 'late_submission_penalty_percent']
        widgets = {
            'activity_name': forms.TextInput(attrs={'class': 'form-control'}),
            'activity_type': forms.Select(attrs={'class': 'form-control'}),
            'subject': forms.HiddenInput(),
            'term': forms.Select(attrs={'class': 'form-control'}),
            'additional_modules': forms.SelectMultiple(attrs={'class': 'form-control js-choice', 'multiple': 'multiple', 'required': True}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'show_score': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'remedial': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'remedial_students': forms.SelectMultiple(attrs={'class': 'form-control js-choice', 'multiple': 'multiple'}),
            'time_duration': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_retake': forms.NumberInput(attrs={'class': 'form-control'}),
            'passing_score': forms.NumberInput(attrs={'class': 'form-control'}),
            'passing_score_type':forms.Select(attrs={'class': 'form-control'}),
            'activity_instruction': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'activity_file_instruction': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'is_graded': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'shuffle_questions': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_late_submission': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'late_submission_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'late_submission_penalty_percent': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
        }

    def __init__(self, *args, **kwargs):
        terms_queryset = kwargs.pop('terms_queryset', None)
        super(ActivityForm, self).__init__(*args, **kwargs)
        self.fields['activity_type'].queryset = ActivityType.objects.all()
        self.fields['term'].queryset = Term.objects.all()
        self.fields['remedial_students'].queryset = CustomUser.objects.filter(profile__role__name__iexact='Student')
        self.fields['module'].queryset = Module.objects.all()
        self.fields['module'].required = False
        self.fields['additional_modules'].queryset = Module.objects.all()
        self.fields['additional_modules'].required = False

        if terms_queryset is not None:
            self.fields['term'].queryset = terms_queryset
        else:
            self.fields['term'].queryset = Term.objects.none()

        if not self.instance.remedial:
            self.fields['remedial_students'].widget.attrs['style'] = 'display:none;'

        # Default passing score to 50 on the add form (no instance yet and no
        # value already supplied), so teachers see a sensible starting value.
        if not self.instance.pk and not self.initial.get('passing_score') and not self.data.get('passing_score'):
            self.fields['passing_score'].initial = 50

    def clean(self):
        cleaned_data = super().clean()
        # Lessons (additional_modules) are optional — an activity can stand
        # on its own without being attached to any lesson.
        cleaned_data['module'] = None
        return cleaned_data
