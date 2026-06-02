from django.apps import AppConfig
from django.db.backends.signals import connection_created


def _apply_sqlite_pragmas(sender, connection, **kwargs):
    if connection.vendor != 'sqlite':
        return
    with connection.cursor() as cursor:
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.execute('PRAGMA synchronous=NORMAL')
        cursor.execute('PRAGMA busy_timeout=30000')


class ActivityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'activity'

    def ready(self):
        connection_created.connect(_apply_sqlite_pragmas, dispatch_uid='lms_sqlite_pragmas')
