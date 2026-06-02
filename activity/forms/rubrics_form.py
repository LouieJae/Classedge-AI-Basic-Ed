from django import forms
from django.db import models
from activity.models import Rubrics
from subject.models import Subject
from course.models import Semester

class SubjectChoiceField(forms.ModelChoiceField):
    """Custom ModelChoiceField to display subject name with type"""
    def label_from_instance(self, obj):
        if obj.subject_type:
            return f"{obj.subject_name} ({obj.subject_type})"
        return obj.subject_name

class RubricsForm(forms.ModelForm):
    subject = SubjectChoiceField(
        queryset=Subject.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True,
        label='Course'
    )
    
    class Meta:
        model = Rubrics
        fields = ['subject', 'rubric_name', 'description']
        widgets = {
            'rubric_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter rubric name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter description (optional)'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(RubricsForm, self).__init__(*args, **kwargs)
        
        if user:
            from django.utils import timezone
            today = timezone.now().date()
            current_semester = Semester.objects.filter(
                start_date__lte=today,
                end_date__gte=today
            ).first()

            is_teacher = getattr(user, 'role_name', None) == 'teacher'

            if not is_teacher:
                # Non-teachers (registrar / admin / program head / dean / etc.)
                # can pick from every subject in the current semester.
                if current_semester:
                    self.fields['subject'].queryset = Subject.objects.filter(
                        subjectenrollment__semester=current_semester
                    ).distinct().order_by('subject_name')
                else:
                    self.fields['subject'].queryset = Subject.objects.all().order_by('subject_name')
            elif current_semester:
                self.fields['subject'].queryset = Subject.objects.filter(
                    subjectenrollment__semester=current_semester
                ).filter(
                    models.Q(assign_teacher=user) | models.Q(collaborators=user)
                ).distinct().order_by('subject_name')
            else:
                self.fields['subject'].queryset = Subject.objects.filter(
                    models.Q(assign_teacher=user) | models.Q(collaborators=user)
                ).distinct().order_by('subject_name')
