from django import forms
from course.models import Semester

class semesterForm(forms.ModelForm):
    class Meta:
        model = Semester
        fields = ['semester_name', 'start_date', 'end_date', 'passing_grade', 'grade_calculation_method']
        widgets = {
            'semester_name': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'passing_grade': forms.NumberInput(attrs={'class': 'form-control'}),
            'grade_calculation_method': forms.Select(attrs={'class': 'form-control'}),
        }
