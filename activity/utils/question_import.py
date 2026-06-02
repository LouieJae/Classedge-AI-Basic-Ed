import csv
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple, BinaryIO


@dataclass
class ImportRowError:
    row_number: int
    message: str


_TRUE_VALUES = {"true", "t", "1"}
_FALSE_VALUES = {"false", "f", "0"}


def _clean(cell: str) -> str:
    return (cell or "").strip().strip('"')


def _resolve_points(raw: str, default_points, row_number: int, errors: List[ImportRowError]):
    raw = _clean(raw)
    if raw == "":
        if default_points is None:
            errors.append(ImportRowError(
                row_number,
                "Points is empty and no default is set on the activity.",
            ))
            return None
        return float(default_points)
    try:
        return float(raw)
    except ValueError:
        errors.append(ImportRowError(row_number, f"Points '{raw}' is not a valid number."))
        return None


def parse_multiple_choice_csv(
    fileobj: Iterable[str],
    default_points: Optional[float],
) -> Tuple[List[dict], List[ImportRowError]]:
    reader = csv.reader(fileobj)
    rows: List[dict] = []
    errors: List[ImportRowError] = []
    for i, raw_row in enumerate(reader, start=1):
        if i == 1:
            continue  # skip header label row
        if not raw_row or all(not _clean(c) for c in raw_row):
            continue
        if len(raw_row) < 4:
            errors.append(ImportRowError(i, "Row must have question, points, at least 2 choices, and a correct answer."))
            continue
        question_text = _clean(raw_row[0])
        points = _resolve_points(raw_row[1], default_points, i, errors)
        if points is None:
            continue
        choices = [_clean(c) for c in raw_row[2:-1]]
        correct_text = _clean(raw_row[-1])
        if correct_text not in choices:
            errors.append(ImportRowError(i, f"Correct answer '{correct_text}' not in the choices."))
            continue
        rows.append({
            "question_text": question_text,
            "quiz_type": "Multiple Choice",
            "score": points,
            "choices": choices,
            "correct_answer": choices.index(correct_text),
        })
    if errors:
        return [], errors
    return rows, errors


def parse_true_false_csv(
    fileobj: Iterable[str],
    default_points: Optional[float],
) -> Tuple[List[dict], List[ImportRowError]]:
    reader = csv.reader(fileobj)
    rows: List[dict] = []
    errors: List[ImportRowError] = []
    for i, raw_row in enumerate(reader, start=1):
        if i == 1:
            continue
        if not raw_row or all(not _clean(c) for c in raw_row):
            continue
        if len(raw_row) < 3:
            errors.append(ImportRowError(i, "Row must have question, points, correct_answer."))
            continue
        question_text = _clean(raw_row[0])
        points = _resolve_points(raw_row[1], default_points, i, errors)
        if points is None:
            continue
        raw_answer = _clean(raw_row[2]).lower()
        if raw_answer in _TRUE_VALUES:
            correct = "True"
        elif raw_answer in _FALSE_VALUES:
            correct = "False"
        else:
            errors.append(ImportRowError(i, f"Correct answer '{_clean(raw_row[2])}' is not a valid true/false value."))
            continue
        rows.append({
            "question_text": question_text,
            "quiz_type": "True/False",
            "score": points,
            "correct_answer": correct,
        })
    if errors:
        return [], errors
    return rows, errors


def _excel_rows(fileobj: BinaryIO):
    """Yield (row_number, list_of_str) from an openpyxl workbook, skipping the header row."""
    import openpyxl
    wb = openpyxl.load_workbook(fileobj, read_only=True, data_only=True)
    ws = wb.active
    for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
        if i == 1:
            continue  # skip header
        yield i, [str(c) if c is not None else "" for c in row]


def parse_multiple_choice_excel(
    fileobj: BinaryIO,
    default_points: Optional[float],
) -> Tuple[List[dict], List[ImportRowError]]:
    rows: List[dict] = []
    errors: List[ImportRowError] = []
    for i, raw_row in _excel_rows(fileobj):
        if not raw_row or all(not _clean(c) for c in raw_row):
            continue
        if len(raw_row) < 4:
            errors.append(ImportRowError(i, "Row must have question, points, at least 2 choices, and a correct answer."))
            continue
        question_text = _clean(raw_row[0])
        points = _resolve_points(raw_row[1], default_points, i, errors)
        if points is None:
            continue
        choices = [_clean(c) for c in raw_row[2:-1]]
        correct_text = _clean(raw_row[-1])
        if correct_text not in choices:
            errors.append(ImportRowError(i, f"Correct answer '{correct_text}' not in the choices."))
            continue
        rows.append({
            "question_text": question_text,
            "quiz_type": "Multiple Choice",
            "score": points,
            "choices": choices,
            "correct_answer": choices.index(correct_text),
        })
    if errors:
        return [], errors
    return rows, errors


def parse_true_false_excel(
    fileobj: BinaryIO,
    default_points: Optional[float],
) -> Tuple[List[dict], List[ImportRowError]]:
    rows: List[dict] = []
    errors: List[ImportRowError] = []
    for i, raw_row in _excel_rows(fileobj):
        if not raw_row or all(not _clean(c) for c in raw_row):
            continue
        if len(raw_row) < 3:
            errors.append(ImportRowError(i, "Row must have question, points, correct_answer."))
            continue
        question_text = _clean(raw_row[0])
        points = _resolve_points(raw_row[1], default_points, i, errors)
        if points is None:
            continue
        raw_answer = _clean(raw_row[2]).lower()
        if raw_answer in _TRUE_VALUES:
            correct = "True"
        elif raw_answer in _FALSE_VALUES:
            correct = "False"
        else:
            errors.append(ImportRowError(i, f"Correct answer '{_clean(raw_row[2])}' is not a valid true/false value."))
            continue
        rows.append({
            "question_text": question_text,
            "quiz_type": "True/False",
            "score": points,
            "correct_answer": correct,
        })
    if errors:
        return [], errors
    return rows, errors
