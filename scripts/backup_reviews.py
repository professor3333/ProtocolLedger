"""Back up or restore the review database.

    uv run python scripts/backup_reviews.py backup  reviews.db backups/reviews-2026-10-10.db
    uv run python scripts/backup_reviews.py restore backups/reviews-2026-10-10.db reviews.db

``backup`` uses SQLite's online backup API, so it is consistent while the service is
running. ``restore`` refuses to overwrite an existing database unless --force is given,
and verifies the copy opens and passes an integrity check first.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from pathlib import Path

from protocolledger.serve.reviews import ReviewStore


def integrity_ok(path: Path) -> bool:
    with sqlite3.connect(path) as db:
        return bool(db.execute("PRAGMA integrity_check").fetchone()[0] == "ok")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("action", choices=["backup", "restore"])
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if not args.source.exists():
        print(f"error: {args.source} does not exist", file=sys.stderr)
        return 1
    if args.destination.exists() and not args.force:
        print(f"error: {args.destination} exists; pass --force to replace it", file=sys.stderr)
        return 1
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    if args.action == "backup":
        ReviewStore(args.source).backup(args.destination)
    else:
        if not integrity_ok(args.source):
            print(f"error: {args.source} failed the integrity check", file=sys.stderr)
            return 1
        shutil.copy2(args.source, args.destination)
    if not integrity_ok(args.destination):
        print(f"error: {args.destination} failed the integrity check", file=sys.stderr)
        return 1
    print(f"{args.action}: {args.source} -> {args.destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
