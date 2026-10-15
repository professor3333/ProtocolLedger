from typing import Any

from protocolledger.eval.errors import analyze, classify_entity, classify_relation, render_markdown

ADD, ML5, WATER, TUBE = (
    (0, 3, "Action"),
    (4, 8, "Amount"),
    (12, 17, "Reagent"),
    (25, 29, "Location"),
)


def test_entity_categories() -> None:
    assert classify_entity(WATER, [WATER]) == "correct"
    assert classify_entity(WATER, [(12, 17, "Location")]) == "wrong_type"
    assert classify_entity(ML5, [(4, 5, "Amount")]) == "wrong_boundary"
    assert classify_entity(ML5, [(4, 5, "Numerical")]) == "wrong_boundary_and_type"
    assert classify_entity(WATER, [ADD]) == "missed"


def test_relation_categories() -> None:
    gold = (WATER, "Measure", ML5)
    ents = {ADD, ML5, WATER, TUBE}
    assert classify_relation(gold, ents, {gold}) == "correct"
    assert classify_relation(gold, ents - {WATER}, set()) == "endpoint_error"
    assert classify_relation(gold, ents, {(WATER, "Mod-Link", ML5)}) == "wrong_label"
    assert classify_relation(gold, ents, {(ML5, "Measure", WATER)}) == "wrong_direction"
    # "5 mL" measured against the tube instead of the water.
    assert classify_relation(gold, ents, {(TUBE, "Measure", ML5)}) == "wrong_attachment"
    assert classify_relation(gold, ents, set()) == "missed"


def doc(doc_id: str, ents: list[tuple[int, int, str]], rels: list[tuple[int, str, int]]) -> Any:
    text = "Add 5 mL of water to the tube."
    return {
        "doc_id": doc_id,
        "text": text,
        "entities": [
            {"id": f"E{i}", "start": s, "end": e, "label": lab}
            for i, (s, e, lab) in enumerate(ents)
        ],
        "relations": [{"head": f"E{h}", "label": lab, "tail": f"E{t}"} for h, lab, t in rels],
    }


def test_analyze_counts_examples_and_slices() -> None:
    gold = doc(
        "dev/1", [ADD, ML5, WATER, TUBE], [(0, "Acts-on", 2), (2, "Measure", 1), (0, "Site", 3)]
    )
    pred = doc(
        "dev/1", [ADD, ML5, WATER, (25, 29, "Device")], [(0, "Acts-on", 2), (3, "Measure", 1)]
    )
    report = analyze([gold], [pred], unseen_names={"water"}, sibling_docs=set())
    assert report["entities"]["categories"]["correct"]["count"] == 3
    assert report["entities"]["categories"]["wrong_type"]["count"] == 1
    rel = report["relations"]["categories"]
    assert rel["correct"]["count"] == 1
    assert rel["endpoint_error"]["count"] == 1  # Site points at the mistyped tube
    assert rel["wrong_attachment"]["count"] == 1  # "5 mL" attached to the tube
    assert report["relations"]["spurious"] == {"spurious_endpoint": 1}
    assert report["slices"]["reagent_names"]["unseen"] == {"gold": 1, "recall": 1.0}
    assert "[[water]]" in report["examples"]["relation/wrong_attachment"][0]
    assert "Error analysis" in render_markdown(report, "test")
    withheld = render_markdown({k: v for k, v in report.items() if k != "examples"}, "test")
    assert "[[" not in withheld and "Examples withheld" in withheld
