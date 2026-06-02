import json

from django import forms

from gamification.side_activity_models import SideActivity

WIDGET_STYLE = (
    "background:var(--surface-2);border:1px solid var(--border);"
    "color:var(--text);padding:.5rem;border-radius:6px;width:100%;"
)


class SideActivityForm(forms.ModelForm):
    content_text = forms.CharField(
        label="Content JSON",
        widget=forms.Textarea(attrs={
            "rows": 12,
            "style": f"{WIDGET_STYLE}font-family:monospace;",
            "placeholder": '{\n  "question": "...",\n  "answers": ["..."]\n}',
        }),
        help_text="Paste valid JSON that matches the chosen activity type schema.",
    )

    class Meta:
        model = SideActivity
        fields = ["sub_type", "title", "estimated_minutes", "xp_reward"]
        widgets = {
            "sub_type": forms.Select(attrs={"style": WIDGET_STYLE}),
            "title": forms.TextInput(attrs={"style": WIDGET_STYLE}),
            "estimated_minutes": forms.NumberInput(attrs={"style": WIDGET_STYLE, "min": 1}),
            "xp_reward": forms.NumberInput(attrs={"style": WIDGET_STYLE, "min": 1}),
        }

    def clean_content_text(self):
        raw = self.cleaned_data["content_text"]
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            raise forms.ValidationError(f"Invalid JSON: {exc}")
        return parsed

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.content_json = self.cleaned_data["content_text"]
        if commit:
            instance.save()
        return instance
