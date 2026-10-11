"""Score a model bundle on clean vs meaning-preservingly perturbed text.

    uv run --extra neural python scripts/robustness.py --bundle artifacts/bundles/<v> --split dev

Perturbations keep every character position (see protocolledger.eval.robustness), so
gold annotations apply unchanged. --split test requires --locked-test-release.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from protocolledger.data.splits import load_split
from protocolledger.eval.robustness import perturb
from protocolledger.eval.scorer import evaluate
from protocolledger.serve.bundle import load_bundle

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument("--rate", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--locked-test-release", default=None)
    args = parser.parse_args(argv)
    if args.split == "test" and not args.locked_test_release:
        raise SystemExit("error: test is locked; pass --locked-test-release")
    docs = load_split(ROOT, args.split)
    loaded = load_bundle(args.bundle)
    rng = random.Random(args.seed)
    results = {}
    for variant in ("clean", "perturbed"):
        preds = []
        for doc in docs:
            text = doc["text"] if variant == "clean" else perturb(doc["text"], rng, args.rate)
            entities, relations = loaded.extractor.extract(text)
            preds.append({"doc_id": doc["doc_id"], "entities": entities, "relations": relations})
        report = evaluate(docs, preds, resamples=1)
        results[variant] = {
            "entity_f1": report["entities"]["micro"]["f1"],
            "relation_f1": report["relations"]["micro"]["f1"],
        }
    drop = round((results["clean"]["relation_f1"] - results["perturbed"]["relation_f1"]) * 100, 2)
    summary = {
        "model_version": loaded.model_version,
        "split": args.split,
        "rate": args.rate,
        "seed": args.seed,
        **results,
        "relation_f1_drop_points": drop,
        "target_max_drop_points": 5.0,
        "locked_test_release": args.locked_test_release,
    }
    out = ROOT / "reports" / "robustness"
    out.mkdir(parents=True, exist_ok=True)
    name = f"{loaded.model_version}-{args.split}"
    (out / f"{name}.json").write_text(json.dumps(summary, indent=1) + "\n", "utf-8")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
