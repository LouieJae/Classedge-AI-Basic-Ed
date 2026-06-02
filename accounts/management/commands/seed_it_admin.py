"""[Classedge LMS] Bootstrap an IT Admin role + user on a fresh Classedge deployment."""
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts.models.account_models import CustomUser, Profile
from roles.models import Role


IT_ADMIN_ROLE_NAME = "IT Admin"


class Command(BaseCommand):
    help = "[Classedge LMS] Ensure the IT Admin role exists and at least one user has it."

    def add_arguments(self, parser):
        parser.add_argument("--email", type=str, default=None, help="IT Admin email; falls back to IT_ADMIN_EMAIL env var.")
        parser.add_argument("--password", type=str, default=None, help="IT Admin password; falls back to IT_ADMIN_PASSWORD env var.")
        parser.add_argument("--username", type=str, default=None, help="Username; defaults to email prefix.")
        parser.add_argument("--dry-run", action="store_true", help="Print intent without writing to the DB.")
        parser.add_argument("--force-reset-password", action="store_true", help="Reset the password even if user exists.")

    def handle(self, *args, **options):
        email = options.get("email") or os.environ.get("IT_ADMIN_EMAIL")
        password = options.get("password") or os.environ.get("IT_ADMIN_PASSWORD")
        username = options.get("username")
        dry_run = options.get("dry_run", False)
        force_reset = options.get("force_reset_password", False)

        if not email:
            if not settings.DEBUG:
                raise CommandError("IT_ADMIN_EMAIL is required (env var or --email) in non-DEBUG mode.")
            email = input("IT Admin email: ").strip()
            if not email:
                raise CommandError("Email is required.")

        if not password:
            if not settings.DEBUG:
                raise CommandError("IT_ADMIN_PASSWORD is required (env var or --password) in non-DEBUG mode.")
            import getpass
            password = getpass.getpass("IT Admin password: ")
            if not password:
                raise CommandError("Password is required.")

        if not username:
            username = email.split("@", 1)[0]

        self.stdout.write(f"Email: {email}")
        self.stdout.write(f"Username: {username}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no changes will be made."))
            return

        role, role_created = Role.objects.get_or_create(name=IT_ADMIN_ROLE_NAME)
        if role_created:
            self.stdout.write(self.style.SUCCESS(f"Created Role '{IT_ADMIN_ROLE_NAME}'"))
        else:
            self.stdout.write(f"Role '{IT_ADMIN_ROLE_NAME}' already exists")

        user = CustomUser.objects.filter(email=email).first()
        if user:
            self.stdout.write(f"User {email} exists — granting IT Admin role")
            if force_reset:
                user.set_password(password)
                user.save(update_fields=["password"])
                self.stdout.write(self.style.WARNING("Password reset (--force-reset-password)."))
        else:
            user = CustomUser.objects.create_user(
                username=username, email=email, password=password,
            )
            self.stdout.write(self.style.SUCCESS(f"Created user {email}"))

        profile, _ = Profile.objects.get_or_create(user=user)
        if profile.role != role:
            profile.role = role
            profile.save()  # Signal flips is_superuser=True via role transition
            self.stdout.write(self.style.SUCCESS("Profile.role set to IT Admin"))
        else:
            self.stdout.write("Profile.role already IT Admin")

        user.refresh_from_db()
        self.stdout.write(self.style.SUCCESS(
            f"Done. is_superuser={user.is_superuser}, role={profile.role.name}"
        ))
