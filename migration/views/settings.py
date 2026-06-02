from django import forms
from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView

from migration.models import MigrationSettings

TOKEN_MASK = "••••••••"


class _SuperuserOnly(UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        return self.request.user.is_active and self.request.user.is_superuser


class MigrationSettingsForm(forms.Form):
    base_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            "class": "mig-input", "placeholder": "http://localhost:8001",
            "autocomplete": "off",
        }),
        help_text="Leave blank to use the .env default.",
    )
    token = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False, attrs={
            "class": "mig-input", "placeholder": TOKEN_MASK,
            "autocomplete": "new-password",
        }),
        help_text="Leave blank to keep the existing token.",
    )


class SettingsView(_SuperuserOnly, FormView):
    template_name = "migration/settings.html"
    form_class = MigrationSettingsForm
    success_url = reverse_lazy("migration:settings")

    def get_initial(self):
        row = MigrationSettings.load()
        return {"base_url": row.base_url}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        row = MigrationSettings.load()
        ctx["row"] = row
        ctx["has_token"] = bool(row.token)
        ctx["env_base_url"] = django_settings.MIGRATION_OLD_LMS_BASE_URL
        ctx["env_has_token"] = bool(django_settings.MIGRATION_OLD_LMS_TOKEN)
        ctx["effective_base_url"] = row.effective_base_url()
        ctx["effective_has_token"] = bool(row.effective_token())
        ctx["old_lms_base_url"] = row.effective_base_url()
        ctx["poll_seconds"] = django_settings.MIGRATION_DASHBOARD_POLL_SECONDS
        ctx["dry_run"] = django_settings.MIGRATION_DRY_RUN
        return ctx

    def form_valid(self, form):
        row = MigrationSettings.load()
        row.base_url = form.cleaned_data["base_url"] or ""
        token = form.cleaned_data["token"]
        # Only overwrite the token when a new value is typed; empty input keeps the stored one.
        if token:
            row.token = token
        row.updated_by = self.request.user if self.request.user.is_authenticated else None
        row.save()
        messages.success(self.request, "Migration settings saved.")
        return redirect(self.success_url)

    def post(self, request, *args, **kwargs):
        if "clear_token" in request.POST:
            row = MigrationSettings.load()
            row.token = ""
            row.save(update_fields=["token", "updated_at"])
            messages.success(request, "Stored token cleared — will fall back to .env.")
            return redirect(self.success_url)
        return super().post(request, *args, **kwargs)
