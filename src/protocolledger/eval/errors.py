"""Error taxonomy for entity and relation predictions.

Entities: every gold entity and every prediction is classified exactly once:

* ``correct``: same span and type
* ``wrong_type``: same span, different type
* ``wrong_boundary``: overlapping span, same type
* ``wrong_boundary_and_type``: overlapping span, different type
* ``missed`` (gold) / ``spurious`` (prediction): nothing overlapping

Relations: every gold relation that is not predicted exactly gets one cause, checked in
this order:

* ``endpoint_error``: an endpoint entity was not predicted exactly (an entity error
  cascading into the relation)
* ``wrong_label``: the same ordered pair was predicted with a different label
* ``wrong_direction``: the reversed pair was predicted with this label
* ``wrong_attachment``: this label was predicted from the same head to a different tail,
  or into the same tail from a different head (e.g. "5 mL" attached to the wrong thing)
* ``missed``: endpoints correct, but nothing relates them

Normalization errors and unsupported inferences need human-checked labels and are not
classified automatically.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

Span = tuple[int, int, str]

ENTITY_CATEGORIES = (
    "correct",
    "wrong_type",
    "wrong_boundary",
    "wrong_boundary_and_type",
    "missed",
)
RELATION_CATEGORIES = (
    "correct",
    "endpoint_error",
    "wrong_label",
    "wrong_direction",
    "wrong_attachment",
    "missed",
)


def _overlaps(a: Span, b: Span) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def classify_entity(gold: Span, predicted: Iterable[Span]) -> str:
    preds = list(predicted)
    if gold in preds:
        return "correct"
    if any(p[:2] == gold[:2] for p in preds):
        return "wrong_type"
    overlapping = [p for p in preds if _overlaps(p, gold)]
    if any(p[2] == gold[2] for p in overlapping):
        return "wrong_boundary"
    if overlapping:
        return "wrong_boundary_and_type"
    return "missed"


def _spans(doc: Mapping[str, Any]) -> dict[str, Span]:
    return {e["id"]: (e["start"], e["end"], e["label"]) for e in doc["entities"]}


def _relations(doc: Mapping[str, Any]) -> set[tuple[Span, str, Span]]:
    s = _spans(doc)
    return {(s[r["head"]], r["label"], s[r["tail"]]) for r in doc["relations"]}


def classify_relation(
    gold: tuple[Span, str, Span],
    pred_entities: set[Span],
    pred_relations: set[tuple[Span, str, Span]],
) -> str:
    head, label, tail = gold
    if gold in pred_relations:
        return "correct"
    if head not in pred_entities or tail not in pred_entities:
        return "endpoint_error"
    if any(h == head and t == tail for h, _, t in pred_relations):
        return "wrong_label"
    if (tail, label, head) in pred_relations:
        return "wrong_direction"
    if any(lab == label and ((h == head) != (t == tail)) for h, lab, t in pred_relations):
        return "wrong_attachment"
    return "missed"


def _context(text: str, spans: Sequence[Span], width: int = 60) -> str:
    """The surrounding text with each span wrapped in [[...]]."""
    lo = max(0, min(s[0] for s in spans) - width)
    hi = min(len(text), max(s[1] for s in spans) + width)
    out, cursor = [], lo
    for start, end, _ in sorted(set(spans)):
        out += [text[cursor:start], "[[", text[start:end], "]]"]
        cursor = end
    out.append(text[cursor:hi])
    return " ".join("".join(out).split())


def analyze(
    gold_docs: Sequence[Mapping[str, Any]],
    pred_docs: Sequence[Mapping[str, Any]],
    examples_per_category: int = 8,
    unseen_names: set[str] | None = None,
    sibling_docs: set[str] | None = None,
) -> dict[str, Any]:
    preds = {p["doc_id"]: p for p in pred_docs}
    entity_counts: Counter[str] = Counter()
    entity_by_label: dict[str, Counter[str]] = defaultdict(Counter)
    spurious_by_label: Counter[str] = Counter()
    relation_counts: Counter[str] = Counter()
    relation_by_label: dict[str, Counter[str]] = defaultdict(Counter)
    spurious_relations: Counter[str] = Counter()
    examples: dict[str, list[str]] = defaultdict(list)
    unseen: Counter[str] = Counter()
    siblings: dict[str, Counter[str]] = defaultdict(Counter)

    for gold in gold_docs:
        pred = preds[gold["doc_id"]]
        text = gold["text"]
        g_ents, p_ents = set(_spans(gold).values()), set(_spans(pred).values())
        g_rels, p_rels = _relations(gold), _relations(pred)

        for span in sorted(g_ents):
            cat = classify_entity(span, p_ents)
            entity_counts[cat] += 1
            entity_by_label[span[2]][cat] += 1
            if cat != "correct" and len(examples[f"entity/{cat}"]) < examples_per_category:
                near = [p for p in p_ents if _overlaps(p, span)]
                found = (
                    ", ".join(f"{p[2]} '{text[p[0] : p[1]]}'" for p in sorted(near)) or "nothing"
                )
                examples[f"entity/{cat}"].append(
                    f"{gold['doc_id']}: gold {span[2]} '{text[span[0] : span[1]]}', predicted "
                    f"{found} | {_context(text, [span, *near])}"
                )
            if unseen_names is not None and span[2] == "Reagent":
                key = "unseen" if text[span[0] : span[1]].casefold() in unseen_names else "seen"
                unseen[f"{key}_total"] += 1
                unseen[f"{key}_correct"] += cat == "correct"
        for span in sorted(p_ents):
            if not any(_overlaps(span, g) for g in g_ents):
                spurious_by_label[span[2]] += 1

        for rel in sorted(g_rels):
            cat = classify_relation(rel, p_ents, p_rels)
            relation_counts[cat] += 1
            relation_by_label[rel[1]][cat] += 1
            if sibling_docs is not None:
                group = "with_template_sibling" if gold["doc_id"] in sibling_docs else "without"
                siblings[group][cat] += 1
            if cat not in ("correct", "endpoint_error") and (
                len(examples[f"relation/{cat}"]) < examples_per_category
            ):
                head, label, tail = rel
                got = [r for r in p_rels if r[0] in (head, tail) or r[2] in (head, tail)]
                shown = (
                    "; ".join(
                        f"{text[h[0] : h[1]]} -{lab}-> {text[t[0] : t[1]]}"
                        for h, lab, t in sorted(got)
                    )
                    or "nothing"
                )
                examples[f"relation/{cat}"].append(
                    f"{gold['doc_id']}: gold {text[head[0] : head[1]]} -{label}-> "
                    f"{text[tail[0] : tail[1]]}; predicted {shown} | {_context(text, [head, tail])}"
                )
        for rel in p_rels - g_rels:
            head, _, tail = rel
            both_gold = head in g_ents and tail in g_ents
            spurious_relations["between_gold_entities" if both_gold else "spurious_endpoint"] += 1

    def share(c: Counter[str]) -> dict[str, Any]:
        total = sum(c.values())
        return {k: {"count": c[k], "share": round(c[k] / total, 4) if total else 0.0} for k in c}

    report: dict[str, Any] = {
        "entities": {
            "gold_total": sum(entity_counts.values()),
            "categories": share(entity_counts),
            "by_label": {lab: dict(c) for lab, c in sorted(entity_by_label.items())},
            "spurious_by_label": dict(spurious_by_label.most_common()),
        },
        "relations": {
            "gold_total": sum(relation_counts.values()),
            "categories": share(relation_counts),
            "by_label": {lab: dict(c) for lab, c in sorted(relation_by_label.items())},
            "spurious": dict(spurious_relations),
        },
        "examples": dict(examples),
        "not_automated": ["normalization_error", "unsupported_inference"],
    }
    if unseen_names is not None:
        report["slices"] = report.get("slices", {})
        report["slices"]["reagent_names"] = {
            k: {
                "gold": unseen[f"{k}_total"],
                "recall": round(unseen[f"{k}_correct"] / unseen[f"{k}_total"], 4)
                if unseen[f"{k}_total"]
                else None,
            }
            for k in ("seen", "unseen")
        }
    if sibling_docs is not None:
        report.setdefault("slices", {})["template_siblings"] = {
            group: {
                "gold_relations": sum(c.values()),
                "relation_recall": round(c["correct"] / sum(c.values()), 4) if c else None,
            }
            for group, c in siblings.items()
        }
    return report


def render_markdown(report: Mapping[str, Any], title: str) -> str:
    lines = [f"# Error analysis: {title}", ""]
    for kind, cats in (("entities", ENTITY_CATEGORIES), ("relations", RELATION_CATEGORIES)):
        block = report[kind]
        lines += [
            f"## {kind.capitalize()} ({block['gold_total']} gold)",
            "",
            "| Category | Count | Share |",
            "|---|---:|---:|",
        ]
        for cat in cats:
            if cat in block["categories"]:
                c = block["categories"][cat]
                lines.append(f"| {cat.replace('_', ' ')} | {c['count']} | {c['share']:.1%} |")
        lines.append("")
    spurious = report["entities"]["spurious_by_label"]
    lines += [
        "Spurious entities (no overlapping gold): "
        + ", ".join(f"{k} {v}" for k, v in list(spurious.items())[:8]),
        "",
    ]
    sp = report["relations"]["spurious"]
    lines += [
        f"Spurious relations: {sp.get('between_gold_entities', 0)} between gold entities, "
        f"{sp.get('spurious_endpoint', 0)} with a spurious endpoint.",
        "",
    ]
    if "slices" in report:
        lines += ["## Slices", ""]
        names = report["slices"].get("reagent_names")
        if names:
            lines.append("| Reagent names | Gold | Recall |")
            lines.append("|---|---:|---:|")
            for k, v in names.items():
                recall = "n/a" if v["recall"] is None else f"{v['recall']:.3f}"
                lines.append(f"| {k} in training | {v['gold']} | {recall} |")
            lines.append("")
        sib = report["slices"].get("template_siblings")
        if sib:
            lines.append("| Documents | Gold relations | Relation recall |")
            lines.append("|---|---:|---:|")
            for k, v in sib.items():
                lines.append(
                    f"| {k.replace('_', ' ')} | {v['gold_relations']} | "
                    f"{v['relation_recall']:.3f} |"
                )
            lines.append("")
    if "examples" in report:
        lines += ["## Examples", ""]
        for key, items in report["examples"].items():
            lines += [f"### {key}", ""] + [f"- {item}" for item in items] + [""]
    else:
        lines += ["Examples withheld: this is a locked test portion.", ""]
    lines += [
        "Not classified automatically: normalization errors and unsupported inferences "
        "(need human-checked labels).",
        "",
    ]
    return "\n".join(lines)
