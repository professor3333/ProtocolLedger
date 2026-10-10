"""Fetch the pinned WNUT-2020 corpus into data/raw/ and verify every file hash.

uv run python scripts/acquire.py            # download, verify, extract read-only
uv run python scripts/acquire.py --verify   # re-check an existing data/raw/ tree
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from protocolledger.data.acquire import AcquisitionError, Paths, acquire, create_manifest, verify

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--verify", action="store_true", help="only verify data/raw/")
    mode.add_argument(
        "--create-manifest",
        action="store_true",
        help="one-time: record file hashes of the pinned commit (refuses if a manifest exists)",
    )
    args = parser.parse_args(argv)
    paths = Paths.under(ROOT)
    try:
        if args.create_manifest:
            create_manifest(paths)
        elif args.verify:
            problems = verify(paths)
            for problem in problems:
                print(problem, file=sys.stderr)
            if problems:
                return 1
            print(f"{paths.raw} matches {paths.manifest}")
        else:
            acquire(paths)
    except AcquisitionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
