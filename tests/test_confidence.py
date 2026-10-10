import pytest

from protocolledger.eval.confidence import (
    Scored,
    cross_fitted_isotonic,
    ece,
    max_coverage_at_precision,
    precision_at_coverage,
    precision_coverage,
    scored_relations,
)


def items(pattern: str) -> list[Scored]:
    """Scores descend; 'c' marks a correct prediction, 'x' an incorrect one."""
    n = len(pattern)
    return [Scored(f"doc{i % 4}", 1 - i / n, ch == "c") for i, ch in enumerate(pattern)]


def test_precision_coverage_and_retained_recall() -> None:
    curve = {row["coverage"]: row for row in precision_coverage(items("ccccxcxxxx"), gold_total=8)}
    assert curve[0.5]["precision"] == pytest.approx(0.8)  # top 5: c c c c x
    assert curve[0.5]["retained_recall"] == pytest.approx(4 / 8)
    assert curve[1.0]["precision"] == pytest.approx(0.5)


def test_targets() -> None:
    xs = items("ccccxcxxxx")
    assert max_coverage_at_precision(xs, 0.95) == {
        "target_precision": 0.95,
        "coverage": 0.4,
        "kept": 4,
    }
    at = precision_at_coverage(xs, 0.3, resamples=200)
    assert at["precision"] == 1.0 and at["kept"] == 3
    assert at["precision_ci95"][0] <= at["precision"] <= at["precision_ci95"][1]


def test_ece_and_isotonic_cross_fit() -> None:
    assert ece([0.9, 0.9], [True, True])["ece"] == pytest.approx(0.1)
    assert ece([1.0, 0.0], [True, False])["ece"] == 0.0
    xs = [Scored(f"d{i % 10}", 0.99, i % 2 == 0) for i in range(200)]  # overconfident
    calibrated = cross_fitted_isotonic(xs)
    assert (
        ece(calibrated, [x.correct for x in xs])["ece"]
        < ece([0.99] * 200, [x.correct for x in xs])["ece"]
    )


def test_joint_score_multiplies_endpoint_confidence() -> None:
    gold = [
        {
            "doc_id": "d",
            "entities": [
                {"id": "A", "start": 0, "end": 1, "label": "Action"},
                {"id": "B", "start": 2, "end": 3, "label": "Reagent"},
            ],
            "relations": [{"head": "A", "label": "Acts-on", "tail": "B"}],
        }
    ]
    pred = [
        {
            "doc_id": "d",
            "entities": [
                {"id": "P1", "start": 0, "end": 1, "label": "Action", "score": 0.5},
                {"id": "P2", "start": 2, "end": 3, "label": "Reagent", "score": 0.8},
            ],
            "relations": [{"head": "P1", "label": "Acts-on", "tail": "P2", "score": 0.9}],
        }
    ]
    (raw,), total = scored_relations(gold, pred)
    (joint,), _ = scored_relations(gold, pred, joint=True)
    assert total == 1 and raw.correct and raw.score == 0.9
    assert joint.score == pytest.approx(0.9 * 0.5 * 0.8)
