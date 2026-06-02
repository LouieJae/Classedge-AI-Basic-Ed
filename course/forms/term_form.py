from django import forms
from course.models import Term

class termForm(forms.ModelForm):
    class Meta:
        model = Term
        fields = ['semester', 'term_name', 'start_date', 'end_date']
        widgets = {
            'semester': forms.Select(attrs={
                'class': 'form-select select2',
                'data-live-search': 'true',
                'data-actions-box': 'true',
                'data-style': 'btn-outline-secondary',
                'title': 'Select Semester',
                'required': 'true',
            }),
            'term_name': forms.Select(attrs={
                'class': 'form-select select2',
                'data-live-search': 'true',
                'data-actions-box': 'true',
                'data-style': 'btn-outline-secondary',
                'title': 'Select Term Name', 
                'required': 'true',
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control', 
                'type': 'date', 
                'required': 'true',
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control', 
                'type': 'date', 
                'required': 'true',
            }),
        }

    def __init__(self, *args, **kwargs):
        super(termForm, self).__init__(*args, **kwargs)
        
        # Add a placeholder or title to the Select field for term_name
        self.fields['term_name'].empty_label = 'Select Term Name'
        self.fields['semester'].empty_label = 'Select Semester'

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        # Validation to check if start_date is before end_date
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("The start date cannot be later than the end date.")

        return cleaned_data

