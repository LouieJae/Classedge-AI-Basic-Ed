import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from migration.side_effects import rag_indexing_suppressed

logger = logging.getLogger(__name__)


def _queue_index(source_type: str, pk):
    """Dispatch the RAG indexer after the surrounding transaction commits.

    Without on_commit, the Celery worker picks up the task in milliseconds and
    queries for a row that the originating transaction hasn't committed yet
    → DoesNotExist. on_commit runs immediately when no transaction is open,
    so the request-path case still works unchanged.

    The migration writer enters suppress_rag_indexing() to skip this entirely
    during bulk import — embedding-API calls per row would be slow and costly.
    Re-index after migration with `manage.py rag_index_all` (or similar)."""
    if rag_indexing_suppressed():
        return

    def _fire():
        try:
            from rag_tutor.tasks import index_content
            index_content.delay(source_type, pk)
        except Exception:
            logger.debug("RAG indexing skipped for %s %s (broker unavailable)", source_type, pk)
    transaction.on_commit(_fire)


@receiver(post_save, sender="module.Module")
def index_module_on_save(sender, instance, **kwargs):
    if instance.description:
        _queue_index("module", instance.pk)


@receiver(post_save, sender="activity.Activity")
def index_activity_on_save(sender, instance, **kwargs):
    if instance.activity_instruction:
        _queue_index("activity", instance.pk)
