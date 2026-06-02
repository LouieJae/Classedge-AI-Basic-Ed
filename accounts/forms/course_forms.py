from accounts.models import Course, Department
from django import forms

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['name', 'short_name', 'department']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter course name'}),
            'short_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter short name'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].required = True
        self.fields['short_name'].required = True
        self.fields['department'].required = False
        self.fields['department'].queryset = Department.objects.order_by('name')
        self.fields['department'].empty_label = '— No department —'
