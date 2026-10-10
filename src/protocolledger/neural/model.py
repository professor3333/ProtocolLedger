"""SpERT-style joint span and relation classifier over a shared encoder.

Reference: Eberts and Ulges, "Span-based Joint Entity and Relation Extraction with
Transformer Pre-training" (arXiv:1909.07755). This is an independent implementation.

* Words are mean-pooled from their subwords.
* A span is the max-pool of its words, concatenated with a learned width embedding.
* Entity logits come from ``[span; CLS]``.
* Relation logits for an ordered pair come from
  ``[head span; tail span; max-pool of the words between; head type; tail type;
  signed distance bucket]``. The type and distance parts are switchable for ablation.
  Relations are multilabel (sigmoid).

Range max-pooling uses a sparse table (O(W log W) memory per sequence), so pooling over
every candidate span and every pair's context never materializes a per-pair mask.
"""

from __future__ import annotations

import torch
from torch import Tensor, nn

from protocolledger.neural.config import NeuralConfig

# Words between head and tail -> bucket; direction doubles the bucket count.
_DISTANCE_EDGES = (0, 1, 2, 3, 4, 7, 15, 31)
NUM_DISTANCE_BUCKETS = 2 * (len(_DISTANCE_EDGES) + 1)


def distance_bucket(between: Tensor, head_first: Tensor) -> Tensor:
    edges = torch.tensor(_DISTANCE_EDGES, device=between.device)
    bucket = torch.bucketize(between, edges, right=False)
    return bucket + (~head_first).long() * (len(_DISTANCE_EDGES) + 1)


def sparse_table(words: Tensor) -> Tensor:
    """``table[l, b, i] = max(words[b, i : i + 2**l])`` (rows past the end are padding)."""
    tables = [words]
    width = words.size(1)
    half = 1
    while 2 * half <= width:
        prev = tables[-1]
        nxt = prev.clone()
        nxt[:, : width - half] = torch.maximum(prev[:, : width - half], prev[:, half:])
        tables.append(nxt)
        half *= 2
    return torch.stack(tables)


def range_max(table: Tensor, batch: Tensor, start: Tensor, end: Tensor) -> Tensor:
    """Max over ``words[batch, start:end]`` for each query; requires ``end > start``."""
    length = (end - start).clamp(min=1)
    level = torch.floor(torch.log2(length.float())).long().clamp(max=table.size(0) - 1)
    reach = torch.pow(2, level)
    left = table[level, batch, start]
    right = table[level, batch, (end - reach).clamp(min=0)]
    return torch.maximum(left, right)


class SpanRelationModel(nn.Module):
    def __init__(
        self,
        encoder: nn.Module,
        hidden_size: int,
        config: NeuralConfig,
        entity_labels: list[str],
        relation_labels: list[str],
    ) -> None:
        super().__init__()
        self.config = config
        self.encoder = encoder
        self.entity_labels = ["None", *entity_labels]
        self.relation_labels = list(relation_labels)
        self.dropout = nn.Dropout(config.dropout)
        self.width_embedding = nn.Embedding(config.max_span_words + 1, config.width_embedding_dim)
        span_dim = hidden_size + config.width_embedding_dim
        self.entity_head = nn.Linear(span_dim + hidden_size, len(self.entity_labels))

        relation_dim = 2 * span_dim + hidden_size
        self.type_embedding: nn.Embedding | None = None
        self.distance_embedding: nn.Embedding | None = None
        if config.use_type_features:
            self.type_embedding = nn.Embedding(len(self.entity_labels), config.type_embedding_dim)
            relation_dim += 2 * config.type_embedding_dim
        if config.use_distance_features:
            self.distance_embedding = nn.Embedding(
                NUM_DISTANCE_BUCKETS, config.distance_embedding_dim
            )
            relation_dim += config.distance_embedding_dim
        self.relation_head = nn.Linear(relation_dim, len(self.relation_labels))
        self.no_context = nn.Parameter(torch.zeros(hidden_size))
        if config.freeze_encoder:
            for p in self.encoder.parameters():
                p.requires_grad = False

    def head_parameters(self) -> list[nn.Parameter]:
        encoder_ids = {id(p) for p in self.encoder.parameters()}
        return [p for p in self.parameters() if id(p) not in encoder_ids]

    # ---------------------------------------------------------------- encoder

    def encode_words(
        self, input_ids: Tensor, attention_mask: Tensor, word_index: Tensor, num_words: int
    ) -> tuple[Tensor, Tensor]:
        """Return (word states ``[B, W, H]``, CLS state ``[B, H]``)."""
        hidden = self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
        batch, _, size = hidden.shape
        valid = word_index >= 0
        slot = torch.where(valid, word_index, torch.full_like(word_index, num_words))
        sums = hidden.new_zeros(batch, num_words + 1, size)
        sums.scatter_add_(1, slot.unsqueeze(-1).expand(-1, -1, size), hidden)
        counts = hidden.new_zeros(batch, num_words + 1)
        counts.scatter_add_(1, slot, valid.to(hidden.dtype))
        words = sums[:, :num_words] / counts[:, :num_words].clamp(min=1).unsqueeze(-1)
        return self.dropout(words), self.dropout(hidden[:, 0])

    # ------------------------------------------------------------------ spans

    def span_representations(
        self, table: Tensor, batch: Tensor, start: Tensor, width: Tensor
    ) -> Tensor:
        pooled = range_max(table, batch, start, start + width)
        return torch.cat([pooled, self.width_embedding(width)], dim=-1)

    def entity_logits(self, spans: Tensor, cls: Tensor, batch: Tensor) -> Tensor:
        logits: Tensor = self.entity_head(self.dropout(torch.cat([spans, cls[batch]], dim=-1)))
        return logits

    def relation_logits(
        self,
        table: Tensor,
        batch: Tensor,
        head: tuple[Tensor, Tensor, Tensor],
        tail: tuple[Tensor, Tensor, Tensor],
    ) -> Tensor:
        """``head``/``tail`` are (start, width, entity type index) per pair."""
        (hs, hw, ht), (ts, tw, tt) = head, tail
        head_repr = self.span_representations(table, batch, hs, hw)
        tail_repr = self.span_representations(table, batch, ts, tw)
        head_first = hs <= ts
        gap_start = torch.where(head_first, hs + hw, ts + tw)
        gap_end = torch.where(head_first, ts, hs)
        has_gap = gap_end > gap_start
        context = range_max(table, batch, gap_start.clamp(max=table.size(2) - 1), gap_end)
        context = torch.where(has_gap.unsqueeze(-1), context, self.no_context.expand_as(context))
        parts = [head_repr, tail_repr, context]
        if self.type_embedding is not None:
            parts += [self.type_embedding(ht), self.type_embedding(tt)]
        if self.distance_embedding is not None:
            between = (gap_end - gap_start).clamp(min=0)
            parts.append(self.distance_embedding(distance_bucket(between, head_first)))
        logits: Tensor = self.relation_head(self.dropout(torch.cat(parts, dim=-1)))
        return logits
