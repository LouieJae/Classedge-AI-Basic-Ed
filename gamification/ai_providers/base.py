"""[Classedge LMS] Shared prompt + JSON contract for quest generation providers."""

SYSTEM_PROMPT = (
    "You generate learning quests from lesson text. Return ONLY valid JSON, no prose. "
    "Each quest must have 'kind' (quiz|reading_check|task), 'title' (<=200 chars), 'body', "
    "'payload', and 'source_chunk' (exact excerpt). "
    "quiz.payload = {options: [4 strings], correct_index: int}. "
    "reading_check.payload = {reading: str, question: str, expected_keywords: [str,...]}. "
    "task.payload = {rubric: str, self_check: bool}. "
    "Mix kinds across the set. Titles must be unique."
)


def user_prompt(text: str, n: int) -> str:
    return (
        f"Generate exactly {n} quests from this lesson. Return JSON: "
        f'{{"quests": [...]}}\n\nLESSON:\n{text}'
    )
