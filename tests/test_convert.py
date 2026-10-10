import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from protocolledger.data.brat import parse_ann
from protocolledger.data.convert import Document, build_document, step_spans
from protocolledger.data.schema import normalize_role

TITLE = "Example protocol\n"
SENTENCE = "Add 5 mL of water to the tube, then mix for 30 s."
TEXT = TITLE + SENTENCE + "\n"
OFF = len(TITLE)

# The worked example from the project brief, as BRAT records.
WORKED_ANN = "\n".join(
    [
        f"T1\tAction {OFF + 0} {OFF + 3}\tAdd",
        f"T2\tAmount {OFF + 4} {OFF + 8}\t5 mL",
        f"T3\tReagent {OFF + 12} {OFF + 17}\twater",
        f"T4\tLocation {OFF + 25} {OFF + 29}\ttube",
        f"T5\tAction {OFF + 36} {OFF + 39}\tmix",
        f"T6\tTime {OFF + 44} {OFF + 48}\t30 s",
        "E1\tAction:T1 Acts-on:T3 Site:T4",
        "E2\tAction:T5 ",
        "R1\tMeasure Arg1:T3 Arg2:T2\t",
        "R2\tSetting Arg1:E2 Arg2:T6\t",
        "#1\tAnnotatorNotes T5\tobject of mix is implicit",
    ]
)


def convert(text: str, ann: str) -> Document:
    return build_document("train_data/protocol_x", "train_data", text, parse_ann(ann))


def codes(doc: Document) -> list[str]:
    return sorted(f"{i.severity}:{i.code}" for i in doc.issues)


def triples(doc: Document) -> set[tuple[str, str, str]]:
    return {(r["head"], r["label"], r["tail"]) for r in doc.relations}


def test_worked_example_converts_to_expected_graph() -> None:
    doc = convert(TEXT, WORKED_ANN)
    assert doc.issues == []
    spans = {
        e["id"]: (e["text"], e["label"], e["start"] - OFF, e["end"] - OFF) for e in doc.entities
    }
    assert spans == {
        "T1": ("Add", "Action", 0, 3),
        "T2": ("5 mL", "Amount", 4, 8),
        "T3": ("water", "Reagent", 12, 17),
        "T4": ("tube", "Location", 25, 29),
        "T5": ("mix", "Action", 36, 39),
        "T6": ("30 s", "Time", 44, 48),
    }
    assert triples(doc) == {
        ("T1", "Acts-on", "T3"),
        ("T1", "Site", "T4"),
        ("T3", "Measure", "T2"),
        ("T5", "Setting", "T6"),  # event endpoint E2 resolved to its trigger
    }
    assert doc.raw_relation_count == 4
    assert doc.notes == [{"id": "#1", "target": "T5", "text": "object of mix is implicit"}]
    assert doc.steps == [(0, len(TITLE) - 1), (OFF, OFF + len(SENTENCE))]


def test_every_entity_text_is_the_raw_offset_slice() -> None:
    doc = convert(TEXT, WORKED_ANN)
    for e in doc.entities:
        assert TEXT[e["start"] : e["end"]] == e["text"]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Acts-on2", "Acts-on"),
        ("Site12", "Site"),
        ("Acts-on", "Acts-on"),
        ("Measure-Type-Link", "Measure-Type-Link"),
    ],
)
def test_normalize_role(raw: str, expected: str) -> None:
    assert normalize_role(raw) == expected


def test_repeated_roles_and_event_arguments_resolve() -> None:
    text = "Add A and B, then spin.\n"
    ann = "\n".join(
        [
            "T1\tAction 0 3\tAdd",
            "T2\tReagent 4 5\tA",
            "T3\tReagent 10 11\tB",
            "T4\tAction 18 22\tspin",
            "E1\tAction:T1 Acts-on:T2 Acts-on2:T3",
            "E2\tAction:T4 Acts-on:E1",
        ]
    )
    doc = convert(text, ann)
    assert doc.errors == []
    assert triples(doc) == {
        ("T1", "Acts-on", "T2"),
        ("T1", "Acts-on", "T3"),
        ("T4", "Acts-on", "T1"),
    }
    raw_labels = {o["raw_label"] for r in doc.relations for o in r["origins"]}
    assert raw_labels == {"Acts-on", "Acts-on2"}


def test_duplicate_relations_merge_but_keep_origins_and_raw_count() -> None:
    text = "Add water.\n"
    ann = (
        "T1\tAction 0 3\tAdd\nT2\tReagent 4 9\twater\n"
        "E1\tAction:T1 Acts-on:T2\nR1\tActs-on Arg1:T1 Arg2:T2\t"
    )
    doc = convert(text, ann)
    assert len(doc.relations) == 1
    assert doc.raw_relation_count == 2
    assert [o["record"] for o in doc.relations[0]["origins"]] == ["E1", "R1"]
    assert codes(doc) == ["warning:duplicate_relation"]


def test_multilabel_pairs_are_kept() -> None:
    text = "Add water.\n"
    ann = "T1\tAction 0 3\tAdd\nT2\tReagent 4 9\twater\nE1\tAction:T1 Acts-on:T2 Using:T2"
    doc = convert(text, ann)
    assert triples(doc) == {("T1", "Acts-on", "T2"), ("T1", "Using", "T2")}


