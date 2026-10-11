"""Export saved reviews as a correction batch awaiting human curation.

    uv run python scripts/export_review_batch.py --db data/reviews.db

Writes data/corrections/batch-<timestamp>/ (never committed) with:
  documents.jsonl  the latest revision of each review saved with its text
  curation.json    one entry per document, all {"include": false}; edit to opt in
  manifest.json    counts, including reviews skipped because their text was not stored
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from protocolledger.data.review_batch import BATCH_VERSION, curation_template, export_reviews

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = args.out or ROOT / "data" / "corrections" / f"batch-{stamp}"
    if out.exists():
        raise SystemExit(f"error: {out} exists")
    docs, counts = export_reviews(args.db)
    out.mkdir(parents=True)
    with (out / "documents.jsonl").open("w", encoding="utf-8") as fh:
        for d in docs:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")
    (out / "curation.json").write_text(json.dumps(curation_template(docs), indent=1) + "\n")
    manifest = {"batch_version": BATCH_VERSION, "exported_at": stamp, **counts}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(
        f"wrote {out}: {counts['exported']} documents, {counts['skipped_no_text']} reviews "
        "skipped (text not stored). Every document starts excluded: edit curation.json, set "
        '"include": true and give a "reason" for each one you accept.'
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
