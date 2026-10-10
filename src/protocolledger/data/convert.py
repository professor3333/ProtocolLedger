"""Convert BRAT standoff documents into canonical, validated entity-relation graphs.

Conventions:

* The raw ``.txt`` string is the coordinate system. Offsets are half-open ``[start, end)``
  code-point indices into it, and the text is stored verbatim.
* Event arguments become directed relations from the event's trigger span to the
  argument; ``R`` records become ``Arg1 -> Arg2``. Any endpoint naming an event resolves
  to that event's trigger span.
* Numeric repeated-role suffixes are stripped (``Acts-on2`` -> ``Acts-on``); the raw role
  is kept in the relation's ``origins``.
* Identical ``(head, label, tail)`` triples are merged, keeping every origin, so counts
  are available both before and after deduplication. Distinct labels on the same pair
  are kept (multilabel pairs).

Problems are classified by severity. ``error`` issues make the document unusable and fail
conversion; ``warning`` issues are kept on the document and reported. Nothing is dropped
silently.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from protocolledger.data.brat import ParsedAnn, parse_ann
from protocolledger.data.schema import (
    ENTITY_LABELS,
    EVENT_TYPE,
    RELATION_LABELS,
    normalize_role,
)

CONVERSION_VERSION = "1"

Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class Issue:
    severity: Severity
    code: str
    record: str
    detail: str

    def to_json(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "record": self.record,
            "detail": self.detail,
        }


@dataclass
class Document:
    doc_id: str
    split: str
    source: dict[str, str]
    text: str
    steps: list[tuple[int, int]]
    entities: list[dict[str, Any]]
    relations: list[dict[str, Any]]
    notes: list[dict[str, str]]
    raw_relation_count: int
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "error"]

    def to_json(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "split": self.split,
            "conversion_version": CONVERSION_VERSION,
            "source": self.source,
            "text": self.text,
            "steps": [list(s) for s in self.steps],
            "entities": self.entities,
            "relations": self.relations,
            "raw_relation_count": self.raw_relation_count,
            "notes": self.notes,
            "issues": [i.to_json() for i in self.issues],
        }


def step_spans(text: str) -> list[tuple[int, int]]:
    """``[start, end)`` of every line, excluding the newline. Line 0 is the protocol title;
    each later line is one protocol step."""
    spans: list[tuple[int, int]] = []
    start = 0
    for line in text.split("\n"):
        spans.append((start, start + len(line)))
        start += len(line) + 1
    if text.endswith("\n"):
        spans.pop()  # the empty string after the final newline is not a step
    return spans


def _step_index(steps: list[tuple[int, int]], offset: int) -> int:
    for i, (s, e) in enumerate(steps):
        if s <= offset <= e:
            return i
    return -1


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_document(
    doc_id: str,
    split: str,
    text: str,
    ann: ParsedAnn,
    source: dict[str, str] | None = None,
) -> Document:
    issues: list[Issue] = []

    def issue(severity: Severity, code: str, record: str, detail: str) -> None:
        issues.append(Issue(severity, code, record, detail))

    for line_no, message in ann.problems:
        issue("error", "parse_error", f"line {line_no}", message)

    steps = step_spans(text)

    # Unique ids across all record kinds.
    seen: Counter[str] = Counter(
        [t.id for t in ann.textbounds] + [e.id for e in ann.events] + [r.id for r in ann.relations]
    )
    for rid, uses in sorted(seen.items()):
        if uses > 1:
            issue("error", "duplicate_id", rid, f"id used {uses} times")

    entities: dict[str, dict[str, Any]] = {}
    for tb in ann.textbounds:
        if tb.label not in ENTITY_LABELS:
            issue("error", "unknown_entity_label", tb.id, tb.label)
            continue
        if not 0 <= tb.start < tb.end <= len(text):
            issue("error", "bad_offsets", tb.id, f"[{tb.start}, {tb.end}) in text of {len(text)}")
            continue
        span_text = text[tb.start : tb.end]
        if span_text != tb.surface:
            issue(
                "warning",
                "surface_mismatch",
                tb.id,
                f"stored {tb.surface!r} != offset slice {span_text!r}; offsets are authoritative",
            )
        if span_text != span_text.strip():
            # Raw offsets are kept; whether gold spans are trimmed for evaluation is a
            # correction-ledger decision, not a silent converter fix.
            issue("warning", "span_edge_whitespace", tb.id, repr(span_text))
        if _step_index(steps, tb.start) != _step_index(steps, tb.end):
            issue("warning", "span_crosses_step", tb.id, f"[{tb.start}, {tb.end})")
        entities[tb.id] = {
            "id": tb.id,
            "label": tb.label,
            "start": tb.start,
            "end": tb.end,
            "text": span_text,
        }

    # Events: resolve each event id to its trigger span.
    trigger_of: dict[str, str] = {}
    for ev in ann.events:
        if ev.event_type != EVENT_TYPE:
            issue("error", "unknown_event_type", ev.id, ev.event_type)
            continue
        trig = entities.get(ev.trigger)
        if trig is None:
            issue("error", "dangling_trigger", ev.id, ev.trigger)
            continue
        if trig["label"] != EVENT_TYPE:
            issue("error", "trigger_not_action", ev.id, f"{ev.trigger} is {trig['label']}")
            continue
        trigger_of[ev.id] = ev.trigger

    def resolve(ref: str, record: str) -> str | None:
        target = trigger_of.get(ref, ref) if ref.startswith("E") else ref
        if target not in entities:
            issue("error", "dangling_endpoint", record, ref)
            return None
        return target

    merged: dict[tuple[str, str, str], dict[str, Any]] = {}
    raw_relation_count = 0

    def add(head: str, raw_label: str, tail: str, record: str) -> None:
        nonlocal raw_relation_count
        raw_relation_count += 1
        label = normalize_role(raw_label)
        if label not in RELATION_LABELS:
            issue("error", "unknown_relation_label", record, raw_label)
            return
        h, t = resolve(head, record), resolve(tail, record)
        if h is None or t is None:
            return
        if h == t:
            issue("warning", "self_relation", record, f"{label} {h} -> {t}")
        origin = {"record": record, "raw_label": raw_label}
        key = (h, label, t)
        if key in merged:
            merged[key]["origins"].append(origin)
        else:
            merged[key] = {"head": h, "label": label, "tail": t, "origins": [origin]}

    for ev in ann.events:
        if ev.id not in trigger_of:
            continue
        for role, target in ev.args:
            add(ev.id, role, target, ev.id)
    for rel in ann.relations:
        add(rel.arg1, rel.label, rel.arg2, rel.id)

    events_by_trigger = set(trigger_of.values())
    for ent in entities.values():
        if ent["label"] == EVENT_TYPE and ent["id"] not in events_by_trigger:
            issue("warning", "action_without_event", ent["id"], ent["text"])

    for key, merged_rel in merged.items():
        if len(merged_rel["origins"]) > 1:
            records = ", ".join(o["record"] for o in merged_rel["origins"])
            issue("warning", "duplicate_relation", records, " ".join(key))

    notes = [{"id": note.id, "target": note.target, "text": note.text} for note in ann.notes]
    for note in ann.notes:
        if note.target not in entities and note.target not in trigger_of:
            issue("warning", "note_on_unknown_record", note.id, note.target)

    def entity_key(e: dict[str, Any]) -> tuple[int, int, str, int]:
        return (e["start"], e["end"], e["label"], int(e["id"][1:]))

    def relation_key(
        r: dict[str, Any],
    ) -> tuple[tuple[int, int, str, int], str, tuple[int, int, str, int]]:
        return (entity_key(entities[r["head"]]), r["label"], entity_key(entities[r["tail"]]))

    return Document(
        doc_id=doc_id,
        split=split,
        source=dict(source or {}),
        text=text,
        steps=steps,
        entities=sorted(entities.values(), key=entity_key),
        relations=sorted(merged.values(), key=relation_key),
        notes=notes,
        raw_relation_count=raw_relation_count,
        issues=issues,
    )


def convert_pair(
    txt_path: Path, ann_path: Path, doc_id: str, split: str, rel_root: Path
) -> Document:
    txt_bytes, ann_bytes = txt_path.read_bytes(), ann_path.read_bytes()
    text = txt_bytes.decode("utf-8")  # strict: invalid UTF-8 is an error, not replaced
    ann = parse_ann(ann_bytes.decode("utf-8"))
    source = {
        "txt": txt_path.relative_to(rel_root).as_posix(),
        "ann": ann_path.relative_to(rel_root).as_posix(),
        "txt_sha256": _sha256(txt_bytes),
        "ann_sha256": _sha256(ann_bytes),
    }
    return build_document(doc_id, split, text, ann, source)


# Issue codes listed individually in the report; others are only counted because they
# are frequent and expected (e.g. Action spans annotated without an event record).
_LISTED_ISSUE_LIMIT = 50


def convert_split(raw_root: Path, split_dir: str) -> list[Document]:
    """Convert every ``.txt``/``.ann`` pair in one selected directory, in name order."""
    directory = raw_root / split_dir
    split = Path(split_dir).parts[1]
    txts = sorted(directory.glob("*.txt"))
    anns = sorted(directory.glob("*.ann"))
    if [p.stem for p in txts] != [p.stem for p in anns]:
        missing = {p.stem for p in txts} ^ {p.stem for p in anns}
        raise ValueError(f"{split_dir}: unpaired files {sorted(missing)}")
    return [
        convert_pair(txt, txt.with_suffix(".ann"), f"{split}/{txt.stem}", split, raw_root)
        for txt in txts
    ]


def _summarize(docs: list[Document]) -> dict[str, Any]:
    entity_labels: Counter[str] = Counter()
    relation_labels: Counter[str] = Counter()
    relation_labels_raw: Counter[str] = Counter()
    issue_counts: Counter[str] = Counter()
    pairs: Counter[tuple[str, str, str]] = Counter()
    for doc in docs:
        entity_labels.update(e["label"] for e in doc.entities)
        relation_labels.update(r["label"] for r in doc.relations)
        relation_labels_raw.update(r["label"] for r in doc.relations for _ in r["origins"])
        issue_counts.update(f"{i.severity}:{i.code}" for i in doc.issues)
        pairs.update((doc.doc_id, r["head"], r["tail"]) for r in doc.relations)
    return {
        "documents": len(docs),
        "entities": sum(len(d.entities) for d in docs),
        "relations_raw": sum(d.raw_relation_count for d in docs),
        "relations_merged": sum(len(d.relations) for d in docs),
        "multilabel_pairs": sum(1 for n in pairs.values() if n > 1),
        "entity_labels": dict(sorted(entity_labels.items())),
        "relation_labels_merged": dict(sorted(relation_labels.items())),
        "relation_labels_raw": dict(sorted(relation_labels_raw.items())),
        "issues": dict(sorted(issue_counts.items())),
    }


def build_report(
    docs_by_split: dict[str, list[Document]], outputs: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    all_docs = [d for docs in docs_by_split.values() for d in docs]
    code_counts = Counter(i.code for d in all_docs for i in d.issues)
    listed = [
        {"doc_id": d.doc_id, **i.to_json()}
        for d in all_docs
        for i in d.issues
        if code_counts[i.code] <= _LISTED_ISSUE_LIMIT
    ]
    return {
        "conversion_version": CONVERSION_VERSION,
        "conventions": {
            "offsets": "half-open [start, end) code-point indices into the raw .txt",
            "event_arguments": "trigger span -> argument span, label = role without suffix",
            "relation_records": "Arg1 -> Arg2; event endpoints resolve to trigger spans",
            "relations_raw": "event arguments + R records, before merging duplicates",
            "relations_merged": "unique (head, label, tail) triples",
            "multilabel_pairs": "ordered (head, tail) pairs carrying more than one label",
        },
        "splits": {split: _summarize(docs) for split, docs in docs_by_split.items()},
        "total": _summarize(all_docs),
        "listed_issues": listed,
        "outputs": outputs,
    }
