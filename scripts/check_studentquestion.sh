#!/usr/bin/env bash
# Fail CI if any production writer reintroduces StudentQuestion writes
# (outside the deferred allowlist) or any view does direct total_score
# arithmetic instead of routing through recompute_student_activity_total.
set -euo pipefail

ALLOWED_WRITERS_REGEX='activity/views/question_views.py|activity/tasks.py|activity/student_import_utils.py'

HITS=$(git grep -nE 'StudentQuestion\.objects\.(create|update_or_create|bulk_create|get_or_create)|StudentQuestion\(' \
    -- 'activity/views/**.py' 'activity/services/**.py' 'activity/utils/**.py' \
       'mobile/views/**.py' 'gradebookcomponent/views/**.py' 'gradebookcomponent/services/**.py' \
       'course/views/**.py' 'calendars/views.py' 'module/views/**.py' \
    | grep -vE "$ALLOWED_WRITERS_REGEX" || true)

if [ -n "$HITS" ]; then
    echo "ERROR: StudentQuestion writers remain in production code:"
    echo "$HITS"
    exit 1
fi

MUT=$(git grep -nE '\.total_score\s*[+\-]=' \
    -- 'activity/views/**.py' 'mobile/views/**.py' 'gradebookcomponent/views/**.py' \
    | grep -vE "$ALLOWED_WRITERS_REGEX" || true)
if [ -n "$MUT" ]; then
    echo "ERROR: compound total_score mutation; use recompute_student_activity_total:"
    echo "$MUT"
    exit 1
fi

echo "OK: no StudentQuestion writers outside the deferred allowlist; no direct total_score mutation."
