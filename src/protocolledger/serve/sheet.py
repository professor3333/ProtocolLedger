"""Turn an entity-relation graph into preparation-sheet rows with evidence.

One row per Action, in text order:

* **materials**: ``Acts-on`` targets of the action.
* **quantities**: ``Measure`` values of those materials, plus ``Measure``/``Count`` values
  attached directly to the action. Each quantity records what it measures.
* **locations / equipment**: ``Site`` and ``Using`` targets.
* **conditions**: ``Setting`` values and ``Mod-Link`` modifiers of the action.

Every cell item is an entity id, so the interface can highlight its source text. Nothing
is inferred: an action without an ``Acts-on`` target gets an empty material list and a
review item, never a guess carried over from another step.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from protocolledger.eval.scorer import QUANTITY_LABELS

IMPLICIT_OBJECT = "The object of this action is not explicitly stated."
UNATTACHED_QUANTITY = "This value is not attached to any material or action."


def build_sheet(
    entities: Sequence[Mapping[str, Any]], relations: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Return (rows, review_items)."""
    by_id = {e["id"]: e for e in entities}
    out: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    has_incoming: set[str] = set()
    for r in relations:
        out[r["head"]][r["label"]].append(r["tail"])
        has_incoming.add(r["tail"])

    def ordered(ids: list[str]) -> list[str]:
        unique = dict.fromkeys(ids)
        return sorted(unique, key=lambda i: (by_id[i]["start"], by_id[i]["end"]))

    rows: list[dict[str, Any]] = []
    review: list[dict[str, str]] = []
    actions = sorted((e for e in entities if e["label"] == "Action"), key=lambda e: e["start"])
    for action in actions:
        links = out[action["id"]]
        materials = ordered(links["Acts-on"])
        quantities = [{"entity": q, "of": m} for m in materials for q in ordered(out[m]["Measure"])]
        quantities += [
            {"entity": q, "of": action["id"]} for q in ordered(links["Measure"] + links["Count"])
        ]
        row = {
            "action": action["id"],
            "materials": materials,
            "quantities": quantities,
            "locations": ordered(links["Site"] + links["Using"]),
            "conditions": ordered(links["Setting"] + links["Mod-Link"]),
            "status": "proposed",
            "issues": [],
        }
        if not materials:
            row["status"] = "review_required"
            row["issues"].append(IMPLICIT_OBJECT)
            review.append({"entity": action["id"], "issue": IMPLICIT_OBJECT})
        rows.append(row)

    for e in sorted(entities, key=lambda e: e["start"]):
        if e["label"] in QUANTITY_LABELS and e["id"] not in has_incoming:
            review.append({"entity": e["id"], "issue": UNATTACHED_QUANTITY})
    return rows, review
