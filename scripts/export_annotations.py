"""Export from-scratch gold annotations for a set (later-domain or challenge).

    uv run python scripts/export_annotations.py --db data/reviews.db --set later-domain

Joins reviews saved in "Annotate from scratch" mode to data/annotation/<set>/sources.jsonl
by text hash and writes data/annotation/<set>/gold.jsonl with source attribution. Reviews
started before the from-scratch defaults were removed are skipped and counted as invalid.
Sources listed in machine_labels_seen.json are flagged in their annotation record.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from protocolledger.data.annotation_sets import (
    gold_from_reviews,
    load_seen_machine_labels,
    load_sources,
)

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--set", required=True, dest="set_name")
    args = parser.parse_args(argv)
    set_dir = ROOT / "data" / "annotation" / args.set_name
    seen = load_seen_machine_labels(set_dir)
    gold, counts = gold_from_reviews(args.db, load_sources(set_dir), args.set_name, seen)
    with (set_dir / "gold.jsonl").open("w", encoding="utf-8") as fh:
        for doc in gold:
            fh.write(json.dumps(doc, ensure_ascii=False) + "\n")
    c = counts
    print(
        f"{args.set_name}: dev {c['dev']}/{c['dev_sources']}, test {c['test']}/{c['test_sources']} "
        f"annotated; {c['invalid_reviews']} invalid reviews skipped (started before the "
        f"from-scratch defaults were removed); {c['machine_labels_seen']} annotated after "
        f"seeing machine labels; {c['ignored_reviews']} other reviews ignored"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
