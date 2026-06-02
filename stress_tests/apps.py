from django.apps import AppConfig


class StressTestsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "stress_tests"
    verbose_name = "Stress Tests"
