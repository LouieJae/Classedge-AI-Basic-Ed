from django import forms
from gamification.quest_settings_models import OrganizationQuestSettings


class OrganizationQuestSettingsForm(forms.ModelForm):
    class Meta:
        model = OrganizationQuestSettings
        fields = ["ai_mode_enabled", "manual_mode_enabled", "upload_mode_enabled", "ai_provider"]
