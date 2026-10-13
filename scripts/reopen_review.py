"""Issue a new access token for a saved review, so it can be reopened in the interface.

    uv run python scripts/reopen_review.py --db data/annotation.db \\
        --text-file data/annotation/later-domain/texts/pio-317105.txt

The interface shows a review's token only once and the server keeps only its hash, so a
lost token cannot be recovered. This script, which needs the database file itself, finds
the most recent review of the given text (from-scratch annotations by default), replaces
its token, and prints the review id and the new token to paste under "Open a saved
review". The old token stops working; saved revisions are unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from protocolledger.serve.reviews import ReviewStore

MANUAL = "manual-annotation"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--text-file", type=Path, required=True)
    parser.add_argument(
        "--any-model", action="store_true", help="also consider model-assisted reviews"
    )
    args = parser.parse_args(argv)
    if not args.db.exists():
        raise SystemExit(f"error: {args.db} does not exist")
    text = args.text_file.read_bytes().decode("utf-8")
    store = ReviewStore(args.db)
    reviews = store.find(
        hashlib.sha256(text.encode("utf-8")).hexdigest(), None if args.any_model else MANUAL
    )
    reviews = [r for r in reviews if r["stored"]]
    if not reviews:
        raise SystemExit(
            "error: no saved review of this text with stored text "
            "(it must be saved with 'Store the protocol text on the server')"
        )
    latest = reviews[-1]
    token = store.reissue_token(latest["id"])
    print(f"review  {latest['id']}  (saved {latest['created_at']}, {latest['model_version']})")
    print(f"token   {token}")
    if len(reviews) > 1:
        print(f"note: {len(reviews) - 1} older review(s) of this text exist; the newest is used.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
