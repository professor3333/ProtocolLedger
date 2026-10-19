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
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from protocolledger.data.convert import step_spans
from protocolledger.data.review_batch import export_reviews
from protocolledger.data.schema import ENTITY_LABELS, RELATION_LABELS

MANUAL = "manual-annotation"
# Before this commit (21446d6) "Annotate from scratch" preselected a type, label and
# direction, so nearly every relation saved earlier is a default, not a judgement.
MANUAL_VALID_FROM = "2026-10-13T05:08:52+00:00"


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


def load_seen_machine_labels(set_dir: Path) -> set[str]:
    """Source ids whose machine labels the annotator saw before annotating them."""
    path = set_dir / "machine_labels_seen.json"
    if not path.exists():
        return set()
    return set(json.loads(path.read_text("utf-8"))["source_ids"])


def gold_from_reviews(
    db_path: Path,
    sources: Sequence[Mapping[str, Any]],
    set_name: str,
    seen_machine_labels: set[str] | frozenset[str] = frozenset(),
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Manual (from-scratch) annotations joined to their sources by text hash. If one
    source was annotated more than once, the most recent valid review wins. Reviews
    started before ``MANUAL_VALID_FROM`` are never gold, even if continued later."""
    by_hash = {s["text_sha256"]: s for s in sources}
    docs, _ = export_reviews(db_path)
    gold: dict[str, dict[str, Any]] = {}
    ignored = invalid = 0
    for doc in docs:
        source = by_hash.get(doc["provenance"]["text_sha256"])
        if source is None or doc["provenance"]["model_version"] != MANUAL:
            ignored += 1
            continue
        if doc["provenance"]["created_at"] < MANUAL_VALID_FROM:
            invalid += 1
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
                "machine_labels_seen": source["source_id"] in seen_machine_labels,
            },
        }
    ordered = [gold[s["source_id"]] for s in sources if s["source_id"] in gold]
    counts = {
        "sources": len(sources),
        "annotated": len(ordered),
        "ignored_reviews": ignored,
        "invalid_reviews": invalid,
        "dev": sum(d["split"] == "dev" for d in ordered),
        "test": sum(d["split"] == "test" for d in ordered),
        "dev_sources": sum(s["split"] == "dev" for s in sources),
        "test_sources": sum(s["split"] == "test" for s in sources),
        "machine_labels_seen": sum(d["annotation"]["machine_labels_seen"] for d in ordered),
    }
    return ordered, counts


MACHINE = "machine-generated, not human-reviewed"
_OCCURRENCE = re.compile(r"@(\d+)$")


def _is_word(ch: str) -> bool:
    return ch.isalnum()


def parse_label_spec(text: str, spec: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Turn a label spec into entities and relations with exact offsets into ``text``.

    The spec is line oriented. ``L<n>`` moves to line ``n`` of the text (0 is the title).
    ``<key> <Entity-label> <surface>`` adds an entity: the first occurrence of ``surface``
    on the current line, at word boundaries, that no earlier entity already occupies;
    ``<surface>@<n>`` takes the n-th occurrence on the line instead, and ``~<surface>``
    skips the word-boundary check for words glued together in the source (``anddry``).
    ``<key> <Relation-label> <key>`` adds a directed relation, head first. Blank lines and
    lines starting with ``#`` are ignored. Anything unresolvable raises, so a spec either
    describes the text exactly or is rejected.
    """
    lines = step_spans(text)
    entities: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    keys: dict[str, str] = {}
    taken: set[tuple[int, int]] = set()
    line: tuple[int, int] | None = None
    for number, raw in enumerate(spec.splitlines(), 1):
        row = raw.strip()
        if not row or row.startswith("#"):
            continue
        where = f"spec line {number} ({row!r})"
        if row[0] == "L" and row[1:].isdigit():
            index = int(row[1:])
            if index >= len(lines):
                raise AnnotationSetError(f"{where}: the text has {len(lines)} lines")
            line = lines[index]
            continue
        parts = row.split(maxsplit=2)
        if len(parts) < 3:
            raise AnnotationSetError(f"{where}: expected three fields")
        key, label, rest = parts
        if label in RELATION_LABELS and " " not in rest:
            if key not in keys or rest not in keys:
                raise AnnotationSetError(f"{where}: unknown entity key")
            relations.append({"head": keys[key], "label": label, "tail": keys[rest]})
            continue
        if label not in ENTITY_LABELS:
            raise AnnotationSetError(f"{where}: unknown label {label!r}")
        if line is None:
            raise AnnotationSetError(f"{where}: no L<n> line before the first entity")
        if key in keys:
            raise AnnotationSetError(f"{where}: duplicate key {key!r}")
        start, end = line
        segment = text[start:end]
        nth = None
        occurrence = _OCCURRENCE.search(rest)
        if occurrence:
            nth, rest = int(occurrence.group(1)), rest[: occurrence.start()]
        glued = rest.startswith("~") and len(rest) > 1  # a lone "~" is the literal symbol
        if glued:
            rest = rest[1:]

        def overlaps(a: int, b: int) -> bool:
            return any(a < y and x < b for x, y in taken)

        found = None
        seen_matches = 0
        i = segment.find(rest)
        while i >= 0:
            a, b = start + i, start + i + len(rest)
            left_ok = glued or not (_is_word(rest[0]) and a > 0 and _is_word(text[a - 1]))
            right_ok = glued or not (_is_word(rest[-1]) and b < len(text) and _is_word(text[b]))
            if left_ok and right_ok:
                seen_matches += 1
                if (nth is None and not overlaps(a, b)) or seen_matches == nth:
                    found = (a, b)
                    break
            i = segment.find(rest, i + 1)
        if found is not None and found in taken:
            raise AnnotationSetError(f"{where}: {rest!r} occurrence already labelled")
        if found is None:
            raise AnnotationSetError(f"{where}: {rest!r} not found (free) on this line")
        taken.add(found)
        eid = f"T{len(entities) + 1}"
        keys[key] = eid
        entities.append(
            {"id": eid, "label": label, "start": found[0], "end": found[1], "text": rest}
        )
    seen: set[tuple[str, str, str]] = set()
    for r in relations:
        triple = (r["head"], r["label"], r["tail"])
        if triple in seen:
            raise AnnotationSetError(f"duplicate relation {triple}")
        if r["head"] == r["tail"]:
            raise AnnotationSetError(f"self relation {triple}")
        seen.add(triple)
    return entities, relations


def machine_document(source: Mapping[str, Any], set_name: str, spec: str) -> dict[str, Any]:
    entities, relations = parse_label_spec(source["text"], spec)
    return {
        "doc_id": f"{set_name}/{source['source_id']}",
        "split": source["split"],
        "text": source["text"],
        "steps": [list(span) for span in step_spans(source["text"])],
        "entities": entities,
        "relations": relations,
        "source": {
            k: source[k]
            for k in ("source_id", "url", "title", "authors", "version", "published", "license")
        },
        "annotation": {"labeller": MACHINE, "spec_sha256": text_sha256(spec)},
    }


def load_machine_labels(set_dir: Path) -> list[dict[str, Any]]:
    path = set_dir / "machine_labels.jsonl"
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line]


