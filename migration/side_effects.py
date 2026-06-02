"""Thread-local switches used by the migration writer to suppress app-side
side-effects (push notifications, etc.) that fire on cascading post_save
signals during data import.

Scope: only the thread that enters the context manager is affected. Live
user requests on other threads keep firing notifications normally.
"""
import threading
from contextlib import contextmanager


_state = threading.local()


def push_suppressed() -> bool:
    return getattr(_state, "suppress_push", False)


@contextmanager
def suppress_push_notifications():
    prev = getattr(_state, "suppress_push", False)
    _state.suppress_push = True
    try:
        yield
    finally:
        _state.suppress_push = prev


def rag_indexing_suppressed() -> bool:
    return getattr(_state, "suppress_rag", False)


@contextmanager
def suppress_rag_indexing():
    prev = getattr(_state, "suppress_rag", False)
    _state.suppress_rag = True
    try:
        yield
    finally:
        _state.suppress_rag = prev
