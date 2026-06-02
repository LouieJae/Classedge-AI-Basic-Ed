"""Scoring engine for side activities."""


def _score_daily_challenge(content, data):
    return 1.0 if data.get("answer") == content.get("answer") else 0.0


def _score_multi_choice(content, data):
    questions = content.get("questions", [])
    if not questions:
        return 0.0
    answers = data.get("answers", [])
    correct = sum(
        1 for i, q in enumerate(questions)
        if i < len(answers) and answers[i] == q.get("answer")
    )
    return correct / len(questions)


def _score_fill_blank(content, data):
    blanks = content.get("blanks", [])
    if not blanks:
        return 0.0
    answers = data.get("answers", [])
    correct = sum(
        1 for i, b in enumerate(blanks)
        if i < len(answers) and str(answers[i]).strip().lower() == str(b).strip().lower()
    )
    return correct / len(blanks)


def _score_word_scramble(content, data):
    words = content.get("words", [])
    if not words:
        return 0.0
    answers = data.get("answers", [])
    correct = sum(
        1 for i, w in enumerate(words)
        if i < len(answers) and str(answers[i]).strip().lower() == str(w.get("answer", "")).strip().lower()
    )
    return correct / len(words)


def _score_equation_balance(content, data):
    expected = content.get("coefficients", [])
    given = data.get("coefficients", [])
    if not expected:
        return 0.0
    try:
        correct = sum(
            1 for i, c in enumerate(expected)
            if i < len(given) and int(given[i]) == int(c)
        )
    except (ValueError, TypeError):
        return 0.0
    return correct / len(expected)


def _score_drag_order(content, data):
    correct_order = content.get("correct_order", [])
    order = data.get("order", [])
    if not correct_order:
        return 0.0
    return 1.0 if order == correct_order else 0.0


def _score_match_pair(content, data):
    matches = data.get("matches", {})
    if not matches:
        return 0.0
    correct = sum(1 for k, v in matches.items() if k == v)
    return correct / len(matches)


def _score_flashcard(content, data):
    cards = content.get("cards", [])
    if not cards:
        return 0.0
    knew = data.get("knew_count", 0)
    return min(1.0, max(0.0, knew / len(cards)))


def _score_typing_drill(content, data):
    return min(1.0, max(0.0, float(data.get("accuracy", 0.0))))


def _score_geo_map(content, data):
    targets = content.get("targets", [])
    if not targets:
        return 0.0
    correct = data.get("correct_clicks", 0)
    return min(1.0, max(0.0, correct / len(targets)))


def _score_code_kata(content, data):
    test_cases = content.get("test_cases", [])
    if not test_cases:
        return 0.0
    passed = data.get("tests_passed", 0)
    return min(1.0, max(0.0, passed / len(test_cases)))


SCORERS = {
    "daily_challenge": _score_daily_challenge,
    "practice_quiz": _score_multi_choice,
    "speed_round": _score_multi_choice,
    "math_drill": _score_multi_choice,
    "reading_mini": _score_multi_choice,
    "fill_blank": _score_fill_blank,
    "word_scramble": _score_word_scramble,
    "equation_balance": _score_equation_balance,
    "drag_order": _score_drag_order,
    "timeline_sort": _score_drag_order,
    "match_pair": _score_match_pair,
    "flashcard": _score_flashcard,
    "typing_drill": _score_typing_drill,
    "geo_map": _score_geo_map,
    "code_kata": _score_code_kata,
}


def score_activity(sub_type, content_json, submitted_data):
    """Score an activity attempt. Returns float 0.0-1.0."""
    scorer = SCORERS.get(sub_type)
    if scorer is None:
        return 0.0
    return scorer(content_json, submitted_data)
