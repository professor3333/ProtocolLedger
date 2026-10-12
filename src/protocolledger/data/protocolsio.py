"""Turn protocols.io API records into annotation-set sources (later-domain and challenge).

Everything here is pure and deterministic; the network and the cache live in
``scripts/collect_protocolsio.py``. Step text comes from the API's ``html`` rendering,
because it is the only format that renders the site's embedded components (amounts,
durations, temperatures, centrifuge settings) as the text a reader sees.

Cleaning rules (version ``COLLECTION_VERSION``):

* every protocol step becomes exactly one line: its paragraphs, list items and line
  breaks are joined with single spaces (authors often paste text with hard line breaks
  mid-sentence), and runs of ASCII whitespace collapse to one space, while Unicode spaces
  (NBSP, thin space) are kept because they are part of what the model has to handle;
* notes, tables, figures, images and embedded media are dropped and counted, because
  flattened tables glue unrelated cells together and notes are commentary, not
  instructions;
* superscript and subscript digits become Unicode super/subscripts (``10<sup>12</sup>``
  becomes ``10¹²``, not the misleading ``1012``); anything else inside them stays plain;
* a step is usable when it keeps 3 to 120 words, its section is not an introduction,
  safety, results or data-analysis section, and it contains at least one word that is an
  Action in the cleaned train split (prose descriptions usually contain none).

The raw API responses are kept unchanged in the cache; this module never edits them.
"""

from __future__ import annotations

import datetime as dt
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any

from protocolledger.data.dedup import (
    Pair,
    jaccard,
    shingles,
    title_key,
    whitespace_normalized_sha256,
)

COLLECTION_VERSION = "1"
LICENSE = "CC BY (protocols.io Terms of Service, section 1(B))"

MIN_STEP_WORDS = 3
MAX_STEP_WORDS = 120
MIN_USABLE_STEPS = 5
MIN_QUANTITY_SHARE = 0.3

