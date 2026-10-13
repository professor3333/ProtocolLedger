"""Score a model bundle on a new annotation set with the shared scorer.

    uv run --extra neural python scripts/evaluate_annotation_set.py --set later-domain \\
        --split dev --bundle artifacts/bundles/<model_version> [--reference machine]

The test portion is locked: --split test requires --locked-test-release, and is meant to
be run once per declared release. Writes reports/annotation_sets/<set>-<split>-<model>.json.

--reference machine scores against machine_labels.jsonl instead of the human gold.jsonl.
Those labels are machine-generated and not human-reviewed, so the report says
"vs. machine labels" and its numbers are agreement with them, not accuracy. For sets whose
steps carry challenge categories, the report adds entity and relation micro-F1 for the
steps of each category. The error taxonomy (protocolledger.eval.errors) is written next to
the report as <name>-errors.{json,md}; "unseen" reagent names are those absent from train.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from protocolledger.data.annotation_sets import load_sources
from protocolledger.data.splits import load_split
from protocolledger.eval.errors import analyze
from protocolledger.eval.errors import render_markdown as render_errors
from protocolledger.eval.scorer import evaluate, render_markdown
from protocolledger.serve.bundle import load_bundle

ROOT = Path(__file__).resolve().parents[1]
REFERENCES = {
    "gold": ("gold.jsonl", "human gold"),
    "machine": ("machine_labels.jsonl", "machine labels (machine-generated, not human-reviewed)"),
}


def restrict(doc: Mapping[str, Any], lines: set[int]) -> dict[str, Any]:
    """Keep the entities that start on the given step lines, and relations between them."""
    steps = doc["steps"]
    kept = [
        e
        for e in doc["entities"]
        if any(steps[i][0] <= e["start"] < steps[i][1] for i in lines if i < len(steps))
    ]
    ids = {e["id"] for e in kept}
    relations = [r for r in doc["relations"] if r["head"] in ids and r["tail"] in ids]
    return {**doc, "entities": kept, "relations": relations}


def _micro(report: Mapping[str, Any], kind: str) -> dict[str, Any]:
    m = report[kind]["micro"]
    return {"f1": m["f1"], "f1_ci95": m["f1_ci95"], "support": m["tp"] + m["fn"]}


def category_slices(
    reference: Sequence[Mapping[str, Any]],
    preds: Sequence[Mapping[str, Any]],
    sources: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    lines_by_category: dict[str, dict[str, set[int]]] = {}
    for doc in reference:
        for step in sources[doc["doc_id"].split("/", 1)[1]].get("steps", []):
            for category in step.get("categories", []):
                lines_by_category.setdefault(category, {}).setdefault(doc["doc_id"], set()).add(
                    step["line"]
                )
    pred_by_id = {p["doc_id"]: p for p in preds}
    out = {}
    for category, by_doc in sorted(lines_by_category.items()):
        gold = [restrict(d, by_doc[d["doc_id"]]) for d in reference if d["doc_id"] in by_doc]
        pred = [
            restrict({**pred_by_id[d["doc_id"]], "steps": d["steps"]}, by_doc[d["doc_id"]])
            for d in gold
        ]
        report = evaluate(gold, pred)
        out[category] = {
            "documents": len(gold),
            "steps": sum(len(v) for v in by_doc.values()),
            "entities": _micro(report, "entities"),
            "relations": _micro(report, "relations"),
        }
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--set", required=True, dest="set_name")
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--locked-test-release", default=None)
    parser.add_argument("--reference", choices=sorted(REFERENCES), default="gold")
    args = parser.parse_args(argv)
    if args.split == "test" and not args.locked_test_release:
        raise SystemExit("error: the test portion is locked; pass --locked-test-release")
    set_dir = ROOT / "data" / "annotation" / args.set_name
    filename, reference_name = REFERENCES[args.reference]
    path = set_dir / filename
    gold = [
        d
        for d in (json.loads(line) for line in path.read_text("utf-8").splitlines() if line)
        if d["split"] == args.split
    ]
    if not gold:
        raise SystemExit(f"error: no annotated {args.split} documents in {path}")
    loaded = load_bundle(args.bundle)
    preds = []
    for doc in gold:
        entities, relations = loaded.extractor.extract(doc["text"])
        preds.append({"doc_id": doc["doc_id"], "entities": entities, "relations": relations})
    report = evaluate(gold, preds)
    sources = {s["source_id"]: s for s in load_sources(set_dir)}
    slices = category_slices(gold, preds, sources)
    report.update(
        {
            "set": args.set_name,
            "split": args.split,
            "reference": reference_name,
            "model_version": loaded.model_version,
            "locked_test_release": args.locked_test_release,
        }
    )
    if slices:
        report["categories"] = slices
    out = ROOT / "reports" / "annotation_sets"
    out.mkdir(parents=True, exist_ok=True)
    suffix = "" if args.reference == "gold" else f"-vs-{args.reference}"
    name = f"{args.set_name}-{args.split}-{loaded.model_version}{suffix}"
    (out / f"{name}.json").write_text(json.dumps(report, indent=1) + "\n", "utf-8")
    vs = "" if args.reference == "gold" else ", vs. machine labels"
    title = f"{loaded.model_version} on {args.set_name} ({args.split}{vs})"
    seen = {
        d["text"][e["start"] : e["end"]].casefold()
        for d in load_split(ROOT, "train")
        for e in d["entities"]
        if e["label"] == "Reagent"
    }
    names = {
        d["text"][e["start"] : e["end"]].casefold()
        for d in gold
        for e in d["entities"]
        if e["label"] == "Reagent"
    }
    errors = analyze(gold, preds, unseen_names=names - seen)
    errors["source"] = {"set": args.set_name, "split": args.split, "reference": reference_name}
    (out / f"{name}-errors.json").write_text(
        json.dumps(errors, indent=1, ensure_ascii=False) + "\n", "utf-8"
    )
    (out / f"{name}-errors.md").write_text(render_errors(errors, title), "utf-8")
    print(render_markdown(report, title))
    if slices:
        print("| Category | Steps | Entity F1 (support) | Relation F1 (support) |")
        print("|---|---:|---:|---:|")
        for category, row in slices.items():
            e, r = row["entities"], row["relations"]
            print(
                f"| {category} | {row['steps']} | {e['f1']:.3f} ({e['support']}) "
                f"| {r['f1']:.3f} ({r['support']}) |"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
