from django import forms
from tinymce.widgets import TinyMCE

from accounts.models import LegalDocument


class LegalDocumentForm(forms.ModelForm):
    content = forms.CharField(
        widget=TinyMCE(attrs={"cols": 100, "rows": 30, "class": "form-control"}),
        help_text="HTML is sanitized on save.",
    )

    class Meta:
        model = LegalDocument
        fields = ["doc_type", "version", "title", "content", "effective_date", "is_active"]
        widgets = {
            "doc_type": forms.Select(attrs={"class": "form-select"}),
            "version": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 1.2.0"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "effective_date": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["effective_date"].input_formats = ["%Y-%m-%dT%H:%M"]
