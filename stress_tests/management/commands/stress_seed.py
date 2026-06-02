"""Seed the LMS with tagged dummy data for stress testing.

Every object is tagged so ``stress_teardown`` can remove it safely:
  * Users: email ends with ``@stresstest.local``
  * Named objects (Subject/Module/Activity/Role-if-created): name starts with ``[STRESS]``

Run small first, scale up:
    python manage.py stress_seed
    python manage.py stress_seed --students 1000 --teachers 100 --subjects 50 \\
        --modules-per-subject 10 --activities-per-module 5 \\
        --enrollments-per-student 5 --xp-transactions-per-student 20 \\
        --login-history-per-user 10
"""
from __future__ import annotations

import random
import time
from datetime import date, timedelta

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from ._stress_common import (
    SEEDED_ROLE_NAMES,
    STRESS_EMAIL_DOMAIN,
    STRESS_NAME_PREFIX,
    STRESS_PASSWORD,
)

BATCH = 1000


class Command(BaseCommand):
    help = "Seed tagged dummy data for stress testing."

    def add_arguments(self, parser):
        parser.add_argument("--students", type=int, default=100)
        parser.add_argument("--teachers", type=int, default=10)
        parser.add_argument("--subjects", type=int, default=10)
        parser.add_argument("--modules-per-subject", type=int, default=5)
        parser.add_argument("--activities-per-module", type=int, default=3)
        parser.add_argument("--enrollments-per-student", type=int, default=3)
        parser.add_argument("--xp-transactions-per-student", type=int, default=10)
        parser.add_argument("--login-history-per-user", type=int, default=5)

    def handle(self, *args, **opts):
        # Defer model imports until Django is set up
        from accounts.models import CustomUser, LoginHistory, Profile
        from activity.models import Activity, ActivityQuestion, QuestionChoice
        from course.models import Semester, SubjectEnrollment
        from gamification.models import (
            BadgeDefinition,
            StudentGamification,
            XPTransaction,
        )
        from module.models import Module
        from roles.models import Role
        from subject.models import Subject

        n_students = opts["students"]
        n_teachers = opts["teachers"]
        n_subjects = opts["subjects"]
        n_modules = opts["modules_per_subject"]
        n_acts = opts["activities_per_module"]
        n_enroll = opts["enrollments_per_student"]
        n_xp = opts["xp_transactions_per_student"]
        n_login = opts["login_history_per_user"]

        start = time.perf_counter()
        self.stdout.write(self.style.NOTICE("== stress_seed starting =="))

        # Idempotency check
        if CustomUser.objects.filter(email__endswith=f"@{STRESS_EMAIL_DOMAIN}").exists():
            self.stdout.write(
                self.style.WARNING(
                    "Stress data already present. Run `stress_teardown --yes` first."
                )
            )
            return

        with transaction.atomic():
            # ---- Roles (only fetch; create if missing, with [STRESS] tag if created) ----
            role_map = {}
            for rn in SEEDED_ROLE_NAMES:
                role = Role.objects.filter(name=rn).first()
                if not role:
                    tagged_name = f"{STRESS_NAME_PREFIX} {rn}"
                    role = Role.objects.create(name=tagged_name)
                    self.stdout.write(f"  created Role {tagged_name!r}")
                role_map[rn] = role

            # ---- Users (admin first; one per role; then bulk students/teachers) ----
            now = timezone.now()
            password_hash = make_password(STRESS_PASSWORD)

            def mk_user(username, email, first, last, is_staff=False, is_super=False):
                return CustomUser(
                    username=username,
                    email=email,
                    first_name=first,
                    last_name=last,
                    password=password_hash,
                    is_staff=is_staff,
                    is_superuser=is_super,
                    is_active=True,
                    needs_password_setup=False,
                    needs_onboarding=False,
                )

            users_to_create = []
            # one user per role (skip IT Admin per spec)
            for rn in SEEDED_ROLE_NAMES:
                slug = rn.lower().replace(" ", "")
                users_to_create.append(
                    mk_user(
                        username=f"stress_role_{slug}",
                        email=f"role_{slug}@{STRESS_EMAIL_DOMAIN}",
                        first=f"{STRESS_NAME_PREFIX} {rn}",
                        last="User",
                        is_staff=(rn == "Admin"),
                    )
                )
            # an admin@stresstest.local for stress_run convenience
            users_to_create.append(
                mk_user(
                    username="stress_admin_main",
                    email=f"admin@{STRESS_EMAIL_DOMAIN}",
                    first=f"{STRESS_NAME_PREFIX} Admin",
                    last="Main",
                    is_staff=True,
                    is_super=True,
                )
            )

            # Bulk students/teachers
            for i in range(n_students):
                users_to_create.append(
                    mk_user(
                        username=f"stress_student_{i:05d}",
                        email=f"student_{i:05d}@{STRESS_EMAIL_DOMAIN}",
                        first=f"{STRESS_NAME_PREFIX} Student",
                        last=f"{i:05d}",
                    )
                )
            for i in range(n_teachers):
                users_to_create.append(
                    mk_user(
                        username=f"stress_teacher_{i:05d}",
                        email=f"teacher_{i:05d}@{STRESS_EMAIL_DOMAIN}",
                        first=f"{STRESS_NAME_PREFIX} Teacher",
                        last=f"{i:05d}",
                    )
                )

            CustomUser.objects.bulk_create(users_to_create, batch_size=BATCH)
            self.stdout.write(f"  users: {len(users_to_create)} created")

            # Re-fetch users (bulk_create on some DBs returns objects without IDs on older Django,
            # but here we re-query by tag for safety regardless).
            all_stress_users = list(
                CustomUser.objects.filter(email__endswith=f"@{STRESS_EMAIL_DOMAIN}")
            )
            students = [u for u in all_stress_users if u.username.startswith("stress_student_")]
            teachers = [u for u in all_stress_users if u.username.startswith("stress_teacher_")]
            role_users = {
                rn: next(
                    (u for u in all_stress_users if u.username == f"stress_role_{rn.lower().replace(' ', '')}"),
                    None,
                )
                for rn in SEEDED_ROLE_NAMES
            }
            main_admin = next(
                (u for u in all_stress_users if u.username == "stress_admin_main"), None
            )

            # ---- Profiles ----
            # Signal `create_or_update_user_profile` fires on each save() but NOT on bulk_create.
            # However, some signals may have created profiles via other paths — guard with get-or-build.
            existing_profile_user_ids = set(
                Profile.objects.filter(user__in=all_stress_users).values_list("user_id", flat=True)
            )
            profiles_to_create = []
            student_role = role_map["Student"]
            teacher_role = role_map["Teacher"]

            for u in all_stress_users:
                if u.id in existing_profile_user_ids:
                    continue
                if u in students:
                    role = student_role
                elif u in teachers:
                    role = teacher_role
                elif u is main_admin:
                    role = role_map["Admin"]
                else:
                    # one-per-role user — figure out which
                    role = None
                    for rn, ru in role_users.items():
                        if ru is u:
                            role = role_map[rn]
                            break
                    if role is None:
                        role = student_role
                profiles_to_create.append(
                    Profile(
                        user=u,
                        role=role,
                        first_name=u.first_name,
                        last_name=u.last_name,
                        status=True,
                    )
                )
            Profile.objects.bulk_create(profiles_to_create, batch_size=BATCH)
            self.stdout.write(f"  profiles: {len(profiles_to_create)} created")

            # ---- Semester (reuse current or create one tagged via end_date convention) ----
            semester = Semester.objects.filter(end_semester=False).first()
            if not semester:
                today = date.today()
                semester = Semester.objects.create(
                    semester_name="First Semester",
                    start_date=today - timedelta(days=30),
                    end_date=today + timedelta(days=120),
                )
                self.stdout.write("  created fallback Semester (untagged — preexisted check failed)")

            # ---- Subjects ----
            subjects_to_create = []
            for i in range(n_subjects):
                primary = teachers[i % len(teachers)] if teachers else None
                subjects_to_create.append(
                    Subject(
                        subject_name=f"{STRESS_NAME_PREFIX} Subject {i:04d}",
                        subject_code=f"STR{i:04d}",
                        subject_description="Stress test subject.",
                        assign_teacher=primary,
                        status="Available",
                    )
                )
            Subject.objects.bulk_create(subjects_to_create, batch_size=BATCH)
            subjects = list(
                Subject.objects.filter(subject_name__startswith=STRESS_NAME_PREFIX)
            )
            self.stdout.write(f"  subjects: {len(subjects)} created")

            # ---- Modules ----
            modules_to_create = []
            for s in subjects:
                for j in range(n_modules):
                    modules_to_create.append(
                        Module(
                            file_name=f"{STRESS_NAME_PREFIX} Module {s.id}-{j:03d}",
                            subject=s,
                            description="Stress module.",
                            order=j,
                        )
                    )
            Module.objects.bulk_create(modules_to_create, batch_size=BATCH)
            modules = list(Module.objects.filter(file_name__startswith=STRESS_NAME_PREFIX))
            self.stdout.write(f"  modules: {len(modules)} created")

            # ---- Activities (+ a couple of questions each) ----
            activities_to_create = []
            for m in modules:
                for k in range(n_acts):
                    activities_to_create.append(
                        Activity(
                            activity_name=f"{STRESS_NAME_PREFIX} Activity {m.id}-{k:02d}",
                            subject=m.subject,
                            max_score=100,
                            passing_score=50,
                            status=True,
                        )
                    )
            Activity.objects.bulk_create(activities_to_create, batch_size=BATCH)
            activities = list(
                Activity.objects.filter(activity_name__startswith=STRESS_NAME_PREFIX)
            )
            self.stdout.write(f"  activities: {len(activities)} created")

            # 2 questions per activity, no choices (keeps it light)
            questions_to_create = []
            for a in activities:
                for q in range(2):
                    questions_to_create.append(
                        ActivityQuestion(
                            activity=a,
                            subject=a.subject,
                            question_text=f"[STRESS] Q{q} for activity {a.id}",
                            correct_answer="0",
                            score=10,
                        )
                    )
            ActivityQuestion.objects.bulk_create(questions_to_create, batch_size=BATCH)
            self.stdout.write(f"  questions: {len(questions_to_create)} created")

            # ---- Enrollments ----
            enrollments_to_create = []
            if subjects and students:
                for stu in students:
                    chosen = random.sample(subjects, min(n_enroll, len(subjects)))
                    for s in chosen:
                        enrollments_to_create.append(
                            SubjectEnrollment(
                                student=stu,
                                subject=s,
                                semester=semester,
                                status="enrolled",
                                student_name=f"{stu.first_name} {stu.last_name}",
                            )
                        )
            # bulk_create with ignore_conflicts to respect unique constraint
            SubjectEnrollment.objects.bulk_create(
                enrollments_to_create, batch_size=BATCH, ignore_conflicts=True
            )
            self.stdout.write(f"  enrollments: ~{len(enrollments_to_create)} attempted")

            # ---- Gamification: StudentGamification + XPTransaction ----
            sg_to_create = [
                StudentGamification(student=s, total_xp=random.randint(0, 5000))
                for s in students
            ]
            StudentGamification.objects.bulk_create(
                sg_to_create, batch_size=BATCH, ignore_conflicts=True
            )
            self.stdout.write(f"  StudentGamification: {len(sg_to_create)} created")

            xp_to_create = []
            for stu in students:
                for _ in range(n_xp):
                    xp_to_create.append(
                        XPTransaction(
                            student=stu,
                            amount=random.randint(1, 100),
                            reason="stress",
                            source_type="stress_seed",
                        )
                    )
            XPTransaction.objects.bulk_create(xp_to_create, batch_size=BATCH)
            self.stdout.write(f"  XPTransaction: {len(xp_to_create)} created")

            # A couple of badge definitions (tagged)
            for tier in ("bronze", "silver", "gold"):
                BadgeDefinition.objects.get_or_create(
                    code=f"stress_{tier}",
                    defaults={
                        "name": f"{STRESS_NAME_PREFIX} Badge {tier}",
                        "description": "stress",
                        "tier": tier,
                        "icon": "star",
                    },
                )

            # ---- LoginHistory ----
            lh_to_create = []
            for u in all_stress_users:
                for k in range(n_login):
                    lh_to_create.append(
                        LoginHistory(
                            user=u,
                            login_time=now - timedelta(days=k),
                            ip_address="127.0.0.1",
                            user_agent="stress-test",
                        )
                    )
            LoginHistory.objects.bulk_create(lh_to_create, batch_size=BATCH)
            self.stdout.write(f"  LoginHistory: {len(lh_to_create)} created")

        elapsed = time.perf_counter() - start
        self.stdout.write(self.style.SUCCESS(f"== stress_seed done in {elapsed:.2f}s =="))
