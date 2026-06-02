from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory, BaseInlineFormSet
from gradebookcomponent.models import GradeBookComponents, ActivityTypePercentage


class ActivityTypePercentageForm(forms.ModelForm):
    class Meta:
        model = ActivityTypePercentage
        fields = ['activity_type', 'percentage']
        widgets = {
            'activity_type': forms.Select(attrs={
                'class': 'form-control selectpicker activity_type_select',
                'data-live-search': 'true',
                'data-style': 'btn-outline-secondary',
                'title': 'Select Activity Type'
            }),
            'percentage': forms.NumberInput(attrs={
                'class': 'form-control sub-activity-percentage',
                'step': '0.01'
            }),
        }


class BaseActivityTypePercentageFormSet(BaseInlineFormSet):
    def clean(self):
        """
        Validate sub-activities:
          1. No duplicate activity_type within the same category.
          2. Percentages of non-deleted rows sum to exactly 100%.
        """
        super().clean()
        if any(self.errors):
            # Don't compound errors that are already on individual rows.
            return

        seen_types = set()
        total_percentage = 0
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            activity_type = form.cleaned_data.get('activity_type')
            if activity_type is not None:
                if activity_type.pk in seen_types:
                    raise ValidationError(
                        f"Duplicate sub-activity: '{activity_type}' is already used in this category. "
                        "Each activity type can only appear once per category."
                    )
                seen_types.add(activity_type.pk)
            percentage = form.cleaned_data.get('percentage')
            if percentage:
                total_percentage += percentage

        if total_percentage != 100:
            raise ValidationError(f"The total percentage must equal 100%. Current total: {total_percentage}%")


# Create the formset for ActivityTypePercentage.
# extra=1 renders one blank row on create. We deliberately do NOT set
# min_num=1; that would render `min_num + extra = 2` blank rows on create.
# The "at least one row" requirement is enforced implicitly by the total=100%
# check (zero rows -> total 0 -> validation fails with a clear message).
ActivityTypePercentageFormSet = inlineformset_factory(
    GradeBookComponents,
    ActivityTypePercentage,
    form=ActivityTypePercentageForm,
    formset=BaseActivityTypePercentageFormSet,
    extra=1,
    can_delete=True,
)
