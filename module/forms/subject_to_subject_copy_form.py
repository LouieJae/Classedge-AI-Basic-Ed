from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from subject.models import Subject
from ..models import Module


class SubjectToSubjectCopyForm(forms.Form):
    source_subject = forms.ModelChoiceField(
        queryset=Subject.objects.all(),
        required=True,
        label="Source Subject"
    )
    selected_modules = forms.ModelMultipleChoiceField(
        queryset=Module.objects.none(),
        widget=forms.CheckboxSelectMultiple(),
        required=False,
        label="Select Lessons to Copy"
    )

    def __init__(self, *args, **kwargs):
        target_subject = kwargs.pop('target_subject', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.target_subject = target_subject

        # Filter source subjects based on user permissions
        if user:
            if getattr(user.profile.role, 'name', '').lower() == 'admin':
                # Admins can copy from any subject
                pass
            else:
                # Teachers can only copy from subjects they're assigned to
                self.fields['source_subject'].queryset = Subject.objects.filter(
                    Q(assign_teacher=user) |
                    Q(substitute_teacher=user, allow_substitute_teacher=True) |
                    Q(collaborators=user)
                ).distinct().exclude(id=target_subject.id if target_subject else None)

        # If a source subject is provided in the POST data, filter modules for that subject
        if self.data.get('source_subject'):
            try:
                source_subject_id = int(self.data.get('source_subject'))
                source_subject = Subject.objects.get(id=source_subject_id)
                self.fields['selected_modules'].queryset = Module.objects.filter(
                    subject=source_subject
                )
            except (ValueError, Subject.DoesNotExist):
                self.fields['selected_modules'].queryset = Module.objects.none()
        else:
            self.fields['selected_modules'].queryset = Module.objects.none()

    def clean_selected_modules(self):
        selected_modules = self.cleaned_data.get('selected_modules')

        # Get all modules in the target subject
        existing_modules_in_target = Module.objects.filter(
            subject=self.target_subject
        ).values_list('file_name', flat=True)

        # Check for duplicate modules
        duplicate_modules = []
        for module in selected_modules:
            if module.file_name in existing_modules_in_target:
                duplicate_modules.append(module.file_name)

        # If duplicates are found, raise a validation error
        if duplicate_modules:
            raise ValidationError(
                f"The following lessons already exist in the target subject: {', '.join(duplicate_modules)}"
            )

        return selected_modules
