"""Parse BRAT standoff ``.ann`` files into typed records.

Format reference: https://brat.nlplab.org/standoff.html. Only the record kinds used by
this corpus are accepted (T, E, R and ``#`` AnnotatorNotes); anything else is reported
as a parse problem rather than ignored.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TextBound:
    id: str
    label: str
    start: int
    end: int
    surface: str
    line_no: int


@dataclass(frozen=True)
class Event:
    id: str
    event_type: str
    trigger: str
    args: tuple[tuple[str, str], ...]  # (raw role, target id)
    line_no: int


@dataclass(frozen=True)
class Relation:
    id: str
    label: str
    arg1: str
    arg2: str
    line_no: int


@dataclass(frozen=True)
class Note:
    id: str
    kind: str
    target: str
    text: str
    line_no: int


@dataclass
class ParsedAnn:
    textbounds: list[TextBound] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    notes: list[Note] = field(default_factory=list)
    problems: list[tuple[int, str]] = field(default_factory=list)  # (line_no, message)


def _parse_textbound(rid: str, rest: str, line_no: int, out: ParsedAnn) -> None:
    head, sep, surface = rest.partition("\t")
    if not sep:
        out.problems.append((line_no, f"{rid}: missing surface text field"))
        return
    label, _, offsets = head.partition(" ")
    if ";" in offsets:
        out.problems.append((line_no, f"{rid}: discontinuous span {offsets!r} is not supported"))
        return
    parts = offsets.split(" ")
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        out.problems.append((line_no, f"{rid}: malformed offsets {offsets!r}"))
        return
    out.textbounds.append(TextBound(rid, label, int(parts[0]), int(parts[1]), surface, line_no))


def _parse_event(rid: str, rest: str, line_no: int, out: ParsedAnn) -> None:
    pairs: list[tuple[str, str]] = []
    for token in rest.split():
        role, sep, target = token.partition(":")
        if not sep or not role or not target:
            out.problems.append((line_no, f"{rid}: malformed event argument {token!r}"))
            return
        pairs.append((role, target))
    if not pairs:
        out.problems.append((line_no, f"{rid}: event without a trigger"))
        return
    (event_type, trigger), args = pairs[0], tuple(pairs[1:])
    out.events.append(Event(rid, event_type, trigger, args, line_no))


def _parse_relation(rid: str, rest: str, line_no: int, out: ParsedAnn) -> None:
    tokens = rest.split()
    if len(tokens) != 3:
        out.problems.append((line_no, f"{rid}: expected 'Type Arg1:X Arg2:Y', got {rest!r}"))
        return
    label, a1, a2 = tokens
    if not a1.startswith("Arg1:") or not a2.startswith("Arg2:"):
        out.problems.append((line_no, f"{rid}: malformed relation arguments {rest!r}"))
        return
    out.relations.append(Relation(rid, label, a1[5:], a2[5:], line_no))


def _parse_note(rid: str, rest: str, line_no: int, out: ParsedAnn) -> None:
    head, _, text = rest.partition("\t")
    kind, _, target = head.partition(" ")
    if kind != "AnnotatorNotes" or not target:
        out.problems.append((line_no, f"{rid}: unsupported note {head!r}"))
        return
    out.notes.append(Note(rid, kind, target, text, line_no))


def parse_ann(content: str) -> ParsedAnn:
    out = ParsedAnn()
    for line_no, line in enumerate(content.splitlines(), start=1):
        if not line.strip():
            continue
        rid, sep, rest = line.partition("\t")
        if not sep or len(rid) < 2:
            out.problems.append((line_no, f"malformed record {line!r}"))
            continue
        kind = rid[0]
        if kind == "T":
            _parse_textbound(rid, rest, line_no, out)
        elif kind == "E":
            _parse_event(rid, rest, line_no, out)
        elif kind == "R":
            _parse_relation(rid, rest, line_no, out)
        elif kind == "#":
            _parse_note(rid, rest, line_no, out)
        else:
            out.problems.append((line_no, f"{rid}: unsupported record kind {kind!r}"))
    return out
