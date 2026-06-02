# lms/settings_central.py
"""Settings module for the central content portal subdomain.

Inherits from lms.settings and overrides only what differs for the
central.classedge.app deployment. Lives alongside the gitignored
lms/settings.py — the gitignore pattern is the exact filename, so this
sibling module is safe to commit.
"""
from lms.settings import *  # noqa: F401,F403

ROOT_URLCONF = "central_content.urls"

ALLOWED_HOSTS = [
    "central.classedge.app",
    "central.localhost",
    "localhost",
    "127.0.0.1",
]

SESSION_COOKIE_DOMAIN = None if DEBUG else "central.classedge.app"
SESSION_COOKIE_NAME = "central_sessionid"
CSRF_COOKIE_NAME = "central_csrftoken"

LOGIN_URL = "/login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login"

AUTHENTICATION_BACKENDS = [
    "central_content.auth_backends.CentralStaffAuthBackend",
]

TEMPLATES[0]["DIRS"] = list(TEMPLATES[0].get("DIRS", []))  # force a mutable list
TEMPLATES[0]["OPTIONS"]["context_processors"] = [
    "django.template.context_processors.debug",
    "django.template.context_processors.request",
    "django.contrib.auth.context_processors.auth",
    "django.contrib.messages.context_processors.messages",
]
