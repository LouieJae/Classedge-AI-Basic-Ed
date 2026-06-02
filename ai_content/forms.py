from django import forms

from ai_content.models import GenerationRequest


class GenerationRequestForm(forms.Form):
    topic = forms.CharField(max_length=200)
    objectives = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}))
    content_type = forms.ChoiceField(
        choices=GenerationRequest.ContentType.choices,
        initial=GenerationRequest.ContentType.BOTH,
        widget=forms.RadioSelect,
    )
    reference_file = forms.FileField(required=False)
    model_key = forms.ChoiceField(choices=[])

    def __init__(self, *args, model_keys=None, **kw):
        super().__init__(*args, **kw)
        if model_keys:
            self.fields["model_key"].choices = [(k, k) for k in model_keys]

    def clean_reference_file(self):
        f = self.cleaned_data.get("reference_file")
        if f and not f.name.lower().endswith(".pdf"):
            raise forms.ValidationError("Only PDF files are accepted.")
        if f and f.size > 50 * 1024 * 1024:
            raise forms.ValidationError("File must be under 50MB.")
        return f
