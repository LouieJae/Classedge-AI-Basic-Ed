# central_content/management/commands/create_central_staff.py
from django.core.management.base import BaseCommand, CommandError

from central_content.models import CentralStaff


class Command(BaseCommand):
    help = "Create a CentralStaff user (bootstrap the first Publisher)."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--full-name", dest="full_name", required=True)
        parser.add_argument(
            "--role", required=True,
            choices=[c.value for c in CentralStaff.Role],
        )
        parser.add_argument("--password", required=True)

    def handle(self, *, email, full_name, role, password, **kwargs):
        if CentralStaff.objects.filter(email=email.lower()).exists():
            raise CommandError(f"User with email {email} already exists")
        staff = CentralStaff.objects.create_user(
            email=email, full_name=full_name, password=password, role=role,
        )
        self.stdout.write(self.style.SUCCESS(f"Created {staff}"))
