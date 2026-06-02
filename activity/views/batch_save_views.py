import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views import View

from activity.models import Activity
from activity.utils.score_validation import validate_exact_total


@method_decorator(login_required, name="dispatch")
class BatchSaveQuestionsView(View):
    def post(self, request, activity_id):
        activity = get_object_or_404(Activity, pk=activity_id)
        try:
            questions = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"ok": False, "error": "Invalid JSON."}, status=400)

        if not isinstance(questions, list):
            return JsonResponse({"ok": False, "error": "Expected a list."}, status=400)

        cleaned = []
        for q in questions:
            cleaned.append({
                "question_text": q.get("question_text", ""),
                "quiz_type": q.get("quiz_type", ""),
                "score": float(q.get("score") or 0),
                "correct_answer": q.get("correct_answer", ""),
                "question_instruction": q.get("question_instruction"),
                "choices": q.get("choices", []),
                "choice_images": q.get("choice_images", []),
                "matching_left": q.get("matching_left", []),
                "matching_right": q.get("matching_right", []),
                "extra_right": q.get("extra_right", []),
                "rubric_items": q.get("rubric_items", []),
            })

        save_final = request.GET.get("save_final") == "1"
        if save_final:
            # Per-question score must be > 0. The form-level HTML `required`
            # is bypassed by fetch-based submission, so enforce it here too.
            zero_score_qs = [
                idx + 1 for idx, q in enumerate(cleaned) if q["score"] <= 0
            ]
            if zero_score_qs:
                if len(zero_score_qs) == 1:
                    msg = f"Question {zero_score_qs[0]} has no point value. Every question must be worth more than 0."
                else:
                    nums = ", ".join(str(n) for n in zero_score_qs)
                    msg = f"Questions {nums} have no point value. Every question must be worth more than 0."
                return JsonResponse({"ok": False, "error": msg}, status=400)

            total = sum(q["score"] for q in cleaned)
            mismatch = validate_exact_total(activity, total)
            if mismatch:
                return JsonResponse({"ok": False, "error": mismatch.message()}, status=400)

        session_questions = request.session.get("questions", {})
        session_questions[str(activity_id)] = cleaned
        request.session["questions"] = session_questions
        request.session.modified = True
        return JsonResponse({"ok": True, "count": len(cleaned)})