def test_surface_mismatch_keeps_offset_slice() -> None:
    text = "Gently dislodge cells.\n"
    doc = convert(text, "T1\tAction 7 15\tdislodge ")
    assert doc.entities[0]["text"] == "dislodge"
    assert codes(doc) == ["warning:action_without_event", "warning:surface_mismatch"]


def test_edge_whitespace_spans_are_flagged_not_trimmed() -> None:
    text = "Add chloroform\u00a0now.\n"
    doc = convert(text, "T1\tReagent 4 15\tchloroform\u00a0")
    assert doc.entities[0]["text"] == "chloroform\u00a0"
    assert (doc.entities[0]["start"], doc.entities[0]["end"]) == (4, 15)
    assert codes(doc) == ["warning:span_edge_whitespace"]


def test_action_without_event_is_reported() -> None:
    doc = convert("Add.\n", "T1\tAction 0 3\tAdd")
    assert codes(doc) == ["warning:action_without_event"]


def test_span_crossing_steps_is_reported() -> None:
    doc = convert("Add\nwater.\n", "T1\tReagent 0 9\tAdd\nwater")
    assert "warning:span_crosses_step" in codes(doc)


@pytest.mark.parametrize(
    ("ann", "code"),
    [
        ("T1\tBanana 0 3\tAdd", "unknown_entity_label"),
        ("T1\tAction 0 99\tAdd", "bad_offsets"),
        ("T1\tAction 3 3\t", "bad_offsets"),
        ("T1\tAction 0 3\tAdd\nE1\tAction:T1 Acts-on:T9", "dangling_endpoint"),
        ("T1\tAction 0 3\tAdd\nR1\tMeasure Arg1:T1 Arg2:E7\t", "dangling_endpoint"),
        ("T1\tReagent 0 3\tAdd\nE1\tAction:T1", "trigger_not_action"),
        ("T1\tAction 0 3\tAdd\nE1\tAction:T1 Banana:T1", "unknown_relation_label"),
        ("T1\tAction 0 3\tAdd\nT1\tAction 0 3\tAdd\nE1\tAction:T1", "duplicate_id"),
        ("T1\tAction 0 1;2 3\tA d", "parse_error"),
        ("A1\tNegated T1", "parse_error"),
        ("T1\tAction zero three\tAdd", "parse_error"),
    ],
)
def test_error_conditions(ann: str, code: str) -> None:
    doc = convert("Add water.\n", ann)
    assert code in {i.code for i in doc.errors}


def test_step_spans() -> None:
    assert step_spans("Title\nA.\nB.") == [(0, 5), (6, 8), (9, 11)]
    assert step_spans("Title\nA.\n") == [(0, 5), (6, 8)]
    assert step_spans("") == [(0, 0)]


def test_conversion_is_deterministic() -> None:
    a = json.dumps(convert(TEXT, WORKED_ANN).to_json(), ensure_ascii=False)
    b = json.dumps(convert(TEXT, WORKED_ANN).to_json(), ensure_ascii=False)
    assert a == b


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT = REPO_ROOT / "data" / "manifests" / "conversion_report.json"

AUDIT_ENTITY_LABELS = {
    "Action": 21993, "Amount": 5857, "Concentration": 2520, "Device": 3300,
    "Generic-Measure": 814, "Location": 7054, "Measure-Type": 1941, "Mention": 486,
    "Method": 3242, "Modifier": 9908, "Numerical": 1676, "Reagent": 20065, "Seal": 422,
    "Size": 635, "Speed": 1111, "Temperature": 2855, "Time": 4115, "pH": 170,
}  # fmt: skip
AUDIT_RELATION_LABELS = {
    "Acts-on": 16000, "Commands": 172, "Coreference-Link": 749, "Count": 620,
    "Measure": 9215, "Measure-Type-Link": 817, "Meronym": 2142, "Mod-Link": 9340,
    "Of-Type": 306, "Or": 837, "Product": 467, "Setting": 8577, "Site": 6018, "Using": 4089,
}  # fmt: skip


def test_committed_report_reproduces_dataset_audit() -> None:
    report: dict[str, Any] = json.loads(REPORT.read_text(encoding="utf-8"))
    expected = {
        "train_data": (370, 48197, 32158),
        "dev_data": (122, 15972, 10812),
        "test_data_2020": (111, 23995, 16379),
    }
    for split, (docs, ents, rels) in expected.items():
        s = report["splits"][split]
        assert (s["documents"], s["entities"], s["relations_raw"]) == (docs, ents, rels)
    assert report["total"]["entity_labels"] == AUDIT_ENTITY_LABELS
    assert report["total"]["relation_labels_raw"] == AUDIT_RELATION_LABELS
    assert not any(k.startswith("error:") for k in report["total"]["issues"])


@pytest.mark.slow
def test_local_conversion_matches_committed_report() -> None:
    report: dict[str, Any] = json.loads(REPORT.read_text(encoding="utf-8"))
    for split, out in report["outputs"].items():
        path = REPO_ROOT / out["path"]
        if not path.exists():
            pytest.skip("run scripts/convert.py first")
        assert hashlib.sha256(path.read_bytes()).hexdigest() == out["sha256"], split
