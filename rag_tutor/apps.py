from django.apps import AppConfig


class RagTutorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "rag_tutor"

    def ready(self):
        import rag_tutor.signals  # noqa: F401
