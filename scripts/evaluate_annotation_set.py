"""Score a model bundle on a new annotation set with the shared scorer.

    uv run --extra neural python scripts/evaluate_annotation_set.py --set later-domain \\
        --split dev --bundle artifacts/bundles/<model_version>

The test portion is locked: --split test requires --locked-test-release, and is meant to
be run once per declared release. Writes reports/annotation_sets/<set>-<split>-<model>.json.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from protocolledger.eval.scorer import evaluate, render_markdown
from protocolledger.serve.bundle import load_bundle

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--set", required=True, dest="set_name")
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--locked-test-release", default=None)
    args = parser.parse_args(argv)
    if args.split == "test" and not args.locked_test_release:
        raise SystemExit("error: the test portion is locked; pass --locked-test-release")
    path = ROOT / "data" / "annotation" / args.set_name / "gold.jsonl"
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
    report.update(
        {
            "set": args.set_name,
            "split": args.split,
            "model_version": loaded.model_version,
            "locked_test_release": args.locked_test_release,
        }
    )
    out = ROOT / "reports" / "annotation_sets"
    out.mkdir(parents=True, exist_ok=True)
    name = f"{args.set_name}-{args.split}-{loaded.model_version}"
    (out / f"{name}.json").write_text(json.dumps(report, indent=1) + "\n", "utf-8")
    print(render_markdown(report, f"{loaded.model_version} on {args.set_name} ({args.split})"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
