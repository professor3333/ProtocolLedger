"""Load the frozen cleaned splits, verifying them against data/manifests/splits.json."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SPLIT_NAMES: tuple[str, ...] = ("train", "dev", "test")


class SplitError(RuntimeError):
    """A cleaned split file is missing or does not match the frozen manifest."""


def load_split(root: Path, split: str) -> list[dict[str, Any]]:
    if split not in SPLIT_NAMES:
        raise SplitError(f"unknown split {split!r}")
    manifest = json.loads((root / "data" / "manifests" / "splits.json").read_text("utf-8"))
    entry = manifest["splits"][split]
    path = root / entry["path"]
    if not path.exists():
        raise SplitError(f"{entry['path']} missing; run scripts/build_splits.py")
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != entry["sha256"]:
        raise SplitError(f"{entry['path']} does not match splits.json; rebuild it")
    docs = [json.loads(line) for line in payload.decode("utf-8").splitlines()]
    if [d["doc_id"] for d in docs] != entry["doc_ids"]:
        raise SplitError(f"{entry['path']} document order differs from splits.json")
    return docs
