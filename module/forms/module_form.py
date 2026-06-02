import os
import re
from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from course.models import Term
from ..models import Module

# File upload constraints
ALLOWED_EXTENSIONS = [
    "pdf", "jpg", "jpeg", "png",
    "mp4", "avi", "mov", "wmv",
    "ppt", "pptx", "doc", "docx", "xls", "xlsx",
]
MAX_FILE_SIZE_MB = 30


class BaseModuleForm(forms.ModelForm):
    """Base form with common fields and validation for all module types"""
    
    class Meta:
        model = Module
        exclude = ['subject', 'file', 'url', 'iframe_code']
        widgets = {
            'file_name': forms.TextInput(attrs={'class': 'form-control'}),
            'term': forms.Select(attrs={
                'class': 'form-control select2',
                'title': 'Select Term'
            }),
            'allow_download': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'required': True}),
        }

    display_lesson_for_selected_users = forms.ModelMultipleChoiceField(
        queryset=get_user_model().objects.filter(profile__role__name__iexact='Student'),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control select2',
            'multiple': 'multiple',
            'data-placeholder': 'Pick students…',
        }),
    )

    def __init__(self, *args, **kwargs):
        current_semester = kwargs.pop('current_semester', None)
        subject = kwargs.pop('subject', None)
        super().__init__(*args, **kwargs)

        # Filter terms based on the current semester
        if current_semester:
            self.fields['term'].queryset = Term.objects.filter(semester=current_semester)
        else:
            self.fields['term'].queryset = Term.objects.none()

        # Ensure the term field doesn't have an empty first option
        self.fields['term'].empty_label = None

        # Filter the users to display only students enrolled in the selected subject
        if subject and current_semester:
            enrolled_students = get_user_model().objects.filter(
                profile__role__name__iexact='Student',
                subjectenrollment__subject=subject,
                subjectenrollment__semester=current_semester,
                subjectenrollment__status='enrolled'  # Only enrolled students
            ).distinct()
            self.fields['display_lesson_for_selected_users'].queryset = enrolled_students

        self.subject = subject

    def clean_start_date(self):
        """Convert naive datetime to timezone-aware datetime"""
        start_date = self.cleaned_data.get('start_date')
        if not start_date:
            raise forms.ValidationError("Please provide a start date.")
        if timezone.is_naive(start_date):
            return timezone.make_aware(start_date)
        return start_date

    def clean_end_date(self):
        """Convert naive datetime to timezone-aware datetime"""
        end_date = self.cleaned_data.get('end_date')
        if not end_date:
            raise forms.ValidationError("Please provide an end date.")
        if timezone.is_naive(end_date):
            return timezone.make_aware(end_date)
        return end_date

    def clean_term(self):
        """Validate that a term is selected"""
        term = self.cleaned_data.get('term')
        if not term:
            raise forms.ValidationError("Please select a term.")
        return term

    def clean_file(self):
        """Validate file type and size"""
        file = self.cleaned_data.get('file')
        if file:
            # Validate file extension
            file_extension = os.path.splitext(file.name)[1][1:].lower()
            if file_extension not in ALLOWED_EXTENSIONS:
                raise forms.ValidationError(
                    f"Unsupported file type: {file_extension.upper()}. "
                    f"Allowed types: {', '.join(ALLOWED_EXTENSIONS).upper()}."
                )
            
            # Validate file size
            file_size_mb = file.size / (1024 * 1024)
            if file_size_mb > MAX_FILE_SIZE_MB:
                raise forms.ValidationError(
                    f"File too large ({file_size_mb:.2f} MB). "
                    f"Maximum allowed size is {MAX_FILE_SIZE_MB} MB."
                )
        return file

    def clean(self):
        """Perform cross-field validation"""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        file_name = cleaned_data.get('file_name')
        term = cleaned_data.get('term')

        # Validate date range
        if start_date and end_date:
            if end_date < start_date:
                raise forms.ValidationError(
                    "End date must be later than the start date."
                )

        # Check for duplicate lesson name in the same semester
        if file_name and term and self.subject:
            existing_module = Module.objects.filter(
                subject=self.subject,
                term__semester=term.semester,
                file_name=file_name
            )
            # Exclude current instance if updating
            if self.instance.pk:
                existing_module = existing_module.exclude(pk=self.instance.pk)
            
            if existing_module.exists():
                raise forms.ValidationError(
                    f"A lesson with the name '{file_name}' already exists in this semester."
                )

        return cleaned_data


class moduleForm(BaseModuleForm):
    """Form for file upload lessons"""
    
    class Meta(BaseModuleForm.Meta):
        exclude = ['subject', 'url', 'iframe_code']
        widgets = {
            **BaseModuleForm.Meta.widgets,
            'file': forms.ClearableFileInput(attrs={'class': 'custom-file-input'}),
        }

    def clean_file(self):
        """Validate file type and size"""
        file = self.cleaned_data.get('file')
        if not file:
            raise forms.ValidationError("Please upload a file.")
        
        # Validate file extension
        file_extension = os.path.splitext(file.name)[1][1:].lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise forms.ValidationError(
                f"Unsupported file type: {file_extension.upper()}. "
                f"Allowed types: {', '.join(ALLOWED_EXTENSIONS).upper()}."
            )
        
        # Validate file size
        file_size_mb = file.size / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            raise forms.ValidationError(
                f"File too large ({file_size_mb:.2f} MB). "
                f"Maximum allowed size is {MAX_FILE_SIZE_MB} MB."
            )
        return file


class ModuleURLForm(BaseModuleForm):
    """Form for URL-based lessons"""
    
    class Meta(BaseModuleForm.Meta):
        exclude = ['subject', 'file', 'iframe_code']
        widgets = {
            **BaseModuleForm.Meta.widgets,
            'url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://example.com'}),
        }

    def clean_url(self):
        """Validate and extract URL from iframe if provided"""
        url = self.cleaned_data.get('url')
        if not url:
            raise forms.ValidationError("Please provide a URL.")
        
        # Check if it's an iframe and extract the src
        sway_match = re.search(r'src="([^"]+)"', url)
        if sway_match:
            return sway_match.group(1)
        return url


class ModuleEmbedForm(BaseModuleForm):
    """Form for embed/iframe code lessons"""
    
    class Meta(BaseModuleForm.Meta):
        exclude = ['subject', 'file', 'url']
        widgets = {
            **BaseModuleForm.Meta.widgets,
            'iframe_code': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': '<iframe src="..."></iframe>'
            }),
        }

    def clean_iframe_code(self):
        """Validate iframe code"""
        iframe_code = self.cleaned_data.get('iframe_code')
        if not iframe_code:
            raise forms.ValidationError("Please provide an embed/iframe code.")
        return iframe_code
