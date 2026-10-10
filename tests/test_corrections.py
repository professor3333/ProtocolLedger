import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from protocolledger.data import corrections as corr

TEXT = "Add\u00a0chloroform\u00a0 and mix.\n"


def make_doc(entities: list[dict[str, Any]]) -> dict[str, Any]:
    return {"doc_id": "train_data/protocol_1", "text": TEXT, "entities": entities}


def ent(eid: str, label: str, start: int, end: int) -> dict[str, Any]:
    return {"id": eid, "label": label, "start": start, "end": end, "text": TEXT[start:end]}


def test_trims_leading_and_trailing_whitespace_to_raw_slice() -> None:
    doc = make_doc([ent("T1", "Action", 0, 3), ent("T2", "Reagent", 3, 16)])
    (c,) = corr.edge_whitespace_corrections(doc)
    assert c.record == "T2"
    assert c.before == (3, 16, "\u00a0chloroform\u00a0 ")
    assert c.after == (4, 14, "chloroform")
    assert TEXT[4:14] == "chloroform"


def test_apply_updates_offsets_and_records_provenance() -> None:
    doc = make_doc([ent("T2", "Reagent", 3, 16), ent("T1", "Action", 0, 3)])
    fixed = corr.apply_corrections(doc, corr.edge_whitespace_corrections(doc))
    assert [(e["id"], e["start"], e["end"], e["text"]) for e in fixed["entities"]] == [
        ("T1", 0, 3, "Add"),
        ("T2", 4, 14, "chloroform"),
    ]
    assert fixed["corrections"][0]["rule"] == corr.TRIM_EDGE_WHITESPACE
    assert doc["entities"][0]["start"] == 3  # input not mutated


def test_stale_entry_fails_loudly() -> None:
    doc = make_doc([ent("T2", "Reagent", 3, 16)])
    (c,) = corr.edge_whitespace_corrections(doc)
    moved = make_doc([ent("T2", "Reagent", 4, 16)])
    with pytest.raises(corr.CorrectionError, match="before-state"):
        corr.apply_corrections(moved, [c])


def test_whitespace_only_span_is_an_error() -> None:
    doc = make_doc([ent("T9", "Modifier", 14, 16)])
    with pytest.raises(corr.CorrectionError, match="whitespace-only"):
        corr.edge_whitespace_corrections(doc)


def test_ledger_round_trip(tmp_path: Path) -> None:
    doc = make_doc([ent("T2", "Reagent", 3, 16)])
    ledger = corr.build_ledger([doc])
    path = tmp_path / "corrections.jsonl"
    corr.write_ledger(ledger, path)
    assert corr.read_ledger(path) == ledger


MANIFESTS = Path(__file__).resolve().parents[1] / "data" / "manifests"


def test_committed_ledger_matches_conversion_findings() -> None:
    ledger = corr.read_ledger(MANIFESTS / "corrections.jsonl")
    report = json.loads((MANIFESTS / "conversion_report.json").read_text(encoding="utf-8"))
    assert len(ledger) == report["total"]["issues"]["warning:span_edge_whitespace"]
    assert all(c.rule == corr.TRIM_EDGE_WHITESPACE for c in ledger)
    for c in ledger:
        start, end, text = c.after
        assert text == text.strip() and end - start == len(text)
        assert c.before[0] <= start < end <= c.before[1]
    splits = json.loads((MANIFESTS / "splits.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256((MANIFESTS / "corrections.jsonl").read_bytes()).hexdigest()
    assert splits["sources"]["corrections_sha256"] == digest
