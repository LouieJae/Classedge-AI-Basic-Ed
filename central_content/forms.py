# central_content/forms.py
from django import forms

from central_content.models import CentralSubject, CentralModule, CentralActivity, School


class CentralSubjectForm(forms.ModelForm):
    class Meta:
        model = CentralSubject
        fields = [
            "subject_name",
            "subject_descriptive_title",
            "subject_short_name",
            "subject_code",
            "subject_type",
            "subject_description",
            "unit",
            "target_grade_level",
            "target_curriculum",
            "source_notes",
        ]
        widgets = {
            "subject_description": forms.Textarea(attrs={"rows": 4}),
            "source_notes": forms.Textarea(attrs={"rows": 2}),
        }


class CentralModuleForm(forms.ModelForm):
    class Meta:
        model = CentralModule
        fields = ["file_name", "description", "url", "iframe_code", "order"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ["name", "base_url", "is_active", "notes"]


class CentralActivityForm(forms.ModelForm):
    class Meta:
        model = CentralActivity
        fields = [
            "activity_name",
            "activity_type",
            "activity_instruction",
            "max_score",
            "time_duration",
            "passing_score",
            "passing_score_type",
            "max_retake",
            "retake_method",
            "shuffle_questions",
            "is_graded",
        ]
        widgets = {"activity_instruction": forms.Textarea(attrs={"rows": 4})}


class TextbookUploadForm(forms.Form):
    title = forms.CharField(max_length=200, required=False)
    file = forms.FileField()

    def clean_file(self):
        f = self.cleaned_data["file"]
        if not f.name.lower().endswith(".pdf"):
            raise forms.ValidationError("Only PDF files are accepted.")
        if f.size > 200 * 1024 * 1024:
            raise forms.ValidationError("File must be under 200 MB.")
        return f
