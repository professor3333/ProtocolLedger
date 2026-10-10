"""Inference: candidate spans → entities → relations → raw-text offsets."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import torch

from protocolledger.neural.batching import encode_batch, subword_counter
from protocolledger.neural.encoding import StepExample, build_examples
from protocolledger.neural.model import SpanRelationModel, sparse_table


def _decode_entities(
    probs: torch.Tensor, spans: list[tuple[int, int, int]], labels: list[str]
) -> dict[int, list[tuple[int, int, str]]]:
    """Greedy non-overlapping decode by confidence, per example."""
    best_p, best_label = probs.max(dim=-1)
    chosen: dict[int, list[tuple[int, int, str, float]]] = {}
    order = torch.argsort(best_p, descending=True).tolist()
    for idx in order:
        label = int(best_label[idx])
        if label == 0:
            continue
        b, s, w = spans[idx]
        kept = chosen.setdefault(b, [])
        if any(s < ks + kw and ks < s + w for ks, kw, _, _ in kept):
            continue
        kept.append((s, w, labels[label], float(best_p[idx])))
    return {b: [(s, w, lab) for s, w, lab, _ in v] for b, v in chosen.items()}


@torch.no_grad()
def predict_examples(
    model: SpanRelationModel,
    tokenizer: Any,
    examples: Sequence[StepExample],
    type_pairs: set[tuple[str, str]],
    device: torch.device,
    gold_entities: bool = False,
) -> list[tuple[list[tuple[int, int, str]], list[tuple[int, int, str]]]]:
    """For each example: (entities as (start word, width, label), relations as
    (head entity index, tail entity index, label))."""
    cfg = model.config
    batch = encode_batch(tokenizer, examples).to(device)
    words, cls = model.encode_words(
        batch.input_ids, batch.attention_mask, batch.word_index, batch.num_words
    )
    table = sparse_table(words)

    if gold_entities:
        per_example = {
            b: [(s, e - s, lab) for s, e, lab in ex.entities] for b, ex in enumerate(examples)
        }
    else:
        spans = [
            (b, s, w)
            for b, ex in enumerate(examples)
            for s in range(len(ex.words))
            for w in range(1, min(cfg.max_span_words, len(ex.words) - s) + 1)
        ]
        per_example = {}
        if spans:
            sb, ss, sw = (torch.tensor(x, device=device) for x in zip(*spans, strict=True))
            logits = model.entity_logits(model.span_representations(table, sb, ss, sw), cls, sb)
            per_example = _decode_entities(
                logits.float().softmax(-1).cpu(), spans, model.entity_labels
            )

    label_index = {lab: i for i, lab in enumerate(model.entity_labels)}
    pairs: list[tuple[int, int, int]] = []
    for b in range(len(examples)):
        ents = per_example.get(b, [])
        for i, hi in enumerate(ents):
            for j, ti in enumerate(ents):
                if i != j and (not cfg.restrict_type_pairs or (hi[2], ti[2]) in type_pairs):
                    pairs.append((b, i, j))
    relations: dict[int, list[tuple[int, int, str]]] = {}
    if pairs:
        pb = torch.tensor([p[0] for p in pairs], device=device)

        def part(which: int, field: int) -> torch.Tensor:
            values = []
            for b, i, j in pairs:
                ent = per_example[b][i if which == 0 else j]
                values.append(label_index[ent[2]] if field == 2 else ent[field])
            return torch.tensor(values, device=device)

        head = (part(0, 0), part(0, 1), part(0, 2))
        tail = (part(1, 0), part(1, 1), part(1, 2))
        probs = model.relation_logits(table, pb, head, tail).float().sigmoid().cpu()
        hits = (probs >= cfg.relation_threshold).nonzero().tolist()
        for row, col in hits:
            b, i, j = pairs[row]
            relations.setdefault(b, []).append((i, j, model.relation_labels[col]))
    return [(per_example.get(b, []), relations.get(b, [])) for b in range(len(examples))]


def predict_documents(
    model: SpanRelationModel,
    tokenizer: Any,
    docs: Sequence[Mapping[str, Any]],
    type_pairs: set[tuple[str, str]],
    device: torch.device,
    gold_entities: bool = False,
    batch_size: int = 32,
) -> list[dict[str, Any]]:
    """Predictions in the scorer's format, one record per document, offsets into raw text."""
    model.eval()
    counter = subword_counter(tokenizer)
    cfg = model.config
    out = []
    for doc in docs:
        source = doc if gold_entities else {**doc, "entities": [], "relations": []}
        examples = build_examples(source, cfg.max_span_words, counter, cfg.max_subwords)
        entities: list[dict[str, Any]] = []
        relations: list[dict[str, str]] = []
        seen: dict[tuple[int, int, str], str] = {}
        for start in range(0, len(examples), batch_size):
            chunk = examples[start : start + batch_size]
            for ex, (ents, rels) in zip(
                chunk,
                predict_examples(model, tokenizer, chunk, type_pairs, device, gold_entities),
                strict=True,
            ):
                ids = []
                for s, w, label in ents:
                    key = (ex.words[s].start, ex.words[s + w - 1].end, label)
                    if key not in seen:
                        seen[key] = f"P{len(seen) + 1}"
                        entities.append(
                            {"id": seen[key], "label": label, "start": key[0], "end": key[1]}
                        )
                    ids.append(seen[key])
                for i, j, label in rels:
                    relations.append({"head": ids[i], "label": label, "tail": ids[j]})
        out.append({"doc_id": doc["doc_id"], "entities": entities, "relations": relations})
    return out
