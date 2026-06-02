"""[Classedge LMS] Grade a single student submission against a Quest's payload."""


def grade(quest, submitted_answer):
    """Return (is_correct: bool, score: float in 0..1)."""
    kind = quest.kind
    p = quest.payload or {}
    if kind == "quiz":
        try:
            idx = int(submitted_answer)
        except (TypeError, ValueError):
            return False, 0.0
        ok = idx == p.get("correct_index")
        return ok, (1.0 if ok else 0.0)
    if kind == "reading_check":
        text = (submitted_answer or "").lower()
        keywords = [k.lower() for k in p.get("expected_keywords", [])]
        if not keywords:
            return False, 0.0
        hits = sum(1 for k in keywords if k in text)
        ratio = hits / len(keywords)
        return ratio >= 0.5, round(ratio, 2)
    if kind == "task":
        if p.get("self_check") and submitted_answer == "done":
            return True, 1.0
        return False, 0.0
    return False, 0.0
