from decimal import Decimal

from django import forms

from gradebookcomponent.models import GradeBookComponents


class GradeBookComponentsForm(forms.ModelForm):
    class Meta:
        model = GradeBookComponents
        fields = ["subject", "term", "gradebook_name", "gradebook_category", "percentage"]
        labels = {
            'subject': 'Course'
        }
        widgets = {
            "gradebook_name": forms.TextInput(attrs={"class": "form-control"}),
            "percentage": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "max": "100"}),
            "gradebook_category": forms.TextInput(attrs={
                "class": "form-control",
                "id": "gradebookCategory",
                "placeholder": "e.g. Quizzes, Performance Tasks, Exams",
                "list": "category-suggestions",
                "autocomplete": "off",
            }),
            "subject": forms.Select(attrs={"class": "selectpicker", "data-live-search": "true", "data-none-selected-text": "Select a course"}),
            "term": forms.Select(attrs={"class": "selectpicker", "data-live-search": "true", "data-none-selected-text": "Select a term"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user
        self.fields["gradebook_name"].required = False

    def clean(self):
        cleaned = super().clean()
        subject = cleaned.get("subject")
        term = cleaned.get("term")
        category = cleaned.get("gradebook_category")
        percentage = cleaned.get("percentage")

        if percentage is not None and (percentage <= 0 or percentage > 100):
            self.add_error("percentage", "Percentage must be between 0 and 100.")

        if subject and term and category:
            qs = GradeBookComponents.objects.filter(
                subject=subject, term=term, gradebook_category=category,
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error(
                    "gradebook_category",
                    f"{category} already exists for this course and term. "
                    "Each category can only be added once.",
                )

        if subject and term and percentage is not None:
            existing_qs = GradeBookComponents.objects.filter(subject=subject, term=term)
            if self.instance.pk:
                existing_qs = existing_qs.exclude(pk=self.instance.pk)
            existing_total = sum(Decimal(str(c.percentage)) for c in existing_qs)
            if existing_total + Decimal(str(percentage)) > 100:
                self.add_error(
                    "percentage",
                    f"Total percentage for this course and term would exceed 100%. "
                    f"Current total is {existing_total}%.",
                )

        return cleaned
