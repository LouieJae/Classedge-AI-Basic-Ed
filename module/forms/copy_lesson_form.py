from django import forms
from django.core.exceptions import ValidationError
from ..models import Module


class CopyLessonForm(forms.Form):
    selected_modules = forms.ModelMultipleChoiceField(
        queryset=Module.objects.none(),
        widget=forms.CheckboxSelectMultiple(),
        required=False
    )

    def __init__(self, *args, **kwargs):
        subject = kwargs.pop('subject', None)
        current_semester = kwargs.pop('current_semester', None)
        super().__init__(*args, **kwargs)

        self.subject = subject
        self.current_semester = current_semester

        # Filter modules to exclude those from the current semester
        if subject and current_semester:
            self.fields['selected_modules'].queryset = Module.objects.filter(
                subject=subject
            ).exclude(term__semester=current_semester).filter(term__isnull=False)

    def clean_selected_modules(self):
        selected_modules = self.cleaned_data.get('selected_modules')

        # Get all modules in the current semester
        existing_modules_in_current_semester = Module.objects.filter(
            subject=self.subject,
            term__semester=self.current_semester
        ).values_list('file_name', flat=True)

        # Check for duplicate modules
        duplicate_modules = []
        for module in selected_modules:
            if module.file_name in existing_modules_in_current_semester:
                duplicate_modules.append(module.file_name)

        # If duplicates are found, raise a validation error
        if duplicate_modules:
            raise ValidationError(
                f"The following lessons already exist in the current semester: {', '.join(duplicate_modules)}"
            )

        return selected_modules
