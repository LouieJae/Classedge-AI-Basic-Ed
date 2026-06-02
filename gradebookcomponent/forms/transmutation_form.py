from django import forms
from django.core.exceptions import ValidationError
from gradebookcomponent.models import TransmutationRule

class Transmutation_form(forms.ModelForm):
    class Meta:
        model = TransmutationRule
        fields = '__all__'
        widgets = {
            'transmutation_table_name': forms.TextInput(attrs={'class': 'form-control'}),
            'min_grade': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'max_grade': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'transmuted_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    def clean(self):
        cleaned_data = super().clean()

        # Fetch and convert values
        min_grade = cleaned_data.get('min_grade')
        max_grade = cleaned_data.get('max_grade')
        transmuted_value = cleaned_data.get('transmuted_value')

        # Validate grades are numeric
        try:
            if min_grade is not None:
                min_grade = float(min_grade)
            if max_grade is not None:
                max_grade = float(max_grade)
            if transmuted_value is not None:
                transmuted_value = float(transmuted_value)
        except ValueError:
            raise ValidationError("Grades and transmuted values must be numeric.")

        # Custom validation logic
        if min_grade is not None and max_grade is not None and min_grade > max_grade:
            self.add_error('min_grade', "Minimum grade cannot be greater than maximum grade.")
        if transmuted_value is not None and transmuted_value < 0:
            self.add_error('transmuted_value', "Transmuted value must be non-negative.")

        return cleaned_data
