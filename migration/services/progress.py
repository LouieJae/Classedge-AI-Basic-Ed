from migration.models import MigrationJob, MigrationRunLog


def rows_per_minute(job: MigrationJob, *, window_logs: int = 5) -> float:
    logs = list(MigrationRunLog.objects.filter(job=job, finished_at__isnull=False).order_by("-finished_at")[:window_logs])
    if len(logs) < 2:
        return 0.0
    earliest = logs[-1].started_at
    latest = logs[0].finished_at
    span_seconds = max((latest - earliest).total_seconds(), 1.0)
    rows = sum(l.rows_written for l in logs)
    return (rows / span_seconds) * 60.0


def eta_seconds(job: MigrationJob) -> int | None:
    if job.total_estimated <= 0:
        return None
    remaining = max(job.total_estimated - job.rows_written, 0)
    if remaining == 0:
        return 0
    rpm = rows_per_minute(job)
    if rpm <= 0:
        return None
    return int((remaining / rpm) * 60)
