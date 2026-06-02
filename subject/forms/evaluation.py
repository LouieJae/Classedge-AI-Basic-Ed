from django import forms
from subject.models import EvaluationQuestion, EvaluationAssignment


class EvaluationQuestionForm(forms.ModelForm):
    class Meta:
        model = EvaluationQuestion
        fields = ['question_text', 'is_active']
        labels = {
            'question_text': 'Question Text',
            'is_active': 'Active',
        }
        widgets = {
            'question_text': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class EvaluationAssignmentForm(forms.ModelForm):
    questions = forms.ModelMultipleChoiceField(
        queryset=EvaluationQuestion.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control js-choice',
            'multiple': 'multiple',
        }),
        required=True,
        label="Questions"
    )

    class Meta:
        model = EvaluationAssignment
        fields = ['subject', 'questions', 'is_visible']
        labels = {
            'is_visible': 'Make Evaluation Visible to Students',
        }
        widgets = {
            'teacher': forms.Select(attrs={'class': 'form-control'}),
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'semester': forms.Select(attrs={'class': 'form-control'}),
            'is_visible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class TeacherEvaluationForm(forms.Form):
    def __init__(self, *args, **kwargs):
        questions = kwargs.pop('questions')
        super().__init__(*args, **kwargs)

        # Dynamically create hidden rating fields for each question
        for question in questions:
            self.fields[f'rating_{question.id}'] = forms.CharField(
                label=question.question_text,
                widget=forms.HiddenInput(attrs={'class': 'form-control'}),
                required=True
            )

        # Add a single feedback field at the end
        self.fields['general_feedback'] = forms.CharField(
            label="Overall Feedback (optional)",
            widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            required=False
        )
