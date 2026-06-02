from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.management import call_command

logger = get_task_logger(__name__)


@shared_task
def notify_due_soon(hours=48):
    """Beat-scheduled wrapper around the `notify_due_soon` management command.

    Keeping the logic in the management command keeps a single source of
    truth (still runnable by hand as `manage.py notify_due_soon --hours N`);
    this task just invokes it on the Celery beat schedule. Runs hourly, so a
    48h look-ahead means each upcoming deadline is reminded once (deduped by
    the command's dedupe window) rather than every tick.
    """
    logger.info("notify_due_soon task: scanning for deadlines within %sh", hours)
    call_command("notify_due_soon", hours=hours)
