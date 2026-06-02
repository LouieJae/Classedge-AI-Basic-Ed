from django import forms
from course.models import Attendance, TeacherAttendancePoints
from accounts.models import CustomUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.timezone import now

class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['student', 'status', 'remark', 'date', 'graded']
        widgets = {
            'student': forms.SelectMultiple(
                attrs={'class': 'selectpicker form-control',
                       'data-live-search': 'true',
                       'data-actions-box': 'true',
                       'data-style': 'btn-outline-secondary',
                       'title': 'Select a student',}
            ),
            'status': forms.RadioSelect(),
            'remark': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': 'required'}),
        }

    def __init__(self, *args, **kwargs):
        current_semester = kwargs.pop('current_semester', None)
        subject = kwargs.pop('subject', None)
        teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)

        if current_semester:
            self.instance.semester = current_semester

        if subject and current_semester:
            enrolled_students = CustomUser.objects.filter(
                subjectenrollment__subject=subject,
                subjectenrollment__semester=current_semester,
                subjectenrollment__status='enrolled',
                profile__role__name__iexact='Student'
            ).distinct()
            self.fields['student'].queryset = enrolled_students
        else:
            self.fields['student'].queryset = CustomUser.objects.none()

        if teacher:
            self.instance.teacher = teacher
            self.fields['teacher'].disabled = True

        self.fields['date'].required = True
        # Default the date to today and forbid future dates in the picker.
        today = now().date()
        self.fields['date'].initial = today
        self.fields['date'].widget.attrs['max'] = today.strftime('%Y-%m-%d')
        if current_semester:
            self.fields['date'].widget.attrs['min'] = current_semester.start_date.strftime('%Y-%m-%d')


class updateAttendanceForm(forms.ModelForm):
    graded = forms.BooleanField(required=False, label="Mark as Graded", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    class Meta:
        model = Attendance
        fields = ['status', 'remark', 'date', 'graded']
        widgets = {
            'status': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'remark': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super(updateAttendanceForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['graded'].initial = self.instance.graded

        self.fields['date'].widget.attrs['min'] = now().date().strftime('%Y-%m-%d')
        
        self.fields['status'].empty_label = None 
        self.fields['status'].choices = [(choice[0], choice[1]) for choice in self.fields['status'].choices if choice[0] != '']


class TeacherAttendancePointsForm(forms.ModelForm):
    class Meta:
        model = TeacherAttendancePoints
        fields = ['status', 'points']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select select2','data-style': 'btn-outline-secondary', 'title': 'Select Status'}),
            'points': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'max': '10', 'min': '0'}),
        }
    
    def __init__(self, *args, **kwargs):
        super(TeacherAttendancePointsForm, self).__init__(*args, **kwargs)
        # Points must be between 0 and 10 inclusive. The widget already enforces
        # min/max in the browser; validators run server-side so a hand-crafted
        # POST or JS-disabled client can't slip in a negative value.
        self.fields['points'].validators.append(MinValueValidator(0))
        self.fields['points'].validators.append(MaxValueValidator(10))

        # Add a placeholder or title to the Select field
        self.fields['status'].empty_label = None

    def clean_points(self):
        points = self.cleaned_data.get('points')
        if points is not None and points < 0:
            raise forms.ValidationError("Points cannot be negative.")
        return points