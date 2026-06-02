"""Locust HTTP load test for the LMS.

Run a Django dev server first, then in another terminal:

    pip install locust
    locust -f stress_tests/locustfile.py

Then open http://localhost:8089 to start the swarm.

Stress users must have been seeded with ``stress_seed`` first; they all share
the password ``stresstest123``.

NOTE: The login form may require reCAPTCHA in production-ish configs. For
testing, set ``RECAPTCHA_TESTING=True`` in your Django settings or run with
``DJANGO_RECAPTCHA_TESTING=1`` so a known dummy token is accepted.
"""
from __future__ import annotations

import random

from locust import HttpUser, between, task


# Seeded subject IDs are not known in advance, but every [STRESS] subject_code is "STR####".
# Locust users can hit them by guessing low PKs; tweak SUBJECT_PK_RANGE for your seed size.
SUBJECT_PK_RANGE = (1, 50)


class LMSUser(HttpUser):
    host = "http://localhost:8000"
    wait_time = between(1, 3)

    def on_start(self):
        # Standard Django session login via the admin_login_view form.
        # GET first to grab a CSRF token from the login page.
        resp = self.client.get("/", name="GET /login (csrf)")
        csrf = resp.cookies.get("csrftoken", "")
        # Pick a random student credential. Range matches typical seed size; adjust as needed.
        idx = random.randint(0, 99)
        email = f"student_{idx:05d}@stresstest.local"
        self.client.post(
            "/",
            data={
                "email": email,
                "password": "stresstest123",
                "csrfmiddlewaretoken": csrf,
                # reCAPTCHA dummy value — only works when RECAPTCHA_TESTING is on.
                "g-recaptcha-response": "PASSED",
            },
            headers={"Referer": f"{self.host}/"},
            name="POST /login",
        )

    @task(5)
    def dashboard(self):
        self.client.get("/dashboard/", name="dashboard")

    @task(4)
    def course_list(self):
        self.client.get("/course/list/", name="course-list")

    @task(4)
    def material_list(self):
        pk = random.randint(*SUBJECT_PK_RANGE)
        self.client.get(f"/material/list/{pk}/", name="material-list/<id>")

    @task(2)
    def leaderboard(self):
        self.client.get("/gamification/leaderboard/", name="gamification_leaderboard")

    @task(1)
    def student_list(self):
        self.client.get("/account/student-list/", name="student-list")

    @task(1)
    def teacher_list(self):
        self.client.get("/account/teacher-list/", name="teacher-list")
