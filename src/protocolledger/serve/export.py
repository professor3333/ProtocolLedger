"""Validate review content and export reviewed results as JSON or CSV."""

from __future__ import annotations

import csv
import io
import re
from typing import Any

from protocolledger.data.schema import ENTITY_LABELS, RELATION_LABELS
from protocolledger.eval.scorer import QUANTITY_LABELS
from protocolledger.serve.schemas import ReviewContent
from protocolledger.serve.sheet import build_sheet
from protocolledger.values import VALUES_VERSION, normalize_value

EXPORT_VERSION = "1"
_NUMERIC_START = re.compile(r"^-\s?\d")


def validate_content(content: ReviewContent, text: str) -> list[str]:
    """Every problem with the submitted review; empty means valid."""
    problems: list[str] = []
    ids: dict[str, str] = {}
    for e in content.entities:
        if e.id in ids:
            problems.append(f"duplicate entity id {e.id}")
        ids[e.id] = e.decision
        if e.label not in ENTITY_LABELS:
            problems.append(f"{e.id}: unknown entity label {e.label!r}")
        if not 0 <= e.start < e.end <= len(text):
            problems.append(f"{e.id}: offsets [{e.start}, {e.end}) outside the text")
        if (e.origin == "human") != (e.decision == "added"):
            problems.append(f"{e.id}: human entities must be 'added' and only they may be")
        if e.decision == "edited" and e.original is None:
            problems.append(f"{e.id}: an edited entity must record its original")
    seen: set[str] = set()
    for r in content.relations:
        if r.id in seen:
            problems.append(f"duplicate relation id {r.id}")
        seen.add(r.id)
        if r.label not in RELATION_LABELS:
            problems.append(f"{r.id}: unknown relation label {r.label!r}")
        if (r.origin == "human") != (r.decision == "added"):
            problems.append(f"{r.id}: human relations must be 'added' and only they may be")
        for end in (r.head, r.tail):
            if end not in ids:
                problems.append(f"{r.id}: unknown endpoint {end}")
            elif r.decision != "rejected" and ids[end] == "rejected":
                problems.append(f"{r.id}: kept relation points at rejected entity {end}")
    return problems


def _kept(content: ReviewContent) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entities = [e.model_dump() for e in content.entities if e.decision != "rejected"]
    relations = [r.model_dump() for r in content.relations if r.decision != "rejected"]
    return entities, relations


def export_json(record: dict[str, Any], content: ReviewContent, text: str) -> dict[str, Any]:
    entities, relations = _kept(content)
    for e in entities:
        e["text"] = text[e["start"] : e["end"]]
        if e["label"] in QUANTITY_LABELS:
            e["normalized"] = normalize_value(e["text"], e["label"])[0]
    rows, review = build_sheet(entities, relations)
    return {
        "export_version": EXPORT_VERSION,
        "normalization_version": VALUES_VERSION,
        "review_id": record["id"],
        "revision": record["revision"],
        "model_version": record["model_version"],
        "text_sha256": record["text_sha256"],
        "offsets": "unicode_code_points",
        "entities": entities,
        "relations": relations,
        "rejected": {
            "entities": [e.id for e in content.entities if e.decision == "rejected"],
            "relations": [r.id for r in content.relations if r.decision == "rejected"],
        },
        "sheet": rows,
        "review_items": review,
    }


def _safe_cell(value: str) -> str:
    """Neutralize spreadsheet formula injection without corrupting values like -80 °C."""
    if value[:1] in ("=", "+", "@", "\t", "\r") or (
        value.startswith("-") and not _NUMERIC_START.match(value)
    ):
        return "'" + value
    return value


def export_csv(record: dict[str, Any], content: ReviewContent, text: str) -> str:
    data = export_json(record, content, text)
    by_id = {e["id"]: e for e in data["entities"]}

    def item(eid: str, of: str | None = None, action: str | None = None) -> str:
        e = by_id[eid]
        label = e["text"]
        if of and of in by_id and of not in (eid, action):
            label += f" (of {by_id[of]['text']})"
        if e["origin"] == "human":
            label += " [human]"
        return f"{label} @[{e['start']},{e['end']})"

    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(
        [
            "row",
            "action",
            "materials",
            "quantities",
            "locations_equipment",
            "conditions",
            "review_status",
            "issues",
            "review_id",
            "revision",
            "model_version",
            "text_sha256",
        ]
    )
    for i, row in enumerate(data["sheet"], start=1):
        cells = [
            str(i),
            item(row["action"]),
            "; ".join(item(m) for m in row["materials"]) or "Not explicitly stated",
            "; ".join(item(q["entity"], q["of"], row["action"]) for q in row["quantities"]),
            "; ".join(item(x) for x in row["locations"]),
            "; ".join(item(x) for x in row["conditions"]),
            row["status"],
            " ".join(row["issues"]),
            data["review_id"],
            str(data["revision"]),
            data["model_version"],
            data["text_sha256"],
        ]
        writer.writerow([_safe_cell(c) for c in cells])
    return out.getvalue()
