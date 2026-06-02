from django import forms
from django.utils import timezone
from subject.models import Subject
from course.models import Semester, Term, SubjectEnrollment

class SubjectChoiceField(forms.ModelMultipleChoiceField):
    """Custom field to display subject name with type"""
    def label_from_instance(self, obj):
        if obj.subject_type:
            return f"{obj.subject_name} - {obj.subject_type}"
        return obj.subject_name


class SingleSubjectChoiceField(forms.ModelChoiceField):
    """Same label rendering as SubjectChoiceField, but a single selection."""
    def label_from_instance(self, obj):
        if obj.subject_type:
            return f"{obj.subject_name} - {obj.subject_type}"
        return obj.subject_name

class CopyGradeBookForm(forms.Form):
    source_semester = forms.ModelChoiceField(
        queryset=Semester.objects.all(),
        label="Copy From Semester",
        widget=forms.Select(attrs={'class': 'form-select select2','data-live-search': 'true','data-actions-box': 'true','data-style': 'btn-outline-secondary','title': 'Select Semester'})
    )
    term = forms.ModelChoiceField(
        queryset=Term.objects.none(),
        label="Term",
        widget=forms.Select(attrs={'class': 'form-select select2','data-live-search': 'true','data-actions-box': 'true','data-style': 'btn-outline-secondary','title': 'Select Term'})
    )
    current_term = forms.ModelChoiceField(
        queryset=Term.objects.none(),
        label="Target Term (Current Semester)",
        widget=forms.Select(attrs={'class': 'form-control selectpicker','data-live-search': 'true','data-actions-box': 'true','data-style': 'btn-outline-secondary','title': 'Select Current Term'})
    )
    subject = SubjectChoiceField(
        queryset=Subject.objects.none(),
        label="Copy to",
        widget=forms.SelectMultiple(attrs={'class': 'form-control selectpicker','data-live-search': 'true','data-actions-box': 'true','data-style': 'btn-outline-secondary','title': 'Select Course'})
    )
    copy_from_subject = SingleSubjectChoiceField(
        queryset=Subject.objects.none(),
        label="Copy from",
        widget=forms.Select(attrs={'class': 'form-control selectpicker','data-live-search': 'true','data-actions-box': 'true','data-style': 'btn-outline-secondary','title': 'Copy From'})
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(CopyGradeBookForm, self).__init__(*args, **kwargs)

        self.fields['term'].empty_label = None
        self.fields['copy_from_subject'].empty_label = None

        source_semester = self.data.get("source_semester") or self.initial.get("source_semester")
        if source_semester:
            self.fields['term'].queryset = Term.objects.filter(semester=source_semester)
            self.fields['copy_from_subject'].queryset = Subject.objects.filter(
                gradebook_components__term__semester=source_semester
            ).distinct()

        today = timezone.now().date()
        current_semester = Semester.objects.filter(start_date__lte=today, end_date__gte=today).first()
        if current_semester:
            self.fields['current_term'].queryset = Term.objects.filter(semester=current_semester)
        else:
            self.fields['current_term'].queryset = Term.objects.none()

        if user and current_semester:
            if hasattr(user, 'profile') and user.profile.role and user.is_teacher:
                self.fields['subject'].queryset = Subject.objects.filter(
                    assign_teacher=user,
                    id__in=SubjectEnrollment.objects.filter(semester=current_semester).values_list('subject_id', flat=True)
                )
            else:
                self.fields['subject'].queryset = Subject.objects.filter(
                    id__in=SubjectEnrollment.objects.filter(semester=current_semester).values_list('subject_id', flat=True)
                )
        else:
            self.fields['subject'].queryset = Subject.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        source_semester = cleaned_data.get("source_semester")
        if source_semester:
            self.fields['term'].queryset = Term.objects.filter(semester=source_semester)
            self.fields['copy_from_subject'].queryset = Subject.objects.filter(
                gradebook_components__term__semester=source_semester
            ).distinct()
