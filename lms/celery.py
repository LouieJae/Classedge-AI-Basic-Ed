import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lms.settings')

app = Celery('lms')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


# Migration pipeline tick — disabled by default via MIGRATION_ENABLED setting
try:
    from celery.schedules import schedule as _celery_schedule
    from django.conf import settings as _django_settings
    _interval = int(getattr(_django_settings, "MIGRATION_BATCH_INTERVAL_SECONDS", 30))
    app.conf.beat_schedule = {
        **getattr(app.conf, "beat_schedule", {}),
        "migration-pipeline-tick": {
            "task": "migration.tasks.run_migration_pipeline",
            "schedule": _celery_schedule(run_every=_interval),
        },
    }
except Exception:  # pragma: no cover — beat config failure must not break Celery boot
    pass