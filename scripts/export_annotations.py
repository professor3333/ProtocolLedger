"""Export from-scratch gold annotations for a set (later-domain or challenge).

    uv run python scripts/export_annotations.py --db data/reviews.db --set later-domain

Joins reviews saved in "Annotate from scratch" mode to data/annotation/<set>/sources.jsonl
by text hash and writes data/annotation/<set>/gold.jsonl with source attribution.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from protocolledger.data.annotation_sets import gold_from_reviews, load_sources

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--set", required=True, dest="set_name")
    args = parser.parse_args(argv)
    set_dir = ROOT / "data" / "annotation" / args.set_name
    gold, counts = gold_from_reviews(args.db, load_sources(set_dir), args.set_name)
    with (set_dir / "gold.jsonl").open("w", encoding="utf-8") as fh:
        for doc in gold:
            fh.write(json.dumps(doc, ensure_ascii=False) + "\n")
    print(f"{args.set_name}: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
