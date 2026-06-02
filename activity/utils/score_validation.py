from dataclasses import dataclass
from typing import Optional


@dataclass
class TotalMismatch:
    expected: float
    actual: float

    def message(self) -> str:
        return (
            f"Score mismatch: your questions total {self.actual:g} points, "
            f"but this activity requires exactly {self.expected:g}. "
            f"Adjust your questions before saving."
        )


def validate_exact_total(activity, question_points_sum: float) -> Optional[TotalMismatch]:
    if activity.passing_score_type != "number":
        return None
    expected = float(activity.passing_score or 0)
    actual = float(question_points_sum or 0)
    if abs(expected - actual) > 1e-9:
        return TotalMismatch(expected=expected, actual=actual)
    return None
