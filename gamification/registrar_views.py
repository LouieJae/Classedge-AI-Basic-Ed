from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render
from gamification.forms.quest_settings_form import OrganizationQuestSettingsForm
from gamification.quest_settings_models import OrganizationQuestSettings


def _is_registrar(user):
    return (
        user.is_authenticated
        and hasattr(user, "profile")
        and user.profile.role
        and user.profile.role.name == "Registrar"
    )


@login_required
@user_passes_test(_is_registrar)
def registrar_quest_settings(request):
    obj = OrganizationQuestSettings.load()
    if request.method == "POST":
        form = OrganizationQuestSettingsForm(request.POST, instance=obj)
        if form.is_valid():
            inst = form.save(commit=False)
            inst.updated_by = request.user
            try:
                inst.save()
            except Exception as e:
                form.add_error(None, str(e))
            else:
                messages.success(request, "Quest settings saved.")
                return redirect("registrar_quest_settings")
    else:
        form = OrganizationQuestSettingsForm(instance=obj)
    return render(request, "operations/registrar_quest_settings.html", {"form": form, "obj": obj})
