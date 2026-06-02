from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _seed_badge_catalog(sender, **kwargs):
    """Idempotently seed the badge catalog after every migrate. Ensures a
    fresh DB — even after a full migration reset — has all definitions.
    """
    if sender.name != "gamification":
        return
    from django.apps import apps
    from gamification.badge_catalog import seed_catalog

    try:
        seed_catalog(apps.get_model)
    except LookupError:
        # Models not yet registered (very early migrate); harmless.
        pass


class GamificationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gamification"

    def ready(self):
        import gamification.signals  # noqa: F401
        from gamification import signals_quest  # noqa: F401

        post_migrate.connect(_seed_badge_catalog, sender=self)
