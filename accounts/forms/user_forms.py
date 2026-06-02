
from django import forms
from django.db import models
from accounts.models import Profile, CustomUser
from captcha.fields import CaptchaField
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox

class CustomLoginForm(forms.Form):
    email = forms.CharField(
        label='',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-user', 'placeholder': 'Email'})
    )
    password = forms.CharField(
        label='',
        widget=forms.PasswordInput(attrs={'class': 'form-control form-control-user', 'placeholder': 'Password'})
    )
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox())

    
class profileForm(forms.ModelForm):

    phone_number = forms.CharField(
        required=False, 
        max_length=15, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number', 'inputmode': 'tel', 'pattern': r'^\+?\d{0,15}$', 'title': 'Digits only, optionally starting with +', 'autocomplete': 'tel', 'oninput': "this.value = this.value.replace(/[^0-9+]/g, '').replace(/(?!^)\\+/g, '');"})
    )

    class Meta:
        model = Profile
        fields = [
            'first_name', 'last_name','role', 'student_status', 'date_of_birth', 'student_photo', 
            'gender', 'nationality', 'address', 'phone_number', 'id_number', 
            'grade_year_level', 'course', 'department_fields',
        ]
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
            'student_status': forms.Select(attrs={
                'class': 'form-control selectpicker',
                'data-live-search': 'true',
                'title': "Select Status"
            }),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'student_photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'nationality': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control'}),
            'id_number': forms.TextInput(attrs={'class': 'form-control'}),
            'grade_year_level': forms.Select(attrs={
                'class': 'form-control selectpicker',
                'data-live-search': 'true',
                'title': "Select Grade Year Level"
            }),
            'course': forms.Select(attrs={'class': 'form-control'}),
            'department_fields': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(profileForm, self).__init__(*args, **kwargs)

        self.fields['student_status'].empty_label = None
        self.fields['grade_year_level'].empty_label = None

        self.fields['grade_year_level'].label = 'Year Level'
        self.fields['student_photo'].label = 'Photo'

        from accounts.models import Course, Department
        
        # Optimize querysets - fetch only necessary fields
        self.fields['course'].queryset = Course.objects.only('id', 'name').order_by('name')
        self.fields['department_fields'].queryset = Department.objects.only('id', 'name').order_by('name')

        phone_number = self.initial.get('phone_number', '') 
        if phone_number and not phone_number.startswith('+63'):
            self.initial['phone_number'] = '+63' + phone_number
        elif not phone_number:
            self.initial['phone_number'] = '+63'

    def clean_phone_number(self):
        phone_number = (self.cleaned_data.get('phone_number') or '').strip()

        if not phone_number or phone_number == '+63':
            return None

        import re as _re
        if not _re.fullmatch(r'\+?\d{7,15}', phone_number):
            raise forms.ValidationError(
                "Phone number may only contain digits (and an optional leading +)."
            )
        return phone_number


class ProgramHeadCreateForm(forms.Form):
    """[Classedge LMS] IT Admin form for creating a new Program Head user + profile in one step."""
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'first.last@school.edu'})
    )
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    id_number = forms.CharField(
        required=False,
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional'})
    )
    department_fields = forms.ModelChoiceField(
        required=False,
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='— Unassigned —',
        label='Department',
    )
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'At least 8 characters'}),
        help_text='Temporary password. The user will be prompted to change it on first login.',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from accounts.models import Department
        self.fields['department_fields'].queryset = Department.objects.only('id', 'name').order_by('name')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(f'A user with email "{email}" already exists.')
        return email


class StudentUpdateForm(forms.ModelForm):
    phone_number = forms.CharField(
        required=False,
        max_length=15, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number', 'inputmode': 'tel', 'pattern': r'^\+?\d{0,15}$', 'title': 'Digits only, optionally starting with +', 'autocomplete': 'tel', 'oninput': "this.value = this.value.replace(/[^0-9+]/g, '').replace(/(?!^)\\+/g, '');"})
    )

    class Meta:
        model = Profile
        fields = ['student_photo', 'phone_number', 'gender','id_number', 'date_of_birth' ,'address','grade_year_level','course','department_fields']
        widgets = {
            'student_photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control'}),
            'grade_year_level': forms.Select(attrs={'class': 'form-control'}),
            'course': forms.Select(attrs={'class': 'form-control'}),
            'department_fields': forms.Select(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'id_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(StudentUpdateForm, self).__init__(*args, **kwargs)
        self.fields['student_photo'].label = 'Photo'

        initial_phone_number = self.initial.get('phone_number', '')
        if initial_phone_number and not initial_phone_number.startswith('+63'):
            self.initial['phone_number'] = '+63' + initial_phone_number
        elif not initial_phone_number:
            self.initial['phone_number'] = '+63'

    def clean_phone_number(self):
        phone_number = (self.cleaned_data.get('phone_number') or '').strip()

        if not phone_number or phone_number == '+63':
            return None

        import re as _re
        if not _re.fullmatch(r'\+?\d{7,15}', phone_number):
            raise forms.ValidationError(
                "Phone number may only contain digits (and an optional leading +)."
            )
        return phone_number


class registrarProfileForm(forms.ModelForm):

    phone_number = forms.CharField(
        required=False, 
        max_length=15, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number', 'inputmode': 'tel', 'pattern': r'^\+?\d{0,15}$', 'title': 'Digits only, optionally starting with +', 'autocomplete': 'tel', 'oninput': "this.value = this.value.replace(/[^0-9+]/g, '').replace(/(?!^)\\+/g, '');"})
    )

    class Meta:
        model = Profile
        fields = [
            'student_status', 'first_name', 'last_name', 'date_of_birth', 'student_photo', 'gender', 
            'nationality', 'address', 'phone_number', 'id_number', 'grade_year_level', 'course'
        ] 
        widgets = {
            'student_status': forms.Select(attrs={
                'class': 'form-control selectpicker',
                'data-live-search': 'true',
                'title': "Select Status"
            }),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'student_photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'nationality': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control'}),
            'id_number': forms.TextInput(attrs={'class': 'form-control'}),
            'grade_year_level': forms.Select(attrs={
                'class': 'form-control selectpicker',
                'data-live-search': 'true',
                'title': "Select Grade Year Level"
            }),
            'course': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(registrarProfileForm, self).__init__(*args, **kwargs)

        self.fields['student_status'].empty_label = None
        self.fields['grade_year_level'].empty_label = None

        self.fields['grade_year_level'].label = 'Year Level'
        self.fields['student_photo'].label = 'Photo'

        phone_number = self.initial.get('phone_number', '')
        if phone_number and not phone_number.startswith('+63'):
            self.initial['phone_number'] = '+63' + phone_number
        elif not phone_number:
            self.initial['phone_number'] = '+63'

    def clean_phone_number(self):
        phone_number = (self.cleaned_data.get('phone_number') or '').strip()

        if not phone_number or phone_number == '+63':
            return None

        import re as _re
        if not _re.fullmatch(r'\+?\d{7,15}', phone_number):
            raise forms.ValidationError(
                "Phone number may only contain digits (and an optional leading +)."
            )
        return phone_number


class SetPasswordForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        max_length=255,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'})
    )
    id_number = forms.CharField(
        label="School ID",
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your school ID'})
    )
    password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter new password'}),
        required=False
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'}),
        required=False
    )
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox())

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password or confirm_password:
            if password != confirm_password:
                self.add_error("confirm_password", "Passwords do not match.")
        return cleaned_data
    

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    captcha =  ReCaptchaField(widget=ReCaptchaV2Checkbox())
    email = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
