"""Compare two annotations of the dev portion of a new annotation set.

    # repeat-annotation consistency: the same annotator, a second time, blind
    uv run python scripts/annotation_agreement.py --set later-domain \\
        --first data/annotation.db --second data/annotation-repeat.db
    # how far the machine labels agree with the human gold
    uv run python scripts/annotation_agreement.py --set later-domain \\
        --first data/annotation.db --second machine

Both sides must be from-scratch annotations (or the machine labels); only documents both
sides have are compared, and only on dev. With a single annotator the first comparison is
repeat-annotation consistency, not inter-annotator agreement. Reports list scores and
counts only, with no example spans, so reading one cannot steer later annotation.
Writes reports/annotation_sets/<set>-dev-<kind>.{json,md}.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from protocolledger.data.annotation_sets import (
    agreement_pairs,
    gold_from_reviews,
    load_machine_labels,
    load_seen_machine_labels,
    load_sources,
)
from protocolledger.eval.scorer import evaluate, render_markdown

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--set", required=True, dest="set_name")
    parser.add_argument("--first", type=Path, required=True, help="review database")
    parser.add_argument("--second", required=True, help="review database, or 'machine'")
    args = parser.parse_args(argv)
    set_dir = ROOT / "data" / "annotation" / args.set_name
    sources = load_sources(set_dir)
    seen = load_seen_machine_labels(set_dir)
    first, _ = gold_from_reviews(args.first, sources, args.set_name, seen)
    if args.second == "machine":
        second = load_machine_labels(set_dir)
        kind, label = "human-vs-machine", "human gold vs. machine labels (agreement)"
    else:
        second, _ = gold_from_reviews(Path(args.second), sources, args.set_name, seen)
        kind, label = "repeat-consistency", "repeat-annotation consistency (one annotator)"
    reference, other, counts = agreement_pairs(first, second, "dev")
    if not reference:
        raise SystemExit(f"error: no dev document is annotated on both sides ({counts})")
    report = evaluate(reference, other)
    report.update({"set": args.set_name, "split": "dev", "comparison": label, "counts": counts})
    out = ROOT / "reports" / "annotation_sets"
    out.mkdir(parents=True, exist_ok=True)
    name = f"{args.set_name}-dev-{kind}"
    (out / f"{name}.json").write_text(json.dumps(report, indent=1) + "\n", "utf-8")
    text = render_markdown(report, f"{args.set_name} (dev): {label}")
    (out / f"{name}.md").write_text(text, "utf-8")
    print(text)
    print(
        f"documents compared {counts['compared']}; first only {counts['first_only']}; "
        f"second only {counts['second_only']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
