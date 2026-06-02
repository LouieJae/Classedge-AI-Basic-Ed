"""[Classedge LMS] Signals enforcing the IT Admin role <-> is_superuser invariant.

Only promotes/demotes on role TRANSITIONS into or out of IT Admin. Profile saves
that neither enter nor leave the IT Admin role are no-ops — this preserves
Django's `create_superuser()` flow, where a fresh superuser's auto-created
Profile defaults to Student (which would otherwise trigger an unwanted demote).
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from accounts.models.account_models import Profile
from accounts.models import CustomUser, LegalDocument, UserLegalConsent


@receiver(post_save, sender=LegalDocument)
def on_legal_document_saved(sender, instance, created, **kwargs):
    if not instance.is_active:
        return

    LegalDocument.objects.filter(
        doc_type=instance.doc_type, is_active=True
    ).exclude(pk=instance.pk).update(is_active=False)

    accepted_user_ids = UserLegalConsent.objects.filter(
        document=instance
    ).values_list("user_id", flat=True)

    CustomUser.objects.exclude(id__in=accepted_user_ids).update(
        legal_update_required=True
    )


IT_ADMIN_ROLE_NAME = "IT Admin"


def _is_it_admin(role):
    """[Classedge LMS] True when the given Role instance is the IT Admin role."""
    return bool(role and role.name == IT_ADMIN_ROLE_NAME)


@receiver(pre_save, sender=Profile)
def remember_previous_role(sender, instance, **kwargs):
    """[Classedge LMS] Stash the previous role on the instance so post_save can diff."""
    if not instance.pk:
        instance._previous_role = None
        return
    try:
        prior = Profile.objects.only("role").get(pk=instance.pk)
    except Profile.DoesNotExist:
        instance._previous_role = None
    else:
        instance._previous_role = prior.role


@receiver(post_save, sender=Profile)
def sync_it_admin_superuser(sender, instance, **kwargs):
    """[Classedge LMS] Promote on IT Admin role assignment, demote on removal; no-op otherwise."""
    previous = getattr(instance, "_previous_role", None)
    was_it_admin = _is_it_admin(previous)
    is_it_admin = _is_it_admin(instance.role)

    if is_it_admin and not was_it_admin:
        user = instance.user
        if not user.is_superuser:
            user.is_superuser = True
            user.save(update_fields=["is_superuser"])
    elif was_it_admin and not is_it_admin:
        user = instance.user
        if user.is_superuser:
            user.is_superuser = False
            user.save(update_fields=["is_superuser"])
