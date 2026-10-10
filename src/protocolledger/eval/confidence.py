"""Precision-coverage curves and calibration for scored relation predictions.

* **Precision-coverage.** Predicted relations are ranked by score. Keeping the top
  fraction (coverage) gives the precision of what is kept, and the retained recall: the
  share of all gold relations that the kept predictions recover. Recall is reported
  because high precision at low coverage can hide many missed relations.
* **Calibration.** A raw score is not a probability of being correct. Isotonic
  regression maps scores to empirical correctness. It is fitted with document-level
  cross-fitting on dev, so every document is scored by a calibrator that never saw it.
  Expected calibration error (ECE, 10 equal-width bins) and the Brier score are reported
  before and after.
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sklearn.isotonic import IsotonicRegression

COVERAGE_GRID = tuple(round(0.05 * i, 2) for i in range(1, 21))


@dataclass(frozen=True)
class Scored:
    doc_id: str
    score: float
    correct: bool


def scored_relations(
    gold_docs: Sequence[Mapping[str, Any]],
    pred_docs: Sequence[Mapping[str, Any]],
    joint: bool = False,
) -> tuple[list[Scored], int]:
    """(scored predictions marked correct/incorrect, total gold relations).

    With ``joint``, a relation's score is P(relation) x P(head) x P(tail): an end-to-end
    relation is only correct when both endpoint entities are, which a relation score
    alone does not know."""
    preds = {p["doc_id"]: p for p in pred_docs}
    items: list[Scored] = []
    gold_total = 0
    for gold in gold_docs:
        gs = {e["id"]: (e["start"], e["end"], e["label"]) for e in gold["entities"]}
        gold_rels = {(gs[r["head"]], r["label"], gs[r["tail"]]) for r in gold["relations"]}
        gold_total += len(gold_rels)
        pred = preds[gold["doc_id"]]
        ps = {e["id"]: (e["start"], e["end"], e["label"]) for e in pred["entities"]}
        entity_score = {e["id"]: float(e.get("score", 1.0)) for e in pred["entities"]}
        seen: set[Any] = set()
        for r in pred["relations"]:
            key = (ps[r["head"]], r["label"], ps[r["tail"]])
            if key in seen:
                continue
            seen.add(key)
            if "score" not in r:
                raise ValueError("relation predictions carry no score")
            score = float(r["score"])
            if joint:
                score *= entity_score[r["head"]] * entity_score[r["tail"]]
            items.append(Scored(gold["doc_id"], score, key in gold_rels))
    return items, gold_total


def _ranked(items: Sequence[Scored]) -> list[Scored]:
    return sorted(items, key=lambda s: (-s.score, s.doc_id))


def precision_coverage(items: Sequence[Scored], gold_total: int) -> list[dict[str, float]]:
    ranked = _ranked(items)
    rows = []
    for coverage in COVERAGE_GRID:
        k = max(1, round(coverage * len(ranked)))
        correct = sum(s.correct for s in ranked[:k])
        rows.append(
            {
                "coverage": coverage,
                "kept": k,
                "score_threshold": round(ranked[k - 1].score, 6),
                "precision": round(correct / k, 4),
                "retained_recall": round(correct / gold_total, 4) if gold_total else 0.0,
            }
        )
    return rows


def precision_at_coverage(
    items: Sequence[Scored], coverage: float, resamples: int = 1000, seed: int = 13
) -> dict[str, Any]:
    """Precision of the top ``coverage`` share, with a document bootstrap CI computed at
    the score threshold fixed on the full set."""
    ranked = _ranked(items)
    k = max(1, round(coverage * len(ranked)))
    threshold = ranked[k - 1].score
    by_doc: dict[str, list[Scored]] = {}
    for s in items:
        by_doc.setdefault(s.doc_id, []).append(s)
    docs = sorted(by_doc)
    rng = random.Random(seed)
    stats = []
    for _ in range(resamples):
        sample = [by_doc[docs[rng.randrange(len(docs))]] for _ in docs]
        kept = [s for group in sample for s in group if s.score >= threshold]
        if kept:
            stats.append(sum(s.correct for s in kept) / len(kept))
    stats.sort()
    kept_all = [s for s in items if s.score >= threshold]
    return {
        "coverage": coverage,
        "score_threshold": round(threshold, 6),
        "kept": len(kept_all),
        "precision": round(sum(s.correct for s in kept_all) / len(kept_all), 4),
        "precision_ci95": [
            round(stats[int(0.025 * len(stats))], 4),
            round(stats[min(len(stats) - 1, int(0.975 * len(stats)))], 4),
        ],
    }


def max_coverage_at_precision(items: Sequence[Scored], precision: float) -> dict[str, Any]:
    """Largest coverage whose kept predictions reach ``precision`` (0 if none)."""
    ranked = _ranked(items)
    best = 0
    correct = 0
    for k, s in enumerate(ranked, start=1):
        correct += s.correct
        if correct / k >= precision:
            best = k
    return {
        "target_precision": precision,
        "coverage": round(best / len(ranked), 4) if ranked else 0.0,
        "kept": best,
    }


def ece(scores: Sequence[float], correct: Sequence[bool], bins: int = 10) -> dict[str, Any]:
    table = []
    total = len(scores)
    error = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [i for i, s in enumerate(scores) if lo <= s < hi or (b == bins - 1 and s == 1.0)]
        if not idx:
            continue
        confidence = sum(scores[i] for i in idx) / len(idx)
        accuracy = sum(correct[i] for i in idx) / len(idx)
        error += len(idx) / total * abs(confidence - accuracy)
        table.append(
            {
                "bin": f"[{lo:.1f}, {hi:.1f})",
                "n": len(idx),
                "confidence": round(confidence, 4),
                "accuracy": round(accuracy, 4),
            }
        )
    brier = (
        sum((s - c) ** 2 for s, c in zip(scores, correct, strict=True)) / total if total else 0.0
    )
    return {"ece": round(error, 4), "brier": round(brier, 4), "reliability": table}


def _fold(doc_id: str, folds: int) -> int:
    return sum(doc_id.encode()) % folds


def cross_fitted_isotonic(items: Sequence[Scored], folds: int = 5) -> list[float]:
    """Calibrated score for each item, fitted only on documents in other folds."""
    calibrated = [0.0] * len(items)
    for fold in range(folds):
        train_idx = [i for i, s in enumerate(items) if _fold(s.doc_id, folds) != fold]
        test_idx = [i for i, s in enumerate(items) if _fold(s.doc_id, folds) == fold]
        if not test_idx:
            continue
        model = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        model.fit([items[i].score for i in train_idx], [float(items[i].correct) for i in train_idx])
        for i, value in zip(
            test_idx, model.predict([items[i].score for i in test_idx]), strict=True
        ):
            calibrated[i] = float(value)
    return calibrated


def fit_isotonic(items: Sequence[Scored]) -> dict[str, list[float]]:
    """A calibrator fitted on all items, serialized as its step function."""
    model = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    model.fit([s.score for s in items], [float(s.correct) for s in items])
    return {
        "x": [float(x) for x in model.X_thresholds_],
        "y": [float(y) for y in model.y_thresholds_],
    }


def confidence_report(
    gold_docs: Sequence[Mapping[str, Any]],
    pred_docs: Sequence[Mapping[str, Any]],
    joint: bool = False,
) -> dict[str, Any]:
    items, gold_total = scored_relations(gold_docs, pred_docs, joint=joint)
    raw = [s.score for s in items]
    correct = [s.correct for s in items]
    calibrated = cross_fitted_isotonic(items)
    return {
        "score": "P(relation) x P(head) x P(tail)" if joint else "P(relation)",
        "predicted_relations": len(items),
        "gold_relations": gold_total,
        "precision_coverage": precision_coverage(items, gold_total),
        "target": {
            "precision_at_30pct_coverage": precision_at_coverage(items, 0.30),
            "coverage_at_95pct_precision": max_coverage_at_precision(items, 0.95),
        },
        "calibration": {
            "method": "isotonic regression, 5-fold document-level cross-fitting on dev",
            "before": ece(raw, correct),
            "after": ece(calibrated, correct),
        },
        "calibrator": fit_isotonic(items),
    }
