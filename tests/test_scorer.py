import copy
from typing import Any

import pytest

from protocolledger.eval.scorer import (
    Counts,
    PredictionError,
    evaluate,
    render_markdown,
    score_document,
)

TITLE = "Example\n"
OFF = len(TITLE)
TEXT = TITLE + "Add 5 mL of water to the tube, then mix for 30 s.\n"


def e(eid: str, label: str, start: int, end: int) -> dict[str, Any]:
    return {"id": eid, "label": label, "start": OFF + start, "end": OFF + end}


def r(head: str, label: str, tail: str) -> dict[str, str]:
    return {"head": head, "label": label, "tail": tail}


GOLD: dict[str, Any] = {
    "doc_id": "dev/protocol_1",
    "text": TEXT,
    "steps": [[0, OFF - 1], [OFF, len(TEXT) - 1]],
    "entities": [
        e("T1", "Action", 0, 3),
        e("T2", "Amount", 4, 8),
        e("T3", "Reagent", 12, 17),
        e("T4", "Location", 25, 29),
        e("T5", "Action", 36, 39),
        e("T6", "Time", 44, 48),
    ],
    "relations": [
        r("T1", "Acts-on", "T3"),
        r("T3", "Measure", "T2"),
        r("T1", "Site", "T4"),
        r("T5", "Setting", "T6"),
    ],
}


def pred_from_gold(**changes: Any) -> dict[str, Any]:
    pred = copy.deepcopy({k: GOLD[k] for k in ("doc_id", "entities", "relations")})
    pred.update(changes)
    return pred


def test_perfect_prediction() -> None:
    report = evaluate([GOLD], [pred_from_gold()], resamples=50)
    assert report["entities"]["micro"]["f1"] == 1.0
    assert report["relations"]["micro"]["f1"] == 1.0
    assert report["quantity_attachment"] == {
        "accuracy": 1.0,
        "ci95": [1.0, 1.0],
        "correct": 2,
        "total": 2,
    }
    assert report["complete_steps"]["exact"] == 1


def test_attachment_error_with_perfect_entities() -> None:
    # Every entity is right, but "5 mL" is attached to the action instead of the water.
    rels = [
        r("T1", "Acts-on", "T3"),
        r("T1", "Measure", "T2"),
        r("T1", "Site", "T4"),
        r("T5", "Setting", "T6"),
    ]
    res = score_document(GOLD, pred_from_gold(relations=rels))
    assert res.entity_micro() == Counts(6, 0, 0)
    assert res.relation_micro() == Counts(3, 1, 1)
    assert res.relation_micro().f1 == pytest.approx(0.75)
    assert (res.attachment_correct, res.attachment_total) == (1, 2)
    assert (res.steps_exact, res.steps_total) == (0, 1)


def test_boundary_error_breaks_entity_and_its_relations() -> None:
    ents = [*GOLD["entities"][:1], e("T2", "Amount", 4, 5), *GOLD["entities"][2:]]  # "5"
    res = score_document(GOLD, pred_from_gold(entities=ents))
    assert res.entity_micro() == Counts(5, 1, 1)
    assert res.relations["Measure"] == Counts(0, 1, 1)
    assert res.attachment_correct == 1  # only mix -> 30 s survives


def test_endpoint_type_error_breaks_relation_but_not_attachment() -> None:
    ents = [*GOLD["entities"][:2], e("T3", "Location", 12, 17), *GOLD["entities"][3:]]
    res = score_document(GOLD, pred_from_gold(entities=ents))
    assert res.relations["Acts-on"] == Counts(0, 1, 1)
    assert res.attachment_correct == 2  # attachment ignores labels


def test_reversed_direction_is_wrong() -> None:
    rels = [*GOLD["relations"][:1], r("T2", "Measure", "T3"), *GOLD["relations"][2:]]
    res = score_document(GOLD, pred_from_gold(relations=rels))
    assert res.relations["Measure"] == Counts(0, 1, 1)


def test_duplicate_predictions_are_collapsed() -> None:
    ents = [*GOLD["entities"], {**GOLD["entities"][0], "id": "X1"}]
    rels = [*GOLD["relations"], r("X1", "Acts-on", "T3")]
    res = score_document(GOLD, pred_from_gold(entities=ents, relations=rels))
    assert res.entity_micro() == Counts(6, 0, 0)
    assert res.relation_micro() == Counts(4, 0, 0)


def test_empty_prediction_scores_zero_recall() -> None:
    report = evaluate([GOLD], [{"doc_id": GOLD["doc_id"], "entities": [], "relations": []}])
    assert report["entities"]["micro"]["recall"] == 0.0
    assert report["entities"]["micro"]["fn"] == 6
    assert report["complete_steps"]["exact"] == 0


def test_macro_f1_averages_only_supported_labels() -> None:
    report = evaluate([GOLD], [pred_from_gold()], resamples=10)
    assert report["entities"]["macro_f1_labels"] == 5  # Action, Amount, Reagent, Location, Time
    assert report["relations"]["macro_f1_labels"] == 4
    assert report["entities"]["per_label"]["pH"]["support"] == 0


@pytest.mark.parametrize(
    ("pred", "match"),
    [
        ({"entities": [{"id": "A", "label": "Banana", "start": 0, "end": 1}]}, "unknown label"),
        ({"entities": [{"id": "A", "label": "Action", "start": 5, "end": 999}]}, "bad offsets"),
        ({"entities": [{"id": "A", "label": "Action", "start": 3, "end": 3}]}, "bad offsets"),
        ({"relations": [r("A", "Measure", "B")]}, "endpoint"),
        ({"relations": [r("T1", "Banana", "T3")]}, "relation label"),
    ],
)
def test_malformed_predictions_raise(pred: dict[str, Any], match: str) -> None:
    with pytest.raises(PredictionError, match=match):
        score_document(GOLD, pred_from_gold(**pred))


def test_prediction_set_must_match_gold_documents() -> None:
    with pytest.raises(PredictionError, match="1 missing"):
        evaluate([GOLD], [])
    other = {**pred_from_gold(), "doc_id": "dev/other"}
    with pytest.raises(PredictionError, match="1 extra"):
        evaluate([GOLD], [pred_from_gold(), other])
    with pytest.raises(PredictionError, match="duplicate"):
        evaluate([GOLD], [pred_from_gold(), pred_from_gold()])


def test_bootstrap_is_deterministic_and_brackets_the_estimate() -> None:
    gold2 = {**copy.deepcopy(GOLD), "doc_id": "dev/protocol_2"}
    preds = [pred_from_gold(), {"doc_id": "dev/protocol_2", "entities": [], "relations": []}]
    a = evaluate([GOLD, gold2], preds, resamples=200, seed=1)
    b = evaluate([GOLD, gold2], preds, resamples=200, seed=1)
    assert a == b
    lo, hi = a["entities"]["micro"]["f1_ci95"]
    assert lo <= a["entities"]["micro"]["f1"] <= hi
    assert "Entity micro-F1" in render_markdown(a, "demo")
