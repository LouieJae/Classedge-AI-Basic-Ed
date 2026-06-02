import json

from django import forms

from ide.models import CodingExercise


class CodingExerciseForm(forms.ModelForm):
    test_cases_text = forms.CharField(
        widget=forms.Textarea(attrs={
            "rows": 12,
            "style": "font-family: monospace;",
            "placeholder": '[{"input": "5\\n3", "expected_output": "8"}]',
        }),
        label="Test Cases (JSON)",
        help_text="JSON array. Each object must have 'expected_output'; 'input' is optional.",
    )

    class Meta:
        model = CodingExercise
        fields = [
            "language",
            "starter_code",
            "solution_code",
            "time_limit_seconds",
            "memory_limit_kb",
        ]
        widgets = {
            "starter_code": forms.Textarea(attrs={"rows": 8, "style": "font-family: monospace;"}),
            "solution_code": forms.Textarea(attrs={"rows": 8, "style": "font-family: monospace;"}),
        }

    def clean_test_cases_text(self):
        raw = self.cleaned_data["test_cases_text"]
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError(f"Invalid JSON: {exc}")

        if not isinstance(data, list) or len(data) == 0:
            raise forms.ValidationError("Test cases must be a non-empty JSON array.")

        for i, item in enumerate(data):
            if not isinstance(item, dict):
                raise forms.ValidationError(f"Test case {i + 1} must be a JSON object.")
            if "expected_output" not in item:
                raise forms.ValidationError(
                    f"Test case {i + 1} is missing 'expected_output'."
                )

        return data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.test_cases = self.cleaned_data["test_cases_text"]
        if commit:
            instance.save()
        return instance
