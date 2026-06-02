"""Data-volume stress test: hit a curated URL list via Django's test Client.

For each URL: force_login as a seeded stress user, GET, record status + ms.
Then print a table sorted by slowest descending. Flag slow / error rows red.

    python manage.py stress_run
    python manage.py stress_run --user student@stresstest.local
    python manage.py stress_run --threshold-ms 1000
"""
from __future__ import annotations

import time

from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import NoReverseMatch, reverse

from ._stress_common import STRESS_EMAIL_DOMAIN

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"


# URLs to hit. ``args_fn`` (optional) returns a list of URL kwargs/args at runtime.
# ``best_role`` is a hint for which seeded role-user is most likely to have access.
URL_PLAN = [
    # (url_name, args_fn_or_None, best_role)
    ("dashboard", None, "admin"),
    ("course-list", None, "teacher"),
    ("grade-book", None, "teacher"),
    ("grades", None, "student"),
    ("student-list", None, "admin"),
    ("teacher-list", None, "admin"),
    ("admin-and-staff-list", None, "admin"),
    ("program-head-list", None, "admin"),
    ("student-login-report", None, "admin"),
    ("teacher-login-report", None, "admin"),
    ("course-report", None, "admin"),
    ("teacher-progress-report", None, "admin"),
    ("it_admin_dashboard", None, "admin"),
    ("registrar_dashboard", None, "registrar"),
    ("academic_director_dashboard", None, "academicdirector"),
    ("program_head_dashboard", None, "programhead"),
    ("super_admin_dashboard", None, "admin"),
    ("gamification_leaderboard", None, "student"),
    # parameterized — find any [STRESS] subject id
    ("subjectStudentList", "first_stress_subject_pk", "teacher"),
    ("material-list", "first_stress_subject_pk", "teacher"),
]


class Command(BaseCommand):
    help = "Hit each curated URL via Django Client and report timings."

    def add_arguments(self, parser):
        parser.add_argument("--user", default=f"admin@{STRESS_EMAIL_DOMAIN}",
                            help="Email of stress user to log in as (default admin)")
        parser.add_argument("--threshold-ms", type=int, default=2000,
                            help="Flag rows slower than this in red")

    def handle(self, *args, **opts):
        from accounts.models import CustomUser
        from subject.models import Subject

        threshold_ms = opts["threshold_ms"]
        login_email = opts["user"]

        try:
            user = CustomUser.objects.get(email=login_email)
        except CustomUser.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                f"No user with email {login_email!r}. Run `stress_seed` first."
            ))
            return

        first_stress_subject = (
            Subject.objects.filter(subject_name__startswith="[STRESS]").first()
        )

        def resolve_args(spec):
            if spec is None:
                return [], {}
            if spec == "first_stress_subject_pk":
                if not first_stress_subject:
                    return None
                # both material-list and subjectStudentList expect a single pk
                # material-list uses <int:id>, subjectStudentList uses <int:pk> — both positional work
                return [first_stress_subject.pk], {}
            return [], {}

        client = Client()
        client.force_login(user)

        results = []  # (name, status, ms, length, url)
        for name, args_spec, _role in URL_PLAN:
            resolved = resolve_args(args_spec)
            if resolved is None:
                results.append((name, "SKIP-no-stress-subject", 0, 0, ""))
                continue
            args, kwargs = resolved
            try:
                url = reverse(name, args=args, kwargs=kwargs)
            except NoReverseMatch as e:
                results.append((name, f"NOREVERSE: {e}", 0, 0, ""))
                continue

            t0 = time.perf_counter()
            try:
                resp = client.get(url, follow=False)
                status = resp.status_code
                length = len(resp.content) if hasattr(resp, "content") else 0
            except Exception as exc:
                status = f"EXC:{type(exc).__name__}"
                length = 0
            ms = (time.perf_counter() - t0) * 1000.0
            results.append((name, status, ms, length, url))

        # Sort slowest first
        results.sort(key=lambda r: (r[2] if isinstance(r[2], (int, float)) else 0), reverse=True)

        self.stdout.write("")
        self.stdout.write(self.style.NOTICE(
            f"== stress_run report (logged in as {login_email}) =="
        ))
        self.stdout.write(f"{'URL name':<35} {'status':<10} {'ms':>10} {'bytes':>10}  url")
        self.stdout.write("-" * 100)
        for name, status, ms, length, url in results:
            ms_str = f"{ms:10.1f}" if isinstance(ms, (int, float)) else f"{str(ms):>10}"
            ok = isinstance(status, int) and status in (200, 302) and (
                not isinstance(ms, (int, float)) or ms <= threshold_ms
            )
            color = GREEN if ok else RED
            line = f"{name:<35} {str(status):<10} {ms_str} {length:>10}  {url}"
            self.stdout.write(f"{color}{line}{RESET}")
        self.stdout.write("")
