class MigrationClientError(Exception):
    """Base for all OldLmsClient errors."""


class AuthError(MigrationClientError):
    """401/403 from old side. Do not retry."""


class ThrottledError(MigrationClientError):
    """429 from old side. Caller should sleep `retry_after` seconds."""

    def __init__(self, message: str, retry_after: float = 1.0):
        super().__init__(message)
        self.retry_after = retry_after


class TransientError(MigrationClientError):
    """5xx or connection error after retries exhausted."""


class PermanentError(MigrationClientError):
    """4xx other than 401/403/429. Do not retry."""
