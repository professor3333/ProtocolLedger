"""The single scorer used for every reported number.

Predictions are one record per gold document::

    {"doc_id": ..., "entities": [{"id", "label", "start", "end"}, ...],
     "relations": [{"head", "label", "tail"}, ...]}

Matching rules:

* **Entity** (strict): same document, ``start``, ``end`` and label.
* **Relation** (end-to-end): same relation label and direction, and both endpoints match
  as strict entities (span *and* entity label). Scoring predictions made from gold
  entities with the same function gives relation F1 with gold entities.
* **Quantity attachment**: for each gold relation whose tail is a quantity-type entity,
  correct when some predicted relation links the same head span to the same tail span,
  regardless of labels. It isolates "does this value belong to the right thing?".
* **Complete step**: a step (any line after the title) that has at least one gold or
  predicted annotation is exact when its predicted entities and relations equal gold.
  Entities are assigned to the step containing their start offset, relations to their
  head entity's step.

Duplicated predictions are collapsed, so a system cannot gain or lose by repeating
itself. Confidence intervals come from a document-level bootstrap because sentences in
the same protocol are correlated.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from protocolledger.data.schema import ENTITY_LABELS, RELATION_LABELS

QUANTITY_LABELS: frozenset[str] = frozenset(
    {
        "Amount",
        "Concentration",
        "Generic-Measure",
        "Numerical",
        "Size",
        "Speed",
        "Temperature",
        "Time",
        "pH",
    }
)

Span = tuple[int, int, str]  # start, end, entity label
RelationKey = tuple[Span, str, Span]  # head, relation label, tail


class PredictionError(ValueError):
    """Predictions are malformed or do not line up with the gold documents."""


@dataclass(frozen=True)
class Counts:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    def __add__(self, other: Counts) -> Counts:
        return Counts(self.tp + other.tp, self.fp + other.fp, self.fn + other.fn)

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else 0.0

    @property
    def f1(self) -> float:
        denom = 2 * self.tp + self.fp + self.fn
        return 2 * self.tp / denom if denom else 0.0


def _compare(gold: set[Any], pred: set[Any]) -> Counts:
    tp = len(gold & pred)
    return Counts(tp, len(pred) - tp, len(gold) - tp)


def _spans(doc: Mapping[str, Any]) -> dict[str, Span]:
    return {e["id"]: (e["start"], e["end"], e["label"]) for e in doc["entities"]}


def _relations(doc: Mapping[str, Any], spans: Mapping[str, Span]) -> set[RelationKey]:
    return {(spans[r["head"]], r["label"], spans[r["tail"]]) for r in doc["relations"]}


def validate_prediction(pred: Mapping[str, Any], gold: Mapping[str, Any]) -> None:
    text_len = len(gold["text"])
    ids: set[str] = set()
    for e in pred.get("entities", []):
        eid = e.get("id")
        if not isinstance(eid, str) or eid in ids:
            raise PredictionError(f"{gold['doc_id']}: missing or duplicate entity id {eid!r}")
        ids.add(eid)
        if e.get("label") not in ENTITY_LABELS:
            raise PredictionError(f"{gold['doc_id']} {eid}: unknown label {e.get('label')!r}")
        start, end = e.get("start"), e.get("end")
        if not (isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= text_len):
            raise PredictionError(f"{gold['doc_id']} {eid}: bad offsets [{start}, {end})")
    for r in pred.get("relations", []):
        if r.get("label") not in RELATION_LABELS:
            raise PredictionError(f"{gold['doc_id']}: unknown relation label {r.get('label')!r}")
        if r.get("head") not in ids or r.get("tail") not in ids:
            raise PredictionError(f"{gold['doc_id']}: relation endpoint not among entities")


def _step_of(steps: Sequence[Sequence[int]], offset: int) -> int:
    for i, (start, end) in enumerate(steps):
        if start <= offset <= end:
            return i
    return -1


@dataclass
class DocResult:
    doc_id: str
    entities: dict[str, Counts] = field(default_factory=dict)
    relations: dict[str, Counts] = field(default_factory=dict)
    attachment_correct: int = 0
    attachment_total: int = 0
    steps_exact: int = 0
    steps_total: int = 0

    def entity_micro(self) -> Counts:
        return sum(self.entities.values(), Counts())

    def relation_micro(self) -> Counts:
        return sum(self.relations.values(), Counts())


def score_document(gold: Mapping[str, Any], pred: Mapping[str, Any]) -> DocResult:
    validate_prediction(pred, gold)
    gspans, pspans = _spans(gold), _spans(pred)
    gents, pents = set(gspans.values()), set(pspans.values())
    grels, prels = _relations(gold, gspans), _relations(pred, pspans)

    result = DocResult(gold["doc_id"])
    for label in ENTITY_LABELS:
        g = {s for s in gents if s[2] == label}
        p = {s for s in pents if s[2] == label}
        if g or p:
            result.entities[label] = _compare(g, p)
    for label in RELATION_LABELS:
        g_rel = {r for r in grels if r[1] == label}
        p_rel = {r for r in prels if r[1] == label}
        if g_rel or p_rel:
            result.relations[label] = _compare(g_rel, p_rel)

    pred_links = {(h[:2], t[:2]) for h, _, t in prels}
    for head, _, tail in grels:
        if tail[2] in QUANTITY_LABELS:
            result.attachment_total += 1
            result.attachment_correct += (head[:2], tail[:2]) in pred_links

    steps = gold["steps"]
    by_step: dict[int, list[set[Any]]] = {}
    for which, items in ((0, gents), (1, pents)):
        for span in items:
            by_step.setdefault(_step_of(steps, span[0]), [set(), set(), set(), set()])[which].add(
                span
            )
    for which, rels in ((2, grels), (3, prels)):
        for rel in rels:
            by_step.setdefault(_step_of(steps, rel[0][0]), [set(), set(), set(), set()])[which].add(
                rel
            )
    for step, (ge, pe, gr, pr) in by_step.items():
        if step <= 0:  # the title line is not a step
            continue
        result.steps_total += 1
        result.steps_exact += ge == pe and gr == pr
    return result


def _ratio(num: int, den: int) -> float:
    return num / den if den else 0.0


def bootstrap_ci(
    results: Sequence[DocResult],
    statistic: Callable[[Sequence[DocResult]], float],
    *,
    resamples: int = 1000,
    seed: int = 13,
    level: float = 0.95,
) -> tuple[float, float]:
    """Percentile interval over documents resampled with replacement."""
    if not results:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(results)
    stats = sorted(
        statistic([results[rng.randrange(n)] for _ in range(n)]) for _ in range(resamples)
    )
    lo = stats[int((1 - level) / 2 * resamples)]
    hi = stats[min(resamples - 1, int((1 + level) / 2 * resamples))]
    return (lo, hi)


def _micro(results: Iterable[DocResult], kind: str) -> Counts:
    if kind == "entities":
        return sum((r.entity_micro() for r in results), Counts())
    return sum((r.relation_micro() for r in results), Counts())


def _block(results: Sequence[DocResult], kind: str, resamples: int, seed: int) -> dict[str, Any]:
    micro = _micro(results, kind)
    per_label: dict[str, Counts] = {}
    for r in results:
        for label, counts in getattr(r, kind).items():
            per_label[label] = per_label.get(label, Counts()) + counts
    labels = sorted(ENTITY_LABELS if kind == "entities" else RELATION_LABELS)
    rows = {}
    for label in labels:
        c = per_label.get(label, Counts())
        rows[label] = {
            "precision": round(c.precision, 4),
            "recall": round(c.recall, 4),
            "f1": round(c.f1, 4),
            "support": c.tp + c.fn,
            "predicted": c.tp + c.fp,
        }
    supported = [rows[label]["f1"] for label in labels if rows[label]["support"] > 0]
    ci = bootstrap_ci(results, lambda rs: _micro(rs, kind).f1, resamples=resamples, seed=seed)
    return {
        "micro": {
            "precision": round(micro.precision, 4),
            "recall": round(micro.recall, 4),
            "f1": round(micro.f1, 4),
            "f1_ci95": [round(ci[0], 4), round(ci[1], 4)],
            "tp": micro.tp,
            "fp": micro.fp,
            "fn": micro.fn,
        },
        "macro_f1": round(sum(supported) / len(supported), 4) if supported else 0.0,
        "macro_f1_labels": len(supported),
        "per_label": rows,
    }


def evaluate(
    gold_docs: Sequence[Mapping[str, Any]],
    pred_docs: Sequence[Mapping[str, Any]],
    *,
    resamples: int = 1000,
    seed: int = 13,
) -> dict[str, Any]:
    gold_ids = [d["doc_id"] for d in gold_docs]
    pred_by_id: dict[str, Mapping[str, Any]] = {}
    for p in pred_docs:
        if p["doc_id"] in pred_by_id:
            raise PredictionError(f"duplicate prediction for {p['doc_id']}")
        pred_by_id[p["doc_id"]] = p
    missing = set(gold_ids) - pred_by_id.keys()
    extra = pred_by_id.keys() - set(gold_ids)
    if missing or extra:
        raise PredictionError(
            f"prediction documents differ from gold: {len(missing)} missing, {len(extra)} extra"
        )
    results = [score_document(g, pred_by_id[g["doc_id"]]) for g in gold_docs]

    def attach(rs: Sequence[DocResult]) -> float:
        return _ratio(sum(r.attachment_correct for r in rs), sum(r.attachment_total for r in rs))

    def steps(rs: Sequence[DocResult]) -> float:
        return _ratio(sum(r.steps_exact for r in rs), sum(r.steps_total for r in rs))

    attach_ci = bootstrap_ci(results, attach, resamples=resamples, seed=seed)
    steps_ci = bootstrap_ci(results, steps, resamples=resamples, seed=seed)
    return {
        "documents": len(results),
        "bootstrap": {"unit": "document", "resamples": resamples, "seed": seed},
        "entities": _block(results, "entities", resamples, seed),
        "relations": _block(results, "relations", resamples, seed),
        "quantity_attachment": {
            "accuracy": round(attach(results), 4),
            "ci95": [round(attach_ci[0], 4), round(attach_ci[1], 4)],
            "correct": sum(r.attachment_correct for r in results),
            "total": sum(r.attachment_total for r in results),
        },
        "complete_steps": {
            "exact_match": round(steps(results), 4),
            "ci95": [round(steps_ci[0], 4), round(steps_ci[1], 4)],
            "exact": sum(r.steps_exact for r in results),
            "total": sum(r.steps_total for r in results),
        },
    }


def render_markdown(report: Mapping[str, Any], title: str) -> str:
    """A compact human-readable summary of an evaluation report."""
    e, r = report["entities"]["micro"], report["relations"]["micro"]
    q, s = report["quantity_attachment"], report["complete_steps"]

    def ci(pair: Sequence[float]) -> str:
        return f"[{pair[0]:.3f}, {pair[1]:.3f}]"

    lines = [
        f"### {title}",
        "",
        f"{report['documents']} documents; 95% CIs from a document-level bootstrap.",
        "",
        "| Metric | Value | 95% CI |",
        "|---|---:|---|",
        f"| Entity micro-F1 (strict) | {e['f1']:.3f} | {ci(e['f1_ci95'])} |",
        f"| Entity macro-F1 ({report['entities']['macro_f1_labels']} labels) "
        f"| {report['entities']['macro_f1']:.3f} | |",
        f"| Relation micro-F1 (end-to-end) | {r['f1']:.3f} | {ci(r['f1_ci95'])} |",
        f"| Relation macro-F1 ({report['relations']['macro_f1_labels']} labels) "
        f"| {report['relations']['macro_f1']:.3f} | |",
        f"| Quantity attachment accuracy ({q['total']}) | {q['accuracy']:.3f} | {ci(q['ci95'])} |",
        f"| Complete-step exact match ({s['total']}) | {s['exact_match']:.3f} | {ci(s['ci95'])} |",
        "",
    ]
    for kind in ("entities", "relations"):
        lines += [
            f"| {'Entity' if kind == 'entities' else 'Relation'} label | P | R | F1 | Support |",
            "|---|---:|---:|---:|---:|",
        ]
        rows = report[kind]["per_label"]
        for label, row in sorted(rows.items(), key=lambda kv: -kv[1]["support"]):
            lines.append(
                f"| {label} | {row['precision']:.3f} | {row['recall']:.3f} "
                f"| {row['f1']:.3f} | {row['support']} |"
            )
        lines.append("")
    return "\n".join(lines)
