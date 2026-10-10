"""Convert canonical documents into per-step examples over words.

Words come from :func:`protocolledger.text.tokenize`, the same offset-preserving
tokenizer as the baselines, so every candidate span maps exactly back to raw-text
character offsets. Each protocol step becomes one example. A step whose subword length
would exceed the encoder limit is split into windows, and anything this makes
unreachable is counted.

Gold that the model cannot represent is counted in :class:`Coverage` and still scored as
a miss: entities whose boundaries fall inside a word, entities wider than
``max_span_words``, relations whose endpoints are unreachable or in different windows.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from protocolledger.data.convert import step_spans
from protocolledger.text.tokenize import Token, tokenize


@dataclass
class Coverage:
    entities: int = 0
    entities_misaligned: int = 0
    entities_too_wide: int = 0
    entities_split_by_window: int = 0
    relations: int = 0
    relations_unreachable: int = 0

    def to_json(self) -> dict[str, int]:
        return dict(self.__dict__)


@dataclass
class StepExample:
    doc_id: str
    words: list[Token]
    # (start word, end word exclusive, label) for reachable gold entities
    entities: list[tuple[int, int, str]] = field(default_factory=list)
    # (head index, tail index into ``entities``, label)
    relations: list[tuple[int, int, str]] = field(default_factory=list)

    @property
    def word_texts(self) -> list[str]:
        return [w.text for w in self.words]


def _windows(
    words: list[Token], count_subwords: Callable[[str], int], max_subwords: int
) -> list[tuple[int, int]]:
    """Greedy word windows whose subword count stays within the encoder limit."""
    windows: list[tuple[int, int]] = []
    start, used = 0, 0
    for i, w in enumerate(words):
        n = max(1, count_subwords(w.text))
        if used + n > max_subwords and i > start:
            windows.append((start, i))
            start, used = i, 0
        used += n
    if start < len(words) or not windows:
        windows.append((start, len(words)))
    return windows


def build_examples(
    doc: Mapping[str, Any],
    max_span_words: int,
    count_subwords: Callable[[str], int],
    max_subwords: int,
    coverage: Coverage | None = None,
) -> list[StepExample]:
    cov = coverage if coverage is not None else Coverage()
    text: str = doc["text"]
    gold_entities: Sequence[Mapping[str, Any]] = doc.get("entities", [])
    gold_relations: Sequence[Mapping[str, Any]] = doc.get("relations", [])
    placed: dict[str, tuple[int, int]] = {}  # entity id -> (example index, entity index)
    examples: list[StepExample] = []

    for s_start, s_end in step_spans(text):
        words = tokenize(text, s_start, s_end)
        if not words:
            continue
        step_entities = [e for e in gold_entities if s_start <= e["start"] < s_end + 1]
        for w_start, w_end in _windows(words, count_subwords, max_subwords):
            window = words[w_start:w_end]
            example = StepExample(doc["doc_id"], window)
            starts = {w.start: k for k, w in enumerate(window)}
            ends = {w.end: k + 1 for k, w in enumerate(window)}
            lo, hi = window[0].start, window[-1].end
            for e in step_entities:
                if not (lo <= e["start"] and e["end"] <= hi):
                    continue
                i, j = starts.get(e["start"]), ends.get(e["end"])
                if i is None or j is None:
                    continue  # counted below as misaligned
                if j - i > max_span_words:
                    continue  # counted below as too wide
                placed[e["id"]] = (len(examples), len(example.entities))
                example.entities.append((i, j, e["label"]))
            examples.append(example)

    word_starts = {w.start for ex in examples for w in ex.words}
    word_ends = {w.end for ex in examples for w in ex.words}
    for e in gold_entities:
        cov.entities += 1
        if e["id"] in placed:
            continue
        toks = tokenize(text, e["start"], e["end"])
        if e["start"] not in word_starts or e["end"] not in word_ends:
            cov.entities_misaligned += 1
        elif len(toks) > max_span_words:
            cov.entities_too_wide += 1
        else:
            cov.entities_split_by_window += 1

    for r in gold_relations:
        cov.relations += 1
        head, tail = placed.get(r["head"]), placed.get(r["tail"])
        if head is None or tail is None or head[0] != tail[0]:
            cov.relations_unreachable += 1
            continue
        examples[head[0]].relations.append((head[1], tail[1], r["label"]))
    return examples
