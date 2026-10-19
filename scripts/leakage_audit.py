"""Residual training overlap after dedup, measured by shingle containment.

    uv run python scripts/leakage_audit.py

Dedup links documents by Jaccard similarity, which stays low when a short document is an
excerpt of, or a kit variant inside, a much longer training document. For every dev and
test document, and every protocol of the new annotation sets, this audit measures the
share of its 5-word shingles found in its nearest training document (containment) and
anywhere in training (union containment). It lists the documents at or above
``FLAG_CONTAINMENT`` that dedup did not already record as a template sibling.

Dev: end-to-end relation F1 per containment bucket, from each system's saved dev
predictions (--pred name=path; the defaults are the frozen releases' files).
Test: text overlap and gold counts only. No predictions are read, so nothing about model
errors on the locked split is inspected. The frozen splits are not changed.
Writes reports/leakage/train-overlap.{json,md}.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from protocolledger.data.annotation_sets import load_sources
from protocolledger.data.dedup import Overlap, reference_overlap
from protocolledger.data.splits import load_split
from protocolledger.eval.scorer import evaluate

ROOT = Path(__file__).resolve().parents[1]
FLAG_CONTAINMENT = 0.5  # the same cut-off dedup uses for template siblings (Jaccard)
BUCKETS: tuple[tuple[str, float, float], ...] = (
    ("< 0.1", 0.0, 0.1),
    ("0.1 to 0.5", 0.1, FLAG_CONTAINMENT),
    ("≥ 0.5", FLAG_CONTAINMENT, 1.01),
)
DEFAULT_PREDICTIONS = {
    "Rules": "artifacts/rules/dev-end_to_end.jsonl",
    "CRF + LR": "artifacts/traditional/dev-end_to_end.jsonl",
    "SciBERT": "artifacts/bundles/scibert-uniform-negatives-s21-7dc7a1893e-dev-predictions.jsonl",
}
NEW_SETS = ("later-domain", "challenge")


def bucket_of(value: float) -> str:
    return next(name for name, lo, hi in BUCKETS if lo <= value < hi)


def distribution(overlaps: Mapping[str, Overlap]) -> dict[str, Any]:
    def quantiles(values: list[float]) -> dict[str, float]:
        v = sorted(values)
        return {
            "median": round(v[len(v) // 2], 4),
            "p90": round(v[int(0.9 * len(v))], 4),
            "max": round(v[-1], 4),
        }

    return {
        "documents": len(overlaps),
        "containment": quantiles([o.containment for o in overlaps.values()]),
        "union_containment": quantiles([o.union_containment for o in overlaps.values()]),
        "jaccard": quantiles([o.jaccard for o in overlaps.values()]),
        "buckets": {
            name: sum(bucket_of(o.containment) == name for o in overlaps.values())
            for name, _, _ in BUCKETS
        },
    }


def flagged(
    overlaps: Mapping[str, Overlap], siblings: Mapping[str, Any], titles: Mapping[str, str]
) -> list[dict[str, Any]]:
    return [
        {
            "doc_id": doc_id,
            "title": titles[doc_id],
            "nearest_title": titles[o.nearest],
            **o.to_json(),
        }
        for doc_id, o in sorted(overlaps.items(), key=lambda kv: -kv[1].containment)
        if o.containment >= FLAG_CONTAINMENT and doc_id not in siblings
    ]


def dev_slices(
    dev: Sequence[Mapping[str, Any]],
    overlaps: Mapping[str, Overlap],
    predictions: Mapping[str, Path],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, lo, hi in BUCKETS:
        gold = [d for d in dev if lo <= overlaps[d["doc_id"]].containment < hi]
        ids = {d["doc_id"] for d in gold}
        row: dict[str, Any] = {
            "documents": len(gold),
            "gold_relations": sum(len(d["relations"]) for d in gold),
        }
        for system, path in predictions.items():
            preds = [
                p
                for p in (json.loads(line) for line in path.read_text("utf-8").splitlines() if line)
                if p["doc_id"] in ids
            ]
            rel = evaluate(gold, preds)["relations"]["micro"] if gold else None
            row[system] = (
                {"f1": rel["f1"], "f1_ci95": rel["f1_ci95"], "recall": rel["recall"]}
                if rel
                else None
            )
        out[name] = row
    return out


def test_counts(
    test: Sequence[Mapping[str, Any]], overlaps: Mapping[str, Overlap]
) -> dict[str, Any]:
    out = {}
    for name, lo, hi in BUCKETS:
        docs = [d for d in test if lo <= overlaps[d["doc_id"]].containment < hi]
        out[name] = {
            "documents": len(docs),
            "gold_relations": sum(len(d["relations"]) for d in docs),
        }
    total = sum(r["gold_relations"] for r in out.values())
    for row in out.values():
        row["share_of_gold_relations"] = round(row["gold_relations"] / total, 4)
    return out


def render(report: Mapping[str, Any]) -> str:
    lines = [
        "# Residual training overlap (shingle containment)",
        "",
        "Generated by `scripts/leakage_audit.py`. **Containment** is the share of a "
        "document's case-folded 5-word shingles that occur in its nearest training document; "
        "**union containment** counts shingles found anywhere in training. Dedup used Jaccard, "
        "which stays low when a short document sits inside a longer one. The frozen splits "
        "are not changed by this audit.",
        "",
        "## Distribution",
        "",
        "| Documents | n | Containment median / p90 / max | Union containment median / p90 / max "
        "| < 0.1 | 0.1 to 0.5 | ≥ 0.5 |",
        "|---|---:|---|---|---:|---:|---:|",
    ]
    for name, d in report["distribution"].items():
        c, u, b = d["containment"], d["union_containment"], d["buckets"]
        lines.append(
            f"| {name} | {d['documents']} | {c['median']:.3f} / {c['p90']:.3f} / {c['max']:.3f} "
            f"| {u['median']:.3f} / {u['p90']:.3f} / {u['max']:.3f} "
            f"| {b['< 0.1']} | {b['0.1 to 0.5']} | {b['≥ 0.5']} |"
        )
    lines += [
        "",
        f"## Documents at containment ≥ {FLAG_CONTAINMENT} not recorded as template siblings",
        "",
        "| Document | Title | Nearest training document | Its title | Containment | Jaccard |",
        "|---|---|---|---|---:|---:|",
    ]
    for group in report["flagged"].values():
        for f in group:
            lines.append(
                f"| `{f['doc_id']}` | {f['title']} | `{f['nearest']}` | {f['nearest_title']} "
                f"| {f['containment']:.3f} | {f['jaccard']:.3f} |"
            )
    systems = list(report["predictions"])
    lines += [
        "",
        "## Dev: end-to-end relation F1 by containment",
        "",
        "Document-level bootstrap 95% CIs. Few documents sit in the high-overlap bucket, so "
        "its intervals are wide.",
        "",
        "| Containment | Documents | Gold relations | " + " | ".join(systems) + " |",
        "|---|---:|---:|" + "---:|" * len(systems),
    ]
    for name, row in report["dev_by_containment"].items():
        cells = []
        for s in systems:
            r = row[s]
            if r is None:
                cells.append("n/a")
            else:
                lo, hi = r["f1_ci95"]
                cells.append(f"{r['f1']:.3f} [{lo:.3f}, {hi:.3f}]")
        lines.append(
            f"| {name} | {row['documents']} | {row['gold_relations']} | " + " | ".join(cells) + " |"
        )
    lines += [
        "",
        "## Test: exposure only (no predictions read)",
        "",
        "| Containment | Documents | Gold relations | Share of gold relations |",
        "|---|---:|---:|---:|",
    ]
    for name, row in report["test_exposure"].items():
        lines.append(
            f"| {name} | {row['documents']} | {row['gold_relations']} "
            f"| {row['share_of_gold_relations']:.1%} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pred", action="append", default=[], metavar="NAME=PATH")
    args = parser.parse_args(argv)
    chosen = dict(p.split("=", 1) for p in args.pred) or DEFAULT_PREDICTIONS
    predictions = {name: ROOT / path for name, path in chosen.items()}
    missing = [str(p) for p in predictions.values() if not p.exists()]
    if missing:
        raise SystemExit(f"error: missing dev predictions: {', '.join(missing)}")

    splits = {s: load_split(ROOT, s) for s in ("train", "dev", "test")}
    titles = {d["doc_id"]: d["text"].split("\n", 1)[0].strip() for v in splits.values() for d in v}
    train_texts = {d["doc_id"]: d["text"] for d in splits["train"]}
    manifest = json.loads((ROOT / "data/manifests/splits.json").read_text("utf-8"))
    siblings = manifest["template_siblings"]
    overlaps = {
        s: reference_overlap({d["doc_id"]: d["text"] for d in splits[s]}, train_texts)
        for s in ("dev", "test")
    }
    corpus = {d["doc_id"]: d["text"] for v in splits.values() for d in v}
    for set_name in NEW_SETS:
        sources = load_sources(ROOT / "data" / "annotation" / set_name)
        texts = {f"{set_name}/{s['source_id']}": s["text"] for s in sources}
        titles.update({f"{set_name}/{s['source_id']}": s["title"] for s in sources})
        # New sets are compared with the whole corpus: a copy of any split would leak.
        overlaps[set_name] = reference_overlap(texts, corpus)

    report = {
        "rules": {
            "shingle_words": manifest["rules"]["shingle_words"],
            "reference": "train for dev/test; train + dev + test for the new sets",
            "flag_containment": FLAG_CONTAINMENT,
            "buckets": [name for name, _, _ in BUCKETS],
        },
        "predictions": {name: str(path.relative_to(ROOT)) for name, path in predictions.items()},
        "distribution": {s: distribution(o) for s, o in overlaps.items()},
        "flagged": {s: flagged(o, siblings, titles) for s, o in overlaps.items()},
        "dev_by_containment": dev_slices(splits["dev"], overlaps["dev"], predictions),
        "test_exposure": test_counts(splits["test"], overlaps["test"]),
        "overlaps": {s: {k: v.to_json() for k, v in o.items()} for s, o in overlaps.items()},
    }
    out = ROOT / "reports" / "leakage"
    out.mkdir(parents=True, exist_ok=True)
    (out / "train-overlap.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False) + "\n", "utf-8"
    )
    text = render(report)
    (out / "train-overlap.md").write_text(text, "utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