def manual_reviews_by_hash(db_path: Path) -> dict[str, dict[str, Any]]:
    """From-scratch reviews keyed by text hash; the most recent review of a text wins."""
    docs, _ = export_reviews(db_path)
    return {
        d["provenance"]["text_sha256"]: d
        for d in docs
        if d["provenance"]["model_version"] == MANUAL
    }


def select_warmup(
    train_docs: Sequence[Mapping[str, Any]],
    n: int = 2,
    steps: tuple[int, int] = (6, 10),
    words: tuple[int, int] = (150, 350),
) -> list[Mapping[str, Any]]:
    """Pick ``n`` train protocols about the size of a new-set protocol, by hash of doc id.

    Train documents may be read freely, so annotating them and comparing with the corpus
    gold shows where an annotator's habits differ from the corpus before any new gold
    counts."""
    fits = [
        d
        for d in train_docs
        if steps[0] <= len(d["steps"]) <= steps[1]
        and words[0] <= len(d["text"].split()) <= words[1]
    ]
    fits.sort(key=lambda d: hashlib.sha256(d["doc_id"].encode("utf-8")).hexdigest())
    return fits[:n]


def warmup_pairs(
    db_path: Path, warmup_docs: Sequence[Mapping[str, Any]]
) -> tuple[list[Mapping[str, Any]], list[dict[str, Any]]]:
    """The corpus gold and the annotator's from-scratch review for each annotated warm-up
    document, matched by text hash."""
    reviews = manual_reviews_by_hash(db_path)
    gold, mine = [], []
    for doc in warmup_docs:
        review = reviews.get(text_sha256(doc["text"]))
        if review is None:
            continue
        gold.append(doc)
        mine.append(
            {
                "doc_id": doc["doc_id"],
                "entities": review["entities"],
                "relations": review["relations"],
            }
        )
    return gold, mine


def agreement_pairs(
    first: Sequence[Mapping[str, Any]], second: Sequence[Mapping[str, Any]], split: str = "dev"
) -> tuple[list[Mapping[str, Any]], list[dict[str, Any]], dict[str, int]]:
    """Two annotations of the same documents, restricted to ``split`` and to documents both
    sides have. ``first`` is the reference; F1 is symmetric, so the choice only swaps
    precision and recall."""
    second_by_id = {d["doc_id"]: d for d in second}
    reference = [d for d in first if d["split"] == split and d["doc_id"] in second_by_id]
    for d in reference:
        if second_by_id[d["doc_id"]]["text"] != d["text"]:
            raise AnnotationSetError(f"{d['doc_id']}: the two annotations cover different text")
    other = [
        {
            "doc_id": d["doc_id"],
            "entities": second_by_id[d["doc_id"]]["entities"],
            "relations": second_by_id[d["doc_id"]]["relations"],
        }
        for d in reference
    ]
    counts = {
        "compared": len(reference),
        "first_only": sum(d["split"] == split for d in first) - len(reference),
        "second_only": sum(d["split"] == split for d in second) - len(reference),
    }
    return reference, other, counts
