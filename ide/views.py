import json

from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from activity.models import Activity
from activity.utils.authorization import check_subject_access
from ide.forms import CodingExerciseForm
from ide.models import CodingExercise, CodeSubmission
from ide.tasks import run_code_submission


@login_required
def exercise_detail(request, activity_id):
    activity = get_object_or_404(Activity, pk=activity_id)
    exercise = get_object_or_404(CodingExercise, activity=activity)

    submissions = (
        CodeSubmission.objects.filter(student=request.user, exercise=exercise)
        .order_by("-submitted_at")[:10]
    )

    test_labels = [
        tc.get("label", f"Test {i + 1}")
        for i, tc in enumerate(exercise.test_cases)
    ]

    return render(request, "ide/exercise_detail.html", {
        "activity": activity,
        "exercise": exercise,
        "submissions": submissions,
        "test_labels": test_labels,
    })


@login_required
@require_POST
def submit_code_view(request, activity_id):
    activity = get_object_or_404(Activity, pk=activity_id)
    exercise = get_object_or_404(CodingExercise, activity=activity)

    try:
        body = json.loads(request.body)
        code = body["code"]
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({"error": "Invalid request body."}, status=400)

    submission = CodeSubmission.objects.create(
        student=request.user,
        exercise=exercise,
        code=code,
        language=exercise.language,
        status="pending",
    )

    run_code_submission.delay(submission.pk)

    return JsonResponse({"submission_id": submission.pk})


@login_required
def submission_status(request, submission_id):
    submission = get_object_or_404(
        CodeSubmission, pk=submission_id, student=request.user,
    )

    score_pct = None
    if submission.score is not None:
        score_pct = round(submission.score * 100, 1)

    return JsonResponse({
        "status": submission.status,
        "score": submission.score,
        "score_pct": score_pct,
        "result_json": submission.result_json,
        "execution_time_ms": submission.execution_time_ms,
        "memory_used_kb": submission.memory_used_kb,
    })


@login_required
def exercise_create(request, activity_id):
    activity = get_object_or_404(Activity, pk=activity_id)
    has_access, redirect_response = check_subject_access(request, activity.subject, require_teacher=True)
    if not has_access:
        return redirect_response

    if CodingExercise.objects.filter(activity=activity).exists():
        exercise = CodingExercise.objects.get(activity=activity)
        return redirect("exercise_edit", exercise_id=exercise.pk)

    if request.method == "POST":
        form = CodingExerciseForm(request.POST)
        if form.is_valid():
            exercise = form.save(commit=False)
            exercise.activity = activity
            exercise.save()
            return redirect("exercise_detail", activity_id=activity.pk)
    else:
        form = CodingExerciseForm()

    return render(request, "ide/exercise_setup.html", {
        "form": form,
        "activity": activity,
        "is_edit": False,
    })


@login_required
def exercise_edit(request, exercise_id):
    exercise = get_object_or_404(CodingExercise, pk=exercise_id)
    has_access, redirect_response = check_subject_access(request, exercise.activity.subject, require_teacher=True)
    if not has_access:
        return redirect_response

    test_cases_text = json.dumps(exercise.test_cases, indent=2)

    if request.method == "POST":
        form = CodingExerciseForm(request.POST, instance=exercise)
        if form.is_valid():
            form.save()
            return redirect("exercise_detail", activity_id=exercise.activity.pk)
    else:
        form = CodingExerciseForm(instance=exercise, initial={
            "test_cases_text": test_cases_text,
        })

    return render(request, "ide/exercise_setup.html", {
        "form": form,
        "activity": exercise.activity,
        "exercise": exercise,
        "is_edit": True,
    })


@login_required
def coding_overview(request):
    exercises = CodingExercise.objects.select_related(
        "activity", "activity__subject",
    ).order_by("-created_at")

    exercise_data = []
    for ex in exercises:
        subs = CodeSubmission.objects.filter(exercise=ex, status="completed")
        student_ids = subs.values_list("student_id", flat=True).distinct()
        attempted = student_ids.count()

        best_scores = []
        for sid in student_ids:
            best = subs.filter(student_id=sid).order_by("-score").first()
            if best:
                best_scores.append(best.score)

        avg_score = sum(best_scores) / len(best_scores) if best_scores else 0
        perfect_count = sum(1 for s in best_scores if s == 1.0)

        exercise_data.append({
            "exercise": ex,
            "activity_name": ex.activity.activity_name,
            "subject_name": ex.activity.subject.subject_name if ex.activity.subject else "",
            "language": ex.get_language_display(),
            "attempted_count": attempted,
            "avg_score": round(avg_score * 100, 1),
            "perfect_count": perfect_count,
        })

    return render(request, "ide/coding_overview.html", {
        "exercises": exercise_data,
    })


@login_required
@permission_required('ide.view_codingexercise', raise_exception=True)
def coding_exercise_results(request, exercise_id):
    exercise = get_object_or_404(CodingExercise, pk=exercise_id)
    submissions = (
        CodeSubmission.objects.filter(exercise=exercise, status="completed")
        .select_related("student")
        .order_by("student__last_name", "student__first_name", "-score")
    )

    student_map = {}
    for sub in submissions:
        if sub.student_id not in student_map:
            student_map[sub.student_id] = {
                "student": sub.student,
                "best": sub,
                "attempts": 0,
            }
        student_map[sub.student_id]["attempts"] += 1

    students = sorted(student_map.values(), key=lambda x: x["student"].last_name)

    return render(request, "ide/coding_exercise_results.html", {
        "exercise": exercise,
        "students": students,
        "test_labels": [
            tc.get("label", f"Test {i + 1}")
            for i, tc in enumerate(exercise.test_cases)
        ],
    })


@login_required
@permission_required('ide.change_codesubmission', raise_exception=True)
def coding_score_override(request, submission_id):
    from django.utils import timezone as tz

    submission = get_object_or_404(CodeSubmission, pk=submission_id)

    if request.method == "POST":
        new_score_str = request.POST.get("new_score", "")
        note = request.POST.get("override_note", "")
        try:
            new_score = float(new_score_str)
            new_score = max(0.0, min(1.0, new_score))
        except (ValueError, TypeError):
            return redirect("coding_exercise_results", exercise_id=submission.exercise_id)

        old_score = submission.score
        submission.score = new_score
        result = submission.result_json or {}
        result["override"] = {
            "by": request.user.pk,
            "original_score": old_score,
            "new_score": new_score,
            "note": note,
            "at": tz.now().isoformat(),
        }
        submission.result_json = result
        submission.save(update_fields=["score", "result_json"])

        from activity.models.student_activity_model import StudentActivity
        sa = StudentActivity.objects.filter(
            student=submission.student, activity=submission.exercise.activity,
        ).first()
        if sa:
            max_score = submission.exercise.activity.max_score or 100
            sa.total_score = new_score * max_score
            sa.save(update_fields=["total_score"])

        return redirect("coding_exercise_results", exercise_id=submission.exercise_id)

    return redirect("coding_exercise_results", exercise_id=submission.exercise_id)
