from django import forms
from django.utils import timezone
from subject.models import Subject
from course.models import Term, Semester
from gradebookcomponent.models import TermGradeBookComponents


class SubjectChoiceField(forms.ModelMultipleChoiceField):
    """Custom field to display subject name with type"""
    def label_from_instance(self, obj):
        if obj.subject_type:
            return f"{obj.subject_name} - {obj.subject_type}"
        return obj.subject_name


class TermGradeBookComponentsForm(forms.ModelForm):
    subjects = SubjectChoiceField(
        label='Courses',
        queryset=Subject.objects.none(),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control selectpicker',
            'data-actions-box': 'true',
            'data-live-search': 'true',
            'title': 'Select Course',
            'data-style': 'btn-outline-secondary',
        }),
        required=True
    )

    class Meta:
        model = TermGradeBookComponents
        fields = ['term', 'subjects', 'percentage', 'base_grade']
        labels = {
            'percentage': 'Grade Percentage',
            'base_grade': 'Base Grade',
            'subjects': 'Courses'
        }
        widgets = {
            'term': forms.Select(attrs={
                'class': 'form-control selectpicker',
                'data-actions-box': 'true',
                'data-live-search': 'true',
                'title': 'Select Term',
                'data-style': 'btn-outline-secondary',
            }),
            'percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'placeholder': 'Enter percentage (e.g., 50)'},),
            'base_grade': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'placeholder': 'Enter base grade (e.g., 50)'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(TermGradeBookComponentsForm, self).__init__(*args, **kwargs)

        # Remove default value for base_grade field on new forms
        if not self.instance.pk:
            self.fields['base_grade'].initial = None
        
        # Add a placeholder or title to the Select field
        self.fields['term'].empty_label = None

        # Get the current semester based on today's date
        today = timezone.now().date()
        current_semester = Semester.objects.filter(start_date__lte=today, end_date__gte=today).first()

        if user and current_semester:
            if user.is_superuser:
                # Admin users can see all terms and subjects in the current semester
                self.fields['term'].queryset = Term.objects.filter(semester=current_semester)
                self.fields['subjects'].queryset = Subject.objects.filter(
                    subjectenrollment__semester=current_semester
                ).distinct()
            else:
                # For teachers, only show terms and subjects assigned to them in the current semester
                self.fields['term'].queryset = Term.objects.filter(semester=current_semester)

                if self.data.get('term'):
                    # When a term is selected, filter subjects based on the selected term and teacher
                    try:
                        term_id = int(self.data.get('term'))
                        term = Term.objects.get(id=term_id, semester=current_semester)
                        self.fields['subjects'].queryset = Subject.objects.filter(
                            subjectenrollment__semester=current_semester,
                            assign_teacher=user
                        ).distinct()
                    except (ValueError, TypeError, Term.DoesNotExist):
                        self.fields['subjects'].queryset = Subject.objects.none()
                else:
                    # Default to showing all subjects assigned to the teacher in the current semester if no term is selected
                    self.fields['subjects'].queryset = Subject.objects.filter(
                        subjectenrollment__semester=current_semester,
                        assign_teacher=user
                    ).distinct()
