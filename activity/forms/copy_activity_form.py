from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from subject.models import Subject
from activity.models import Activity


class SubjectToSubjectActivityCopyForm(forms.Form):
    source_subject = forms.ModelChoiceField(
        queryset=Subject.objects.all(),
        required=True,
        label="Source Subject"
    )
    selected_activities = forms.ModelMultipleChoiceField(
        queryset=Activity.objects.none(),
        widget=forms.CheckboxSelectMultiple(),
        required=False,
        label="Select Activities to Copy"
    )

    def __init__(self, *args, **kwargs):
        target_subject = kwargs.pop('target_subject', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.target_subject = target_subject

        # Filter source subjects based on user permissions
        if user:
            if hasattr(user, 'profile') and user.profile and user.profile.role and user.is_admin:
                pass
            else:
                self.fields['source_subject'].queryset = Subject.objects.filter(
                    Q(assign_teacher=user) |
                    Q(substitute_teacher=user, allow_substitute_teacher=True) |
                    Q(collaborators=user)
                ).distinct().exclude(id=target_subject.id if target_subject else None)

        # If a source subject is provided in the POST data, filter activities for that subject
        if self.data.get('source_subject'):
            try:
                source_subject_id = int(self.data.get('source_subject'))
                source_subject = Subject.objects.get(id=source_subject_id)
                self.fields['selected_activities'].queryset = Activity.objects.filter(
                    subject=source_subject
                )
            except (ValueError, Subject.DoesNotExist):
                self.fields['selected_activities'].queryset = Activity.objects.none()
        else:
            self.fields['selected_activities'].queryset = Activity.objects.none()

    def clean_selected_activities(self):
        selected_activities = self.cleaned_data.get('selected_activities')

        # Get all activities in the target subject
        existing_activities_in_target = Activity.objects.filter(
            subject=self.target_subject
        ).values_list('activity_name', flat=True)

        # Check for duplicate activities
        duplicate_activities = []
        for activity in selected_activities:
            if activity.activity_name in existing_activities_in_target:
                duplicate_activities.append(activity.activity_name)

        if duplicate_activities:
            raise ValidationError(
                f"The following activities already exist in the target subject: {', '.join(duplicate_activities)}"
            )

        return selected_activities
