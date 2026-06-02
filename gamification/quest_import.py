"""[Classedge LMS] CSV/JSON bulk import of teacher-authored quests."""
import csv
import io
import json
import os
from django.db import transaction
from gamification.quest_models import Quest
from gamification.quest_schema import validate_single_quest, QuestSchemaError

MAX_BYTES = 1 * 1024 * 1024
MAX_ROWS = 200


class ImportError(Exception):
    pass


def _read(file_obj) -> bytes:
    data = file_obj.read()
    if len(data) > MAX_BYTES:
        raise ImportError(f"File too large (>{MAX_BYTES} bytes).")
    return data


def _parse_csv(data: bytes) -> list:
    text = data.decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))
    items = []
    for i, row in enumerate(reader, start=2):
        try:
            payload = json.loads(row["payload_json"])
        except (json.JSONDecodeError, KeyError) as e:
            raise ImportError(f"Row {i}: invalid payload_json ({e})")
        counts = (row.get("counts_toward_grade", "true").strip().lower() in ("1", "true", "yes"))
        items.append({
            "kind": row.get("kind", "").strip(),
            "title": row.get("title", "").strip(),
            "body": row.get("body", "").strip(),
            "payload": payload,
            "counts_toward_grade": counts,
        })
    return items


def _parse_json(data: bytes) -> list:
    try:
        parsed = json.loads(data.decode("utf-8", errors="ignore"))
    except json.JSONDecodeError as e:
        raise ImportError(f"Invalid JSON: {e}")
    if not isinstance(parsed, list):
        raise ImportError("JSON root must be a list of quests.")
    return parsed


def import_quests(module, file_obj) -> int:
    name = getattr(file_obj, "name", "")
    ext = os.path.splitext(name)[1].lower()
    data = _read(file_obj)
    if ext == ".csv":
        items = _parse_csv(data)
    elif ext == ".json":
        items = _parse_json(data)
    else:
        raise ImportError("File must be .csv or .json")

    if len(items) > MAX_ROWS:
        raise ImportError(f"Too many quests ({len(items)}); cap is {MAX_ROWS}.")
    if not items:
        raise ImportError("No quests found in file.")

    for i, q in enumerate(items, start=1):
        try:
            validate_single_quest(q)
        except QuestSchemaError as e:
            raise ImportError(f"Item {i} invalid: {e}")

    start_order = (Quest.objects.filter(module=module).order_by("-order").values_list("order", flat=True).first() or 0) + 1
    with transaction.atomic():
        for offset, q in enumerate(items):
            Quest.objects.create(
                module=module, order=start_order + offset,
                kind=q["kind"], title=q["title"], body=q["body"],
                payload=q["payload"], status="draft", ai_provider="upload",
                counts_toward_grade=q.get("counts_toward_grade", True),
            )
    return len(items)
