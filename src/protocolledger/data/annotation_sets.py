"""New annotation sets: the later-domain protocols.io set and the challenge set.

A set lives in ``data/annotation/<set>/``:

* ``sources.jsonl``: one record per source protocol: ``source_id``, ``url``, ``title``,
  ``authors``, ``version``, ``published``, ``license``, ``text``, ``text_sha256`` and
  ``split`` (``dev`` or ``test``). Written by the collector.
* ``texts/<source_id>.txt``: the text to paste into the review page in
  "Annotate from scratch" mode.
* ``gold.jsonl``: exported gold annotations, joined back to their source by text hash.

Splits are assigned per whole protocol from a hash of its ``source_id``, so revisions
of one protocol share a split and the assignment never depends on annotation order. The
test portion is locked like the corpus test split.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from protocolledger.data.convert import step_spans
from protocolledger.data.review_batch import export_reviews

MANUAL = "manual-annotation"


class AnnotationSetError(RuntimeError):
    """A set's sources or annotations are inconsistent."""


def assign_split(source_id: str, test_fraction: float = 0.5) -> str:
    bucket = int(hashlib.sha256(source_id.encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF
    return "test" if bucket < test_fraction else "dev"


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_sources(set_dir: Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in (set_dir / "sources.jsonl").read_text("utf-8").splitlines()
        if line.strip()
    ]
    for row in rows:
        if text_sha256(row["text"]) != row["text_sha256"]:
            raise AnnotationSetError(f"{row['source_id']}: text does not match its hash")
        if row["split"] not in ("dev", "test"):
            raise AnnotationSetError(f"{row['source_id']}: unknown split {row['split']!r}")
    return rows


def gold_from_reviews(
    db_path: Path, sources: Sequence[Mapping[str, Any]], set_name: str
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Manual (from-scratch) annotations joined to their sources by text hash. If one
    source was annotated more than once, the most recent review wins."""
    by_hash = {s["text_sha256"]: s for s in sources}
    docs, _ = export_reviews(db_path)
    gold: dict[str, dict[str, Any]] = {}
    ignored = 0
    for doc in docs:
        source = by_hash.get(doc["provenance"]["text_sha256"])
        if source is None or doc["provenance"]["model_version"] != MANUAL:
            ignored += 1
            continue
        gold[source["source_id"]] = {
            "doc_id": f"{set_name}/{source['source_id']}",
            "split": source["split"],
            "text": doc["text"],
            "steps": [list(span) for span in step_spans(doc["text"])],
            "entities": doc["entities"],
            "relations": doc["relations"],
            "source": {
                k: source[k]
                for k in ("source_id", "url", "title", "authors", "version", "published", "license")
            },
            "annotation": {
                "review_id": doc["provenance"]["review_id"],
                "revision": doc["provenance"]["revision"],
            },
        }
    ordered = [gold[s["source_id"]] for s in sources if s["source_id"] in gold]
    counts = {
        "sources": len(sources),
        "annotated": len(ordered),
        "ignored_reviews": ignored,
        "dev": sum(d["split"] == "dev" for d in ordered),
        "test": sum(d["split"] == "test" for d in ordered),
    }
    return ordered, counts
