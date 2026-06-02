# stress_tests

Two-pronged stress suite for the Classedge LMS:

1. **Data-volume tests** (`stress_seed` + `stress_run`) — fill the DB with
   tagged dummy data, then time each curated view via Django's test client.
2. **HTTP load tests** (`locustfile.py`) — drive concurrent real HTTP requests.

All seeded data is tagged so teardown is safe:

- Users have emails ending in `@stresstest.local`.
- Named objects start with `[STRESS]`.
- `stress_teardown` deletes only objects matching those markers.

## Quick start

```bash
# 1. Seed a small dataset
python manage.py stress_seed

# 2. Time the curated URLs
python manage.py stress_run

# 3. Tear it all down
python manage.py stress_teardown            # dry run, prints what would go
python manage.py stress_teardown --yes      # actually delete
```

## Scaling up the seed

```bash
python manage.py stress_seed \
    --students 1000 --teachers 100 --subjects 50 \
    --modules-per-subject 10 --activities-per-module 5 \
    --enrollments-per-student 5 \
    --xp-transactions-per-student 20 \
    --login-history-per-user 10
```

The seeder is **idempotent**: running it twice without teardown is a no-op
(it bails with a warning).

## stress_run options

```bash
python manage.py stress_run                                # default: admin@stresstest.local
python manage.py stress_run --user student_00000@stresstest.local
python manage.py stress_run --threshold-ms 1000
```

Rows are sorted slowest-first. Rows over the threshold or with non-2xx/3xx
statuses are highlighted in red.

## Locust HTTP load test

```bash
pip install locust
python manage.py runserver 0.0.0.0:8000   # in one shell
locust -f stress_tests/locustfile.py      # in another
# open http://localhost:8089
```

Login via the standard Django form uses reCAPTCHA in this project. For
Locust to authenticate, enable test mode (`RECAPTCHA_TESTING=True` /
`os.environ["RECAPTCHA_TESTING"]="True"`) in your dev settings, otherwise
the POST-login step will fail and most tasks will redirect to the login page.

## Cleanup

`stress_teardown --yes` removes (in FK-safe order):

- `XPTransaction`, `StudentBadge`, `StudentGamification` for stress users
- `BadgeDefinition` rows whose name starts with `[STRESS]`
- `LoginHistory` for stress users
- `QuestionChoice`, `ActivityQuestion`, `Activity` for `[STRESS]` activities
- `SubjectEnrollment` for stress users or `[STRESS]` subjects
- `Module`, `Subject` with `[STRESS]` prefix
- `Profile` for stress users
- `CustomUser` with `@stresstest.local` email
- `Role` rows the seeder created with the `[STRESS]` prefix

It never touches a user/object that lacks the marker.
