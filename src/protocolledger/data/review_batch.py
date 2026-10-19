"""Curated correction batches: from saved reviews to candidate training documents.

Reviewer edits never become training labels on their own. A batch is exported from the
review store, every review starts **excluded**, and a person must include each one with
a reason. Included reviews whose text duplicates a dev or test protocol are refused, so
curated data cannot leak into evaluation.

Only reviews saved with their text can be exported; the rest are counted and skipped.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from protocolledger.data.dedup import similar_pairs

BATCH_VERSION = "1"


class BatchError(RuntimeError):
    """The batch or its curation is not acceptable for training."""


def export_reviews(db_path: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Latest revision of every review as a canonical training document."""
    uri = f"file:{db_path}?mode=ro"
    with sqlite3.connect(uri, uri=True) as db:
        db.row_factory = sqlite3.Row
        reviews = db.execute(
            "SELECT id, created_at, text, text_sha256, model_version FROM reviews "
            "ORDER BY created_at, id"
        ).fetchall()
        docs: list[dict[str, Any]] = []
        skipped = 0
        for review in reviews:
            if review["text"] is None:
                skipped += 1
                continue
            latest = db.execute(
                "SELECT number, payload FROM revisions WHERE review_id = ? "
                "ORDER BY number DESC LIMIT 1",
                (review["id"],),
            ).fetchone()
            content = json.loads(latest["payload"])
            docs.append(to_document(review, latest["number"], content))
    return docs, {"reviews": len(reviews), "exported": len(docs), "skipped_no_text": skipped}


def to_document(
    review: Mapping[str, Any], revision: int, content: Mapping[str, Any]
) -> dict[str, Any]:
    text: str = review["text"]
    kept = [e for e in content["entities"] if e["decision"] != "rejected"]
    ids = {e["id"] for e in kept}
    entities = [
        {
            "id": e["id"],
            "label": e["label"],
            "start": e["start"],
            "end": e["end"],
            "text": text[e["start"] : e["end"]],
        }
        for e in kept
    ]
    relations = [
        {"head": r["head"], "label": r["label"], "tail": r["tail"]}
        for r in content["relations"]
        if r["decision"] != "rejected" and r["head"] in ids and r["tail"] in ids
    ]
    human = sum(e["origin"] == "human" or e["decision"] == "edited" for e in content["entities"])
    human += sum(r["origin"] == "human" for r in content["relations"])
    human += sum(x["decision"] == "rejected" for x in [*content["entities"], *content["relations"]])
    return {
        "doc_id": f"review/{review['id']}/r{revision}",
        "text": text,
        "entities": entities,
        "relations": relations,
        "provenance": {
            "review_id": review["id"],
            "created_at": review["created_at"],
            "revision": revision,
            "model_version": review["model_version"],
            "text_sha256": review["text_sha256"],
            "reviewer_changes": human,
        },
    }


def curation_template(docs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Every review starts excluded; a person must opt each one in with a reason."""
    return [
        {
            "doc_id": d["doc_id"],
            "include": False,
            "reason": "",
            "reviewer_changes": d["provenance"]["reviewer_changes"],
        }
        for d in docs
    ]


def apply_curation(
    docs: Sequence[Mapping[str, Any]], curation: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    by_id = {d["doc_id"]: d for d in docs}
    unknown = [c["doc_id"] for c in curation if c["doc_id"] not in by_id]
    if unknown:
        raise BatchError(f"curation lists unknown documents: {unknown[:3]}")
    included = [c for c in curation if c.get("include") is True]
    missing_reason = [c["doc_id"] for c in included if not str(c.get("reason", "")).strip()]
    if missing_reason:
        raise BatchError(f"included documents need a curation reason: {missing_reason[:3]}")
    if not included:
        raise BatchError("no document is included; nothing to train on")
    return [dict(by_id[c["doc_id"]]) for c in included]


def leakage(
    candidates: Sequence[Mapping[str, Any]], protected: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Candidate documents that are the same protocol as a protected (dev/test) one."""
    texts = {f"candidate::{d['doc_id']}": d["text"] for d in candidates}
    texts.update({f"protected::{d['doc_id']}": d["text"] for d in protected})
    found = []
    for pair in similar_pairs(texts):
        names = sorted((pair.a, pair.b))
        if (
            pair.same_protocol
            and names[0].startswith("candidate::")
            and names[1].startswith("protected::")
        ):
            found.append(
                {
                    "candidate": names[0].split("::", 1)[1],
                    "protected": names[1].split("::", 1)[1],
                    "jaccard": pair.jaccard,
                }
            )
    return found


def batch_sha256(docs: Sequence[Mapping[str, Any]]) -> str:
    body = json.dumps(
        [{k: d[k] for k in ("doc_id", "text", "entities", "relations")} for d in docs],
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()
