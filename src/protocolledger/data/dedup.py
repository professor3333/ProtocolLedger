"""Exact and near-duplicate detection, and leakage-safe split assignment.

Two documents are treated as the *same protocol* (a copy or a revision) when either

* their 5-word-shingle Jaccard similarity is at least ``SAME_DOC_JACCARD``, or
* it is at least ``SAME_TITLE_JACCARD`` and their normalized titles are equal.

Those links are merged into connected components. Each component keeps exactly one
document, placed in the most protected split it touches (test > dev > train), so the
locked test split is never altered and no training copy of a dev/test document survives.

Pairs above ``SIBLING_JACCARD`` that do not meet the same-protocol rule are *template
siblings* (e.g. one vendor kit protocol adapted per tissue or strain). They are distinct
documents and are kept, but recorded so evaluation can report them as a slice.

The thresholds were chosen by inspecting the similarity distribution of this corpus;
see docs/dataset_card.md and data/manifests/dedup_report.json.
"""

from __future__ import annotations

import hashlib
import itertools
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

SHINGLE_WORDS = 5
SAME_DOC_JACCARD = 0.85
SAME_TITLE_JACCARD = 0.5
SIBLING_JACCARD = 0.5

# Most protected first. Higher-priority splits win when a protocol appears in several.
SPLIT_PRIORITY: tuple[str, ...] = ("test", "dev", "train")

_WORD = re.compile(r"\w+")


def whitespace_normalized_sha256(text: str) -> str:
    """The audit's exact-duplicate key: whitespace runs collapsed, no case folding."""
    return hashlib.sha256(" ".join(text.split()).encode("utf-8")).hexdigest()


def title_key(text: str) -> str:
    """First line, case-folded, whitespace collapsed, trailing punctuation stripped."""
    first = text.split("\n", 1)[0]
    return " ".join(first.split()).rstrip(" .").casefold()


def shingles(text: str, k: int = SHINGLE_WORDS) -> frozenset[tuple[str, ...]]:
    words = _WORD.findall(text.casefold())
    if len(words) < k:
        return frozenset({tuple(words)})
    return frozenset(tuple(words[i : i + k]) for i in range(len(words) - k + 1))


def jaccard(a: frozenset[tuple[str, ...]], b: frozenset[tuple[str, ...]]) -> float:
    union = len(a | b)
    return len(a & b) / union if union else 1.0


def containment(a: frozenset[tuple[str, ...]], b: frozenset[tuple[str, ...]]) -> float:
    """Share of ``a``'s shingles that also occur in ``b``. Unlike Jaccard it stays high when
    a short document is an excerpt of, or a variant inside, a much longer one."""
    return len(a & b) / len(a) if a else 1.0


@dataclass(frozen=True)
class Overlap:
    """How much of one document's text already occurs in a reference collection."""

    nearest: str  # reference document with the highest containment
    containment: float  # share of this document's shingles found in ``nearest``
    jaccard: float  # Jaccard with ``nearest``
    union_containment: float  # share found anywhere in the reference collection

    def to_json(self) -> dict[str, Any]:
        return {
            "nearest": self.nearest,
            "containment": round(self.containment, 4),
            "jaccard": round(self.jaccard, 4),
            "union_containment": round(self.union_containment, 4),
        }


def reference_overlap(texts: Mapping[str, str], reference: Mapping[str, str]) -> dict[str, Overlap]:
    """For each document in ``texts``, its overlap with the ``reference`` documents. Ties
    on containment go to the lowest reference id, so the result is deterministic."""
    ref = {i: shingles(reference[i]) for i in sorted(reference)}
    everything = frozenset().union(*ref.values())
    out = {}
    for doc_id in sorted(texts):
        sh = shingles(texts[doc_id])
        nearest = max(ref, key=lambda r: containment(sh, ref[r]))  # first maximum wins
        out[doc_id] = Overlap(
            nearest,
            containment(sh, ref[nearest]),
            jaccard(sh, ref[nearest]),
            containment(sh, everything),
        )
    return out


@dataclass(frozen=True)
class Pair:
    a: str
    b: str
    jaccard: float
    same_title: bool
    exact: bool

    @property
    def same_protocol(self) -> bool:
        return (
            self.exact
            or self.jaccard >= SAME_DOC_JACCARD
            or (self.same_title and self.jaccard >= SAME_TITLE_JACCARD)
        )


