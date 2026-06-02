from gamification.models import CodingStats


def update_coding_stats(student, submission):
    """Update CodingStats after a CodeSubmission is graded."""
    stats, _ = CodingStats.objects.get_or_create(student=student)

    stats.total_submissions += 1

    if submission.score == 1.0:
        stats.perfect_submissions += 1
        stats.current_streak += 1
        if stats.current_streak > stats.best_streak:
            stats.best_streak = stats.current_streak
        if submission.execution_time_ms is not None and submission.execution_time_ms < 500:
            stats.fast_perfects += 1
    else:
        stats.current_streak = 0

    lang = submission.language
    if lang and lang not in stats.languages_used:
        stats.languages_used = stats.languages_used + [lang]

    stats.save()


def update_coding_stats_kata(student, attempt):
    """Update CodingStats after a code_kata SideActivityAttempt completes."""
    stats, _ = CodingStats.objects.get_or_create(student=student)

    stats.total_katas += 1

    if attempt.score is not None and attempt.score == 1.0:
        stats.perfect_katas += 1
        stats.current_streak += 1
        if stats.current_streak > stats.best_streak:
            stats.best_streak = stats.current_streak
    else:
        stats.current_streak = 0

    stats.save()
