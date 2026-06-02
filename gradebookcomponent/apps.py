from django.apps import AppConfig


class GradebookcomponentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gradebookcomponent'

    def ready(self):
        # Force import of models so Django picks them up for migrations
        from . import models