def similar_pairs(texts: Mapping[str, str], min_jaccard: float = SIBLING_JACCARD) -> list[Pair]:
    """All document pairs at or above ``min_jaccard``, plus every exact duplicate pair."""
    ids = sorted(texts)
    sh = {i: shingles(texts[i]) for i in ids}
    exact = {i: whitespace_normalized_sha256(texts[i]) for i in ids}
    titles = {i: title_key(texts[i]) for i in ids}
    pairs: list[Pair] = []
    for a, b in itertools.combinations(ids, 2):
        is_exact = exact[a] == exact[b]
        jac = jaccard(sh[a], sh[b])
        if is_exact or jac >= min_jaccard:
            pairs.append(Pair(a, b, round(jac, 4), titles[a] == titles[b], is_exact))
    return pairs


def components(ids: Iterable[str], links: Iterable[tuple[str, str]]) -> list[list[str]]:
    """Connected components (union-find), each sorted, ordered by first member."""
    parent = {i: i for i in ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in links:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    groups: dict[str, list[str]] = {}
    for i in parent:
        groups.setdefault(find(i), []).append(i)
    return sorted((sorted(g) for g in groups.values()), key=lambda g: g[0])


def _protocol_number(doc_id: str) -> int:
    match = re.search(r"(\d+)$", doc_id)
    if match is None:
        raise ValueError(f"doc id without a protocol number: {doc_id}")
    return int(match.group(1))


def choose_keeper(group: Sequence[str], split_of: Mapping[str, str]) -> str:
    """Most protected split first, then the lowest protocol number within it."""
    return min(
        group,
        key=lambda d: (SPLIT_PRIORITY.index(split_of[d]), _protocol_number(d), d),
    )


@dataclass(frozen=True)
class Exclusion:
    doc_id: str
    split: str
    kept: str
    kept_split: str
    reason: str  # "exact_duplicate" | "near_duplicate"

    def to_json(self) -> dict[str, str]:
        return {
            "doc_id": self.doc_id,
            "split": self.split,
            "kept": self.kept,
            "kept_split": self.kept_split,
            "reason": self.reason,
        }


def resolve(
    split_of: Mapping[str, str], pairs: Sequence[Pair]
) -> tuple[dict[str, list[str]], list[Exclusion], list[list[str]]]:
    """Return (kept doc ids per split, exclusions, same-protocol components)."""
    same = [p for p in pairs if p.same_protocol]
    exact_links = {(p.a, p.b) for p in same if p.exact}
    groups = [g for g in components(split_of, ((p.a, p.b) for p in same)) if len(g) > 1]

    exclusions: list[Exclusion] = []
    excluded: set[str] = set()
    exact_partner: dict[str, set[str]] = {}
    for a, b in exact_links:
        exact_partner.setdefault(a, set()).add(b)
        exact_partner.setdefault(b, set()).add(a)
    for group in groups:
        keeper = choose_keeper(group, split_of)
        for doc in group:
            if doc == keeper:
                continue
            reason = (
                "exact_duplicate" if keeper in exact_partner.get(doc, set()) else "near_duplicate"
            )
            exclusions.append(Exclusion(doc, split_of[doc], keeper, split_of[keeper], reason))
            excluded.add(doc)

    kept: dict[str, list[str]] = {s: [] for s in SPLIT_PRIORITY}
    for doc in sorted(split_of, key=lambda d: (split_of[d], _protocol_number(d))):
        if doc not in excluded:
            kept[split_of[doc]].append(doc)
    exclusions.sort(key=lambda e: (SPLIT_PRIORITY.index(e.split), _protocol_number(e.doc_id)))
    return kept, exclusions, groups


def _span_index(doc: Mapping[str, Any]) -> dict[str, tuple[str, int, int]]:
    return {e["id"]: (e["label"], e["start"], e["end"]) for e in doc["entities"]}


def annotation_agreement(a: Mapping[str, Any], b: Mapping[str, Any]) -> dict[str, int]:
    """Matched/total counts between two annotations of byte-identical text. Entities match
    on (label, start, end); relations on (head span, label, tail span)."""
    if a["text"] != b["text"]:
        raise ValueError("agreement requires identical text")
    sa, sb = _span_index(a), _span_index(b)
    ents_a, ents_b = set(sa.values()), set(sb.values())
    rels_a = {(sa[r["head"]], r["label"], sa[r["tail"]]) for r in a["relations"]}
    rels_b = {(sb[r["head"]], r["label"], sb[r["tail"]]) for r in b["relations"]}
    return {
        "entities_a": len(ents_a),
        "entities_b": len(ents_b),
        "entities_matched": len(ents_a & ents_b),
        "relations_a": len(rels_a),
        "relations_b": len(rels_b),
        "relations_matched": len(rels_a & rels_b),
    }


def f1(matched: int, total_a: int, total_b: int) -> float:
    return 2 * matched / (total_a + total_b) if total_a + total_b else 1.0