_BLOCK_TAGS = frozenset(
    {"p", "div", "li", "ul", "ol", "br", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre"}
)
_DROP_TAGS = frozenset({"table", "figure", "img", "video", "iframe", "audio", "svg", "script"})
_DROP_CLASSES = ("component-note", "component-table", "component-image", "component-emoji")
_VOID_TAGS = frozenset({"br", "img", "hr", "input", "meta", "link", "source", "wbr"})
_SUPERSCRIPT = str.maketrans("0123456789+-\u2212=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁻⁼⁽⁾ⁿ")  # \u2212 minus sign
_SUBSCRIPT = str.maketrans("0123456789+-=()", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎")
_ASCII_SPACE = re.compile(r"[ \t\r\n\f\v]+")
_WORD = re.compile(r"\w+")

_SKIP_SECTION = re.compile(
    r"\b(introduction|background|objectives?|aims?|abstract|overview|summary|references?|"
    r"safety|disclaimer|results?|discussion|troubleshooting|acknowledg\w*|data analysis|"
    r"statistic\w*|software|bioinformatic\w*|computational)\b",
    re.IGNORECASE,
)
_UNITS = (
    r"(?:[µμu]l|ml|l|[µμu]g|mg|ng|pg|g|kg|[µμunmp]m|m|mol|kda|%|"
    r"°\s?c|º\s?c|°|k|rpm|x\s?g|\u00d7\s?g|g-force|s|sec|secs|seconds?|min|mins|minutes?|"
    r"h|hr|hrs|hours?|days?|v|ma|mv|w|u|iu|units?|cells?|ph)"
)
QUANTITY = re.compile(rf"\d(?:[\d.,]*)\s?{_UNITS}\b|\b\d{{2}}:\d{{2}}:\d{{2}}\b", re.IGNORECASE)
_ENGLISH_WORDS = frozenset(
    {"the", "and", "of", "to", "in", "with", "for", "a", "an", "at", "is", "are", "on", "by"}
    | {"from", "into", "each", "until", "then", "add", "remove", "place", "use"}
)

# Challenge categories (CLAUDE.md "challenge set"); each is a deterministic text test.
_RANGE = re.compile(
    r"\d\s*(?:-|\u2013|\u2014|~|to)\s*\d|\bbetween\s+\d[\d.,]*\s*\S*\s+and\s+\d|±", re.IGNORECASE
)
_IMPLICIT = re.compile(
    r"\b(?:it|its|them|they|their|the (?:mixture|supernatant|pellet|lysate|contents|"
    r"remaining|rest|same|above|former|latter))\b",
    re.IGNORECASE,
)
_CONDITIONAL = re.compile(
    r"\b(?:if|unless|when|whenever|until|otherwise|optional|optionally|as needed|"
    r"depending on|in case)\b",
    re.IGNORECASE,
)
# curly quotes, en and em dashes, ellipsis: ordinary typography, not unusual symbols
_PLAIN_NON_ASCII = frozenset("\u2018\u2019\u201c\u201d\u2013\u2014\u2026")
CATEGORIES: tuple[str, ...] = (
    "multiple_actions",
    "repeated_materials",
    "ranges",
    "unusual_symbols",
    "implicit_references",
    "conditional_wording",
)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lines: list[str] = []
        self.current: list[str] = []
        self.dropped: Counter[str] = Counter()
        self.components: Counter[str] = Counter()
        self._skip_depth = 0
        self._stack: list[tuple[str, bool]] = []
        self._script: list[str] = []  # "sup" / "sub" nesting

    def _break(self) -> None:
        line = _ASCII_SPACE.sub(" ", "".join(self.current)).strip(" ")
        if line:
            self.lines.append(line)
        self.current = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = dict(attrs).get("class") or ""
        for name in classes.split():
            if name.startswith("component-"):
                self.components[name] += 1
        drop = tag in _DROP_TAGS or any(c in classes.split() for c in _DROP_CLASSES)
        if self._skip_depth:
            if tag not in _VOID_TAGS:
                self._stack.append((tag, False))
                self._skip_depth += 1
            return
        if drop:
            self.dropped[next((c for c in _DROP_CLASSES if c in classes.split()), tag)] += 1
            if tag not in _VOID_TAGS:
                self._stack.append((tag, True))
                self._skip_depth = 1
            return
        if tag in _BLOCK_TAGS:
            self._break()
        if tag in ("sup", "sub"):
            self._script.append(tag)
        if tag not in _VOID_TAGS:
            self._stack.append((tag, False))

    def handle_endtag(self, tag: str) -> None:
        if tag in _VOID_TAGS:
            return
        # pop to the matching open tag; tolerate the unbalanced markup editors produce
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                popped = self._stack[i:]
                del self._stack[i:]
                break
        else:
            return
        if self._skip_depth:
            self._skip_depth = max(0, self._skip_depth - len(popped))
            if not self._skip_depth:
                self._break()
            return
        for name, _ in popped:
            if name in ("sup", "sub") and self._script:
                self._script.pop()
        if tag in _BLOCK_TAGS:
            self._break()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._script:
            table = _SUPERSCRIPT if self._script[-1] == "sup" else _SUBSCRIPT
            mapped = data.translate(table)
            if all(not ch.isascii() or ch.isspace() for ch in mapped):
                data = mapped
        self.current.append(data)

    def close(self) -> None:
        super().close()
        self._break()


@dataclass(frozen=True)
class CleanStep:
    step_id: int
    number: str
    section: str
    lines: tuple[str, ...]
    dropped: Mapping[str, int] = field(default_factory=dict)

    @property
    def text(self) -> str:
        return " ".join(self.lines)

    @property
    def words(self) -> int:
        return len(_WORD.findall(self.text))


def html_to_lines(html: str) -> tuple[list[str], Counter[str], Counter[str]]:
    """Visible text lines of one step, plus counts of dropped and seen components."""
    parser = _TextExtractor()
    parser.feed(html or "")
    parser.close()
    return parser.lines, parser.dropped, parser.components


def section_title(html: str | None) -> str:
    lines, _, _ = html_to_lines(html or "")
    return " ".join(lines)


def clean_steps(steps: Sequence[Mapping[str, Any]]) -> tuple[list[CleanStep], Counter[str]]:
    out: list[CleanStep] = []
    components: Counter[str] = Counter()
    for raw in steps:
        lines, dropped, seen = html_to_lines(str(raw.get("step") or ""))
        components.update(seen)
        out.append(
            CleanStep(
                step_id=int(raw["id"]),
                number=str(raw.get("number") or ""),
                section=section_title(raw.get("section")),
                lines=tuple(lines),
                dropped=dict(dropped),
            )
        )
    return out, components


def usable(step: CleanStep, actions: frozenset[str]) -> str | None:
    """``None`` when the step can be annotated, else the reason it is skipped."""
    if not step.lines:
        return "empty"
    if _SKIP_SECTION.search(step.section):
        return "section"
    if step.words < MIN_STEP_WORDS:
        return "too-short"
    if step.words > MAX_STEP_WORDS:
        return "too-long"
    if not any(w.lower() in actions for w in _WORD.findall(step.text)):
        return "no-action-word"
    return None


def looks_english(texts: Iterable[str]) -> bool:
    words = [w.lower() for t in texts for w in _WORD.findall(t)]
    letters = [c for t in texts for c in t if c.isalpha()]
    if not words or not letters:
        return False
    ascii_share = sum(c.isascii() for c in letters) / len(letters)
    function_share = sum(w in _ENGLISH_WORDS for w in words) / len(words)
    return ascii_share >= 0.9 and function_share >= 0.08


def quantity_share(steps: Sequence[CleanStep]) -> float:
    return sum(bool(QUANTITY.search(s.text)) for s in steps) / len(steps) if steps else 0.0


def published_date(record: Mapping[str, Any]) -> str:
    return dt.datetime.fromtimestamp(int(record["published_on"]), dt.UTC).date().isoformat()


def authors(record: Mapping[str, Any]) -> list[str]:
    names = []
    for a in record.get("authors") or []:
        name = (a.get("name") or f"{a.get('first_name', '')} {a.get('last_name', '')}").strip()
        if name:
            names.append(name)
    return names


def build_text(title: str, steps: Sequence[CleanStep]) -> tuple[str, list[dict[str, Any]]]:
    """Line 0 is the title and line i is the i-th step, as in the corpus conversion.
    Returns the text and each step's line number."""
    lines = [_ASCII_SPACE.sub(" ", title).strip()]
    index = []
    for step in steps:
        index.append(
            {
                "step_id": step.step_id,
                "number": step.number,
                "section": step.section,
                "line": len(lines),
            }
        )
        lines.append(step.text)
    return "\n".join(lines) + "\n", index


@dataclass(frozen=True)
class Lexicons:
    """Train-only vocabularies used to tag challenge categories."""

    actions: frozenset[str]
    reagents: re.Pattern[str] | None

    @classmethod
    def from_train(cls, docs: Sequence[Mapping[str, Any]], min_count: int = 3) -> Lexicons:
        actions: Counter[str] = Counter()
        reagents: Counter[str] = Counter()
        for doc in docs:
            for e in doc["entities"]:
                surface = doc["text"][e["start"] : e["end"]].lower()
                if e["label"] == "Action" and _WORD.fullmatch(surface):
                    actions[surface] += 1
                elif e["label"] == "Reagent" and len(surface) >= 3:
                    reagents[surface] += 1
        terms = sorted((t for t, c in reagents.items() if c >= min_count), key=lambda t: -len(t))
        pattern = (
            re.compile(r"(?<!\w)(?:" + "|".join(map(re.escape, terms)) + r")(?!\w)", re.I)
            if terms
            else None
        )
        return cls(frozenset(a for a, c in actions.items() if c >= min_count), pattern)


def challenge_tags(text: str, lexicons: Lexicons) -> list[str]:
    tags = []
    words = [w.lower() for w in _WORD.findall(text)]
    if sum(w in lexicons.actions for w in words) >= 3:
        tags.append("multiple_actions")
    if lexicons.reagents is not None:
        found = Counter(m.group(0).lower() for m in lexicons.reagents.finditer(text))
        if any(c >= 2 for c in found.values()):
            tags.append("repeated_materials")
    if _RANGE.search(text):
        tags.append("ranges")
    if any(not c.isascii() and c not in _PLAIN_NON_ASCII for c in text):
        tags.append("unusual_symbols")
    if _IMPLICIT.search(text):
        tags.append("implicit_references")
    if _CONDITIONAL.search(text):
        tags.append("conditional_wording")
    return tags


def select_challenge(
    candidates: Sequence[tuple[str, CleanStep, Sequence[str]]],
    per_category: int,
    per_protocol: int,
) -> list[tuple[str, CleanStep, list[str]]]:
    """Round-robin over categories, taking the next unused step (in candidate order) that
    carries the category, until every category has ``per_category`` steps or runs out.
    A step counts toward every category it carries."""
    chosen: list[tuple[str, CleanStep, list[str]]] = []
    used: set[int] = set()
    per_source: Counter[str] = Counter()
    counts: Counter[str] = Counter()
    progress = True
    while progress:
        progress = False
        for cat in CATEGORIES:
            if counts[cat] >= per_category:
                continue
            for source_id, step, tags in candidates:
                if (
                    cat in tags
                    and step.step_id not in used
                    and per_source[source_id] < per_protocol
                ):
                    chosen.append((source_id, step, list(tags)))
                    used.add(step.step_id)
                    per_source[source_id] += 1
                    counts.update(tags)
                    progress = True
                    break
    return chosen


class ProtocolIndex:
    """Incremental "same protocol" lookup with the corpus dedup rule (exact text, high
    shingle Jaccard, or same title with moderate Jaccard), without all-pairs rescans."""

    def __init__(self) -> None:
        self._entries: list[tuple[str, frozenset[tuple[str, ...]], str, str]] = []

    def add(self, doc_id: str, text: str) -> None:
        self._entries.append(
            (doc_id, shingles(text), title_key(text), whitespace_normalized_sha256(text))
        )

    def match(self, text: str) -> str | None:
        sh, title, exact = shingles(text), title_key(text), whitespace_normalized_sha256(text)
        for doc_id, other, other_title, other_exact in self._entries:
            pair = Pair(
                "new", doc_id, jaccard(sh, other), title == other_title, exact == other_exact
            )
            if pair.same_protocol:
                return doc_id
        return None
