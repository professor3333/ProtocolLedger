"""Subword encoding of word sequences, and training-target sampling."""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import torch
from torch import Tensor

from protocolledger.neural.config import NeuralConfig
from protocolledger.neural.encoding import StepExample
from protocolledger.text.normalize import encoder_view


@dataclass
class EncodedBatch:
    input_ids: Tensor
    attention_mask: Tensor
    word_index: Tensor  # [B, S] subword -> word index, -1 for special/padding tokens
    num_words: int

    def to(self, device: torch.device) -> EncodedBatch:
        return EncodedBatch(
            self.input_ids.to(device),
            self.attention_mask.to(device),
            self.word_index.to(device),
            self.num_words,
        )


def encode_batch(tokenizer: Any, examples: Sequence[StepExample]) -> EncodedBatch:
    enc = tokenizer(
        [[encoder_view(w) for w in ex.word_texts] for ex in examples],
        is_split_into_words=True,
        padding=True,
        truncation=False,
        return_tensors="pt",
    )
    rows = []
    for i in range(len(examples)):
        rows.append([-1 if w is None else w for w in enc.word_ids(i)])
    return EncodedBatch(
        enc["input_ids"],
        enc["attention_mask"],
        torch.tensor(rows, dtype=torch.long),
        max(len(ex.words) for ex in examples),
    )


def subword_counter(tokenizer: Any) -> Any:
    cache: dict[str, int] = {}

    def count(word: str) -> int:
        if word not in cache:
            view = encoder_view(word)
            cache[word] = len(tokenizer(view, add_special_tokens=False)["input_ids"])
        return cache[word]

    return count


@dataclass
class Targets:
    span_batch: Tensor
    span_start: Tensor
    span_width: Tensor
    span_label: Tensor
    pair_batch: Tensor
    head: tuple[Tensor, Tensor, Tensor]
    tail: tuple[Tensor, Tensor, Tensor]
    pair_labels: Tensor  # [P, R] multi-hot

    def to(self, device: torch.device) -> Targets:
        def mv(t: Tensor) -> Tensor:
            return t.to(device)

        return Targets(
            mv(self.span_batch),
            mv(self.span_start),
            mv(self.span_width),
            mv(self.span_label),
            mv(self.pair_batch),
            (mv(self.head[0]), mv(self.head[1]), mv(self.head[2])),
            (mv(self.tail[0]), mv(self.tail[1]), mv(self.tail[2])),
            mv(self.pair_labels),
        )


def _touches(a: tuple[int, int], b: tuple[int, int]) -> bool:
    """Spans (start, end exclusive) overlap or are directly adjacent."""
    return a[0] <= b[1] and b[0] <= a[1]


def sample_targets(
    examples: Sequence[StepExample],
    config: NeuralConfig,
    rng: random.Random,
    entity_index: dict[str, int],
    relation_index: dict[str, int],
    type_pairs: set[tuple[str, str]],
) -> Targets:
    sb: list[int] = []
    ss: list[int] = []
    sw: list[int] = []
    sl: list[int] = []
    pb: list[int] = []
    head: list[list[int]] = [[], [], []]
    tail: list[list[int]] = [[], [], []]
    labels: list[list[float]] = []
    k = config.max_span_words

    for b, ex in enumerate(examples):
        n = len(ex.words)
        gold = {(s, e - s): lab for s, e, lab in ex.entities}
        negatives = [
            (s, w) for s in range(n) for w in range(1, min(k, n - s) + 1) if (s, w) not in gold
        ]
        if config.hard_negatives and gold:
            near = [
                c
                for c in negatives
                if any(_touches((c[0], c[0] + c[1]), (s, s + w)) for s, w in gold)
            ]
            far = [c for c in negatives if c not in set(near)]
            take_near = rng.sample(near, min(len(near), config.negative_spans // 2))
            rest = config.negative_spans - len(take_near)
            chosen = take_near + rng.sample(far, min(len(far), rest))
        else:
            chosen = rng.sample(negatives, min(len(negatives), config.negative_spans))
        spans = [(s, w, entity_index[lab]) for (s, w), lab in gold.items()]
        spans += [(s, w, 0) for s, w in chosen]
        for s, w, label in spans:
            sb.append(b)
            ss.append(s)
            sw.append(w)
            sl.append(label)

        ents = ex.entities
        gold_pairs: dict[tuple[int, int], set[str]] = {}
        for h, t, lab in ex.relations:
            gold_pairs.setdefault((h, t), set()).add(lab)
        candidates = [
            (i, j)
            for i in range(len(ents))
            for j in range(len(ents))
            if i != j
            and (not config.restrict_type_pairs or (ents[i][2], ents[j][2]) in type_pairs)
            and (i, j) not in gold_pairs
        ]
        if config.hard_negatives and gold_pairs:
            involved = {x for pair in gold_pairs for x in pair}
            hard = [c for c in candidates if c[0] in involved or c[1] in involved]
            soft = [c for c in candidates if c not in set(hard)]
            take_hard = rng.sample(hard, min(len(hard), config.negative_pairs // 2))
            rest = config.negative_pairs - len(take_hard)
            pairs = take_hard + rng.sample(soft, min(len(soft), rest))
        else:
            pairs = rng.sample(candidates, min(len(candidates), config.negative_pairs))
        for i, j in list(gold_pairs) + pairs:
            hi, ti = ents[i], ents[j]
            pb.append(b)
            for slot, value in zip(head, (hi[0], hi[1] - hi[0], entity_index[hi[2]]), strict=True):
                slot.append(value)
            for slot, value in zip(tail, (ti[0], ti[1] - ti[0], entity_index[ti[2]]), strict=True):
                slot.append(value)
            row = [0.0] * len(relation_index)
            for lab in gold_pairs.get((i, j), ()):
                row[relation_index[lab]] = 1.0
            labels.append(row)

    def lt(xs: list[int]) -> Tensor:
        return torch.tensor(xs, dtype=torch.long)

    return Targets(
        lt(sb),
        lt(ss),
        lt(sw),
        lt(sl),
        lt(pb),
        (lt(head[0]), lt(head[1]), lt(head[2])),
        (lt(tail[0]), lt(tail[1]), lt(tail[2])),
        torch.tensor(labels, dtype=torch.float32).reshape(-1, len(relation_index)),
    )
