from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.management import call_command

logger = get_task_logger(__name__)


@shared_task
def notify_streak_at_risk():
    """Beat-scheduled wrapper around the `notify_streak_at_risk` command.

    Keeps the logic in the management command (single source of truth, still
    runnable by hand); this task just runs it on the daily beat schedule.
    Best scheduled for the afternoon/evening so the nudge lands while there's
    still time to log in and save the streak.
    """
    logger.info("notify_streak_at_risk task: scanning for at-risk login streaks")
    call_command("notify_streak_at_risk")
