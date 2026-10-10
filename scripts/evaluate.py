"""Score a prediction file against a cleaned split with the shared scorer.

    uv run python scripts/evaluate.py --split dev --pred preds.jsonl --out report.json

The locked test split is refused unless --locked-test-release names the declared
release being evaluated; never use it for development decisions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from protocolledger.data.splits import load_split
from protocolledger.eval.scorer import PredictionError, evaluate, render_markdown

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--split", choices=["train", "dev", "test"], required=True)
    parser.add_argument("--pred", type=Path, required=True, help="prediction JSONL")
    parser.add_argument("--out", type=Path, help="write the JSON report here")
    parser.add_argument("--title", default=None)
    parser.add_argument("--locked-test-release", default=None)
    args = parser.parse_args(argv)

    if args.split == "test" and not args.locked_test_release:
        print("error: test is locked; pass --locked-test-release <release>", file=sys.stderr)
        return 2
    gold = load_split(ROOT, args.split)
    preds = [json.loads(line) for line in args.pred.read_text("utf-8").splitlines() if line]
    try:
        report = evaluate(gold, preds)
    except PredictionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    report["split"] = args.split
    if args.locked_test_release:
        report["locked_test_release"] = args.locked_test_release
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(render_markdown(report, args.title or f"{args.pred.name} on {args.split}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
