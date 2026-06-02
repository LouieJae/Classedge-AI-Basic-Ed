from django import forms
from subject.models import Subject
from accounts.models import CustomUser
from roles.models import Role


class subjectForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(subjectForm, self).__init__(*args, **kwargs)

        # Get all teachers
        teacher_role = Role.objects.get(name__iexact='teacher')
        teacher_queryset = CustomUser.objects.filter(profile__role=teacher_role)

        # Set choices for assign_teacher
        self.fields['assign_teacher'].queryset = teacher_queryset
        self.fields['assign_teacher'].empty_label = "Select Teacher"

        # Exclude the selected assign_teacher from the substitute_teacher choices
        if self.instance and self.instance.pk and self.instance.assign_teacher:
            self.fields['substitute_teacher'].queryset = teacher_queryset.exclude(id=self.instance.assign_teacher.id)
        else:
            self.fields['substitute_teacher'].queryset = teacher_queryset

        self.fields['substitute_teacher'].empty_label = "Select Substitute Teacher"

        # Mirror the backend-required fields onto the rendered HTML so the
        # browser surfaces inline validation messages before submit. The
        # view enforces these four; without the `required` attribute the
        # user gets a redirect-with-toast instead of an inline cue.
        for required_name in ('subject_name', 'assign_teacher', 'room_number', 'status'):
            field = self.fields.get(required_name)
            if not field:
                continue
            field.required = True
            field.widget.attrs['required'] = 'required'

    class Meta:
        model = Subject
        fields = '__all__'
        widgets = {
            'subject_name': forms.TextInput(attrs={'class': 'form-control'}),
            'subject_short_name': forms.TextInput(attrs={'class': 'form-control'}),
            'assign_teacher': forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': 'Select Teacher',
                'data-allow-clear': 'true'
            }),
            'substitute_teacher': forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': 'Select Substitute Teacher',
                'data-allow-clear': 'true'
            }),
            'is_hali': forms.CheckboxInput(attrs={'class': 'form-check-input hali-input'}), 
            'is_coil': forms.CheckboxInput(attrs={'class': 'form-check-input coil-input'}), 
            'is_cte': forms.CheckboxInput(attrs={'class': 'form-check-input cte-input'}),
            'allow_substitute_teacher': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'subject_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'subject_code': forms.TextInput(attrs={'class': 'form-control'}),
            'room_number': forms.TextInput(attrs={'class': 'form-control'}),
            'max_number_of_enrollees': forms.NumberInput(attrs={'class': 'form-control'}),
            'duration': forms.TextInput(attrs={'class': 'form-control'}),
            'industry_partners': forms.TextInput(attrs={'class': 'form-control'}),
            'highlight': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'unit': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': 'Select Teacher',
                'data-allow-clear': 'true'
            }),
            'target_sdgs': forms.SelectMultiple(attrs={'class': 'form-select select2'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'subject_type': forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': 'Select course type',
                'data-allow-clear': 'true',
            }),
        }


class subjectPhotoForm(forms.ModelForm):
    """ Form specifically for updating the subject photo and the allow substitute teacher"""
    class Meta:
        model = Subject
        fields = ['subject_photo', 'allow_substitute_teacher']


class CoilSubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['subject_name', 'assign_teacher', 'target_sdgs', 'duration', 
        'subject_description', 'industry_partners', 'issued_by', 'issued_on', 'issued_under']
        widgets = {
            'target_sdgs': forms.SelectMultiple(attrs={'class': 'form-select select2'}),
            'subject_description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'duration': forms.TextInput(attrs={'class': 'form-control'}),
            'industry_partners': forms.TextInput(attrs={'class': 'form-control'}),
            'issued_by': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Issued by (e.g. Holy Child Central College, Inc.)'}),
            'issued_on': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'subject_name': forms.TextInput(attrs={'class': 'form-control'}),
            'assign_teacher': forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': 'Select Teacher',
                'data-allow-clear': 'true'
            }),
            'issued_under': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Issued under (e.g. Holy Child Central College, Inc.)'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assign_teacher'].queryset = CustomUser.objects.filter(profile__role__name__iexact='teacher')
        self.fields['assign_teacher'].label_from_instance = lambda obj: f"{obj.get_full_name()} ({obj.email})"