"""Allauth adapters for ClassEdge.

We rely on allauth's built-in `microsoft` provider (allauth.socialaccount.providers.microsoft)
for the OAuth2 flow and Graph profile fetch — no custom Adapter/View is needed.
This module only customizes:

  * CustomAccountAdapter      — minor tweaks to local-account signup
  * CustomSocialAccountAdapter — auto-link by email, set role from Graph jobTitle
"""
import difflib
import logging

from allauth.account.adapter import DefaultAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from django.contrib.auth import login
from django.shortcuts import redirect

from accounts.models import CustomUser, Profile
from roles.models import Role

logger = logging.getLogger(__name__)


ROLE_ALIASES = {
    'student': 'Student',
    'teacher': 'Teacher',
    'instructor': 'Teacher',
    'professor': 'Teacher',
    'dean': 'Dean',
    'registrar': 'Registrar',
    'program head': 'Program Head',
    'academic director': 'Academic Director',
    'parent': 'Parent',
    'time keeper': 'Time Keeper',
    'admin': 'Admin',
}


class CustomAccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        user.email = form.cleaned_data.get('email')
        user.set_password(form.cleaned_data.get('password'))
        user.save()
        return user


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Sync role from Microsoft Graph jobTitle and auto-link by email."""

    def _resolve_role_from_job_title(self, job_title):
        if not job_title:
            return None
        normalized = job_title.lower()
        for key, role_name in ROLE_ALIASES.items():
            if key in normalized:
                role = Role.objects.filter(name__iexact=role_name).first()
                if role:
                    return role
        role_names = list(Role.objects.values_list('name', flat=True))
        match = difflib.get_close_matches(job_title, role_names, n=1, cutoff=0.6)
        if match:
            return Role.objects.filter(name__iexact=match[0]).first()
        return None

    def _apply_role_from_extra_data(self, profile, extra_data):
        job_title = (extra_data.get('jobTitle') or '').strip()
        role = self._resolve_role_from_job_title(job_title)
        logger.info(
            "Microsoft login role sync: jobTitle=%r resolved=%s current=%s",
            job_title, role, profile.role,
        )
        if role and profile.role_id != role.id:
            profile.role = role
            profile.save(update_fields=['role'])

    def save_user(self, request, sociallogin, form=None):
        """Called for first-time social signups."""
        user = super().save_user(request, sociallogin, form=form)
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.first_name = user.first_name
        profile.last_name = user.last_name
        profile.save(update_fields=['first_name', 'last_name'])
        self._apply_role_from_extra_data(profile, sociallogin.account.extra_data)
        return user

    def pre_social_login(self, request, sociallogin):
        """Auto-link Microsoft account to existing user by verified email."""
        if sociallogin.is_existing:
            # Returning user — refresh role and continue.
            self._refresh_role(sociallogin)
            return

        email = (
            sociallogin.account.extra_data.get('mail')
            or sociallogin.account.extra_data.get('userPrincipalName')
            or ''
        ).lower()
        if not email:
            return

        try:
            user = CustomUser.objects.get(email__iexact=email)
        except CustomUser.DoesNotExist:
            return  # Let allauth create a new user via save_user.

        # Existing local user — connect this Microsoft identity to them.
        sociallogin.connect(request, user)
        self._refresh_role(sociallogin, user=user)

    def _refresh_role(self, sociallogin, user=None):
        user = user or sociallogin.user
        if not user or not user.pk:
            return
        profile, _ = Profile.objects.get_or_create(user=user)
        self._apply_role_from_extra_data(profile, sociallogin.account.extra_data)

    def get_login_redirect_url(self, request):
        return getattr(settings, 'LOGIN_REDIRECT_URL', '/')
