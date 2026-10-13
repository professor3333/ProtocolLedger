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
