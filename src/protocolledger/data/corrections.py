"""The correction ledger: explicit, versioned changes to converted gold annotations.

Raw files are never edited. Every change to a gold annotation is a ledger entry that
records the rule, the document, the record and the before/after values, and is applied
identically to every split, including the locked test split.

Rules (each entry names one):

* ``trim_edge_whitespace``: entity spans whose offsets include leading or trailing
  whitespace (mostly U+00A0 NO-BREAK SPACE) are narrowed to the non-whitespace core.
  Boundary whitespace carries no meaning, and leaving it in gold would penalize every
  system that predicts the clean span under strict boundary matching.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LEDGER_VERSION = "1"
TRIM_EDGE_WHITESPACE = "trim_edge_whitespace"


class CorrectionError(RuntimeError):
    """A ledger entry does not match the document it targets."""


@dataclass(frozen=True)
class Correction:
    rule: str
    doc_id: str
    record: str
    before: tuple[int, int, str]
    after: tuple[int, int, str]

    @property
    def key(self) -> tuple[str, str]:
        return (self.doc_id, self.record)

    def to_json(self) -> dict[str, Any]:
        b, a = self.before, self.after
        return {
            "rule": self.rule,
            "doc_id": self.doc_id,
            "record": self.record,
            "before": {"start": b[0], "end": b[1], "text": b[2]},
            "after": {"start": a[0], "end": a[1], "text": a[2]},
        }

    @classmethod
    def from_json(cls, row: Mapping[str, Any]) -> Correction:
        b, a = row["before"], row["after"]
        return cls(
            row["rule"],
            row["doc_id"],
            row["record"],
            (b["start"], b["end"], b["text"]),
            (a["start"], a["end"], a["text"]),
        )


def edge_whitespace_corrections(doc: Mapping[str, Any]) -> list[Correction]:
    out: list[Correction] = []
    text: str = doc["text"]
    for ent in doc["entities"]:
        span: str = ent["text"]
        core = span.strip()
        if core == span:
            continue
        if not core:
            raise CorrectionError(f"{doc['doc_id']} {ent['id']}: whitespace-only span")
        start = ent["start"] + (len(span) - len(span.lstrip()))
        end = start + len(core)
        if text[start:end] != core:
            raise CorrectionError(f"{doc['doc_id']} {ent['id']}: span text is not the raw slice")
        out.append(
            Correction(
                TRIM_EDGE_WHITESPACE,
                doc["doc_id"],
                ent["id"],
                (ent["start"], ent["end"], span),
                (start, end, core),
            )
        )
    return out


def build_ledger(docs: Iterable[Mapping[str, Any]]) -> list[Correction]:
    return [c for doc in docs for c in edge_whitespace_corrections(doc)]


def apply_corrections(doc: Mapping[str, Any], corrections: Iterable[Correction]) -> dict[str, Any]:
    """Return a corrected copy of ``doc``. Each applied entry is recorded on the document
    under ``corrections``; an entry whose ``before`` does not match fails loudly."""
    out = copy.deepcopy(dict(doc))
    by_id = {e["id"]: e for e in out["entities"]}
    applied: list[dict[str, Any]] = []
    for c in corrections:
        if c.doc_id != out["doc_id"]:
            raise CorrectionError(f"{c.doc_id} entry applied to {out['doc_id']}")
        ent = by_id.get(c.record)
        if ent is None or (ent["start"], ent["end"], ent["text"]) != c.before:
            raise CorrectionError(f"{c.doc_id} {c.record}: before-state does not match")
        start, end, text = c.after
        if out["text"][start:end] != text:
            raise CorrectionError(f"{c.doc_id} {c.record}: after-state is not the raw slice")
        ent["start"], ent["end"], ent["text"] = start, end, text
        applied.append(c.to_json())
    out["entities"].sort(key=lambda e: (e["start"], e["end"], e["label"], int(e["id"][1:])))
    out["corrections"] = applied
    return out


def write_ledger(corrections: Iterable[Correction], path: Path) -> None:
    lines = [json.dumps(c.to_json(), ensure_ascii=False, sort_keys=True) for c in corrections]
    path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")


def read_ledger(path: Path) -> list[Correction]:
    rows = path.read_text(encoding="utf-8").splitlines()
    return [Correction.from_json(json.loads(row)) for row in rows if row.strip()]
