"""Training loop with dev-based early stopping and resumable checkpoints.

Selection follows the project rule: relation heads train on gold entity endpoints, but
the checkpoint is chosen by dev **end-to-end** relation micro-F1 with predicted entities.
``last.pt`` holds everything needed to resume after an interrupted session (model,
optimizer, scheduler, AMP scaler, RNG states, history); ``best.pt`` holds the selected
weights and metadata.
"""

from __future__ import annotations

import json
import math
import random
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import torch
from torch import nn

from protocolledger.data.convert import step_spans
from protocolledger.data.schema import ENTITY_LABELS, RELATION_LABELS
from protocolledger.eval.scorer import evaluate
from protocolledger.neural.batching import encode_batch, sample_targets, subword_counter
from protocolledger.neural.config import NeuralConfig
from protocolledger.neural.encoding import Coverage, StepExample, build_examples
from protocolledger.neural.model import SpanRelationModel, sparse_table
from protocolledger.neural.predict import predict_documents
from protocolledger.neural.tracking import NullTracker, Tracker


@dataclass
class TrainResult:
    best_epoch: int
    best_dev_relation_f1: float
    history: list[dict[str, float]] = field(default_factory=list)
    train_coverage: dict[str, int] = field(default_factory=dict)
    dev_coverage: dict[str, int] = field(default_factory=dict)


def seed_everything(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def training_type_pairs(docs: Sequence[Mapping[str, Any]]) -> set[tuple[str, str]]:
    """(head type, tail type) pairs of same-step training relations."""
    pairs: set[tuple[str, str]] = set()
    for doc in docs:
        steps = step_spans(doc["text"])
        ents = {e["id"]: e for e in doc["entities"]}

        def step(offset: int, spans: list[tuple[int, int]] = steps) -> int:
            return next((i for i, (s, e) in enumerate(spans) if s <= offset <= e), -1)

        for r in doc["relations"]:
            h, t = ents[r["head"]], ents[r["tail"]]
            if step(h["start"]) == step(t["start"]):
                pairs.add((h["label"], t["label"]))
    return pairs


def _optimizer(model: SpanRelationModel, cfg: NeuralConfig) -> torch.optim.Optimizer:
    no_decay = ("bias", "LayerNorm.weight", "layer_norm.weight")
    head_ids = {id(p) for p in model.head_parameters()}
    groups: dict[tuple[bool, bool], list[nn.Parameter]] = {}
    for name, p in model.named_parameters():
        if not p.requires_grad:
            continue
        key = (id(p) in head_ids, any(n in name for n in no_decay))
        groups.setdefault(key, []).append(p)
    return torch.optim.AdamW(
        [
            {
                "params": params,
                "lr": cfg.head_learning_rate if is_head else cfg.learning_rate,
                "weight_decay": 0.0 if skip_decay else cfg.weight_decay,
            }
            for (is_head, skip_decay), params in groups.items()
        ]
    )


def _linear_schedule(optimizer: torch.optim.Optimizer, warmup: int, total: int) -> Any:
    def factor(step: int) -> float:
        if step < warmup:
            return (step + 1) / max(1, warmup)
        return max(0.0, (total - step) / max(1, total - warmup))

    return torch.optim.lr_scheduler.LambdaLR(optimizer, factor)


def _rng_state() -> dict[str, Any]:
    state: dict[str, Any] = {"python": random.getstate(), "torch": torch.get_rng_state()}
    if torch.cuda.is_available():
        state["cuda"] = torch.cuda.get_rng_state_all()
    return state


def _set_rng_state(state: Mapping[str, Any]) -> None:
    random.setstate(state["python"])
    torch.set_rng_state(state["torch"])
    if "cuda" in state and torch.cuda.is_available():
        torch.cuda.set_rng_state_all(state["cuda"])


def dev_metrics(
    model: SpanRelationModel,
    tokenizer: Any,
    dev_docs: Sequence[Mapping[str, Any]],
    type_pairs: set[tuple[str, str]],
    device: torch.device,
    resamples: int = 1,
) -> tuple[dict[str, float], dict[str, Any], dict[str, Any]]:
    e2e = evaluate(
        dev_docs,
        predict_documents(model, tokenizer, dev_docs, type_pairs, device),
        resamples=resamples,
    )
    gold = evaluate(
        dev_docs,
        predict_documents(model, tokenizer, dev_docs, type_pairs, device, gold_entities=True),
        resamples=resamples,
    )
    metrics = {
        "dev_entity_f1": e2e["entities"]["micro"]["f1"],
        "dev_relation_f1": e2e["relations"]["micro"]["f1"],
        "dev_relation_f1_gold_entities": gold["relations"]["micro"]["f1"],
        "dev_quantity_attachment": e2e["quantity_attachment"]["accuracy"],
        "dev_complete_steps": e2e["complete_steps"]["exact_match"],
    }
    return metrics, e2e, gold


def train(
    config: NeuralConfig,
    encoder: nn.Module,
    hidden_size: int,
    tokenizer: Any,
    train_docs: Sequence[Mapping[str, Any]],
    dev_docs: Sequence[Mapping[str, Any]],
    out_dir: Path,
    tracker: Tracker | None = None,
    device: torch.device | None = None,
    max_steps_per_epoch: int | None = None,
    metadata: Mapping[str, Any] | None = None,
    log: Callable[[str], None] = print,
) -> TrainResult:
    tracker = tracker or NullTracker()
    device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    out_dir.mkdir(parents=True, exist_ok=True)
    seed_everything(config.seed)

    entity_labels, relation_labels = sorted(ENTITY_LABELS), sorted(RELATION_LABELS)
    entity_index = {lab: i + 1 for i, lab in enumerate(entity_labels)}
    relation_index = {lab: i for i, lab in enumerate(relation_labels)}
    type_pairs = training_type_pairs(train_docs)

    counter = subword_counter(tokenizer)
    train_cov, dev_cov = Coverage(), Coverage()
    examples: list[StepExample] = []
    for doc in train_docs:
        examples += build_examples(
            doc, config.max_span_words, counter, config.max_subwords, train_cov
        )
    for doc in dev_docs:
        build_examples(doc, config.max_span_words, counter, config.max_subwords, dev_cov)
    examples = [ex for ex in examples if ex.words]

    model = SpanRelationModel(encoder, hidden_size, config, entity_labels, relation_labels)
    model.to(device)
    optimizer = _optimizer(model, config)
    steps_per_epoch = math.ceil(len(examples) / config.batch_size)
    if max_steps_per_epoch is not None:
        steps_per_epoch = min(steps_per_epoch, max_steps_per_epoch)
    updates_per_epoch = math.ceil(steps_per_epoch / config.grad_accumulation)
    total_updates = updates_per_epoch * config.epochs
    scheduler = _linear_schedule(
        optimizer, int(config.warmup_fraction * total_updates), total_updates
    )
    use_amp = config.mixed_precision and device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    history: list[dict[str, float]] = []
    best_f1, best_epoch, start_epoch, stale = -1.0, -1, 0, 0
    last_path, best_path = out_dir / "last.pt", out_dir / "best.pt"
    if last_path.exists():
        state = torch.load(last_path, map_location=device, weights_only=False)
        if state["config"] != config.to_json():
            raise RuntimeError(f"{last_path} was written with a different config")
        model.load_state_dict(state["model"])
        optimizer.load_state_dict(state["optimizer"])
        scheduler.load_state_dict(state["scheduler"])
        scaler.load_state_dict(state["scaler"])
        _set_rng_state(state["rng"])
        history, best_f1, best_epoch = state["history"], state["best_f1"], state["best_epoch"]
        start_epoch, stale = state["epoch"] + 1, state["stale"]
        log(f"resumed from epoch {state['epoch']} (best {best_f1:.4f} at epoch {best_epoch})")

    rng = random.Random(config.seed)
    for epoch in range(start_epoch, config.epochs):
        if stale >= config.patience:
            break
        model.train()
        started = time.time()
        order = list(range(len(examples)))
        random.Random(config.seed * 1000 + epoch).shuffle(order)
        rng.seed(config.seed * 1000 + epoch)
        total_loss, total_ent, total_rel = 0.0, 0.0, 0.0
        optimizer.zero_grad(set_to_none=True)
        for step in range(steps_per_epoch):
            batch_examples = [
                examples[i] for i in order[step * config.batch_size :][: config.batch_size]
            ]
            if not batch_examples:
                break
            batch = encode_batch(tokenizer, batch_examples).to(device)
            targets = sample_targets(
                batch_examples, config, rng, entity_index, relation_index, type_pairs
            ).to(device)
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
                words, cls = model.encode_words(
                    batch.input_ids, batch.attention_mask, batch.word_index, batch.num_words
                )
                table = sparse_table(words)
                spans = model.span_representations(
                    table, targets.span_batch, targets.span_start, targets.span_width
                )
                ent_logits = model.entity_logits(spans, cls, targets.span_batch)
                ent_loss = nn.functional.cross_entropy(ent_logits.float(), targets.span_label)
                if targets.pair_batch.numel():
                    rel_logits = model.relation_logits(
                        table, targets.pair_batch, targets.head, targets.tail
                    )
                    rel_loss = nn.functional.binary_cross_entropy_with_logits(
                        rel_logits.float(), targets.pair_labels
                    )
                else:
                    rel_loss = ent_loss.new_zeros(())
                loss = (ent_loss + rel_loss) / config.grad_accumulation
            scaler.scale(loss).backward()  # type: ignore[no-untyped-call]
            if (step + 1) % config.grad_accumulation == 0 or step + 1 == steps_per_epoch:
                scaler.unscale_(optimizer)
                nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(optimizer)
                scaler.update()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
            total_loss += loss.detach().item() * config.grad_accumulation
            total_ent += ent_loss.detach().item()
            total_rel += rel_loss.detach().item()

        metrics, _, _ = dev_metrics(model, tokenizer, dev_docs, type_pairs, device)
        metrics.update(
            {
                "train_loss": total_loss / steps_per_epoch,
                "train_entity_loss": total_ent / steps_per_epoch,
                "train_relation_loss": total_rel / steps_per_epoch,
                "epoch_seconds": time.time() - started,
            }
        )
        history.append({"epoch": float(epoch), **metrics})
        tracker.log_metrics(metrics, step=epoch)
        improved = metrics["dev_relation_f1"] > best_f1
        if improved:
            best_f1, best_epoch, stale = metrics["dev_relation_f1"], epoch, 0
            torch.save(
                {
                    "model": model.state_dict(),
                    "config": config.to_json(),
                    "entity_labels": entity_labels,
                    "relation_labels": relation_labels,
                    "type_pairs": sorted(type_pairs),
                    "hidden_size": hidden_size,
                    "epoch": epoch,
                    "dev_metrics": metrics,
                    "metadata": dict(metadata or {}),
                },
                best_path,
            )
        else:
            stale += 1
        torch.save(
            {
                "model": model.state_dict(),
                "optimizer": optimizer.state_dict(),
                "scheduler": scheduler.state_dict(),
                "scaler": scaler.state_dict(),
                "rng": _rng_state(),
                "config": config.to_json(),
                "history": history,
                "best_f1": best_f1,
                "best_epoch": best_epoch,
                "epoch": epoch,
                "stale": stale,
            },
            last_path,
        )
        log(
            f"epoch {epoch}: loss {metrics['train_loss']:.4f} | dev entity F1 "
            f"{metrics['dev_entity_f1']:.4f} relation F1 {metrics['dev_relation_f1']:.4f} "
            f"(gold entities {metrics['dev_relation_f1_gold_entities']:.4f})"
            f"{' *' if improved else ''} [{metrics['epoch_seconds']:.0f}s]"
        )

    (out_dir / "history.json").write_text(json.dumps(history, indent=1) + "\n", "utf-8")
    return TrainResult(best_epoch, best_f1, history, train_cov.to_json(), dev_cov.to_json())


def load_best(
    path: Path, encoder: nn.Module, device: torch.device
) -> tuple[SpanRelationModel, set[tuple[str, str]], dict[str, Any]]:
    state = torch.load(path, map_location=device, weights_only=False)
    config = NeuralConfig.from_json(state["config"])
    model = SpanRelationModel(
        encoder, state["hidden_size"], config, state["entity_labels"], state["relation_labels"]
    )
    model.load_state_dict(state["model"])
    model.to(device).eval()
    return model, {tuple(p) for p in state["type_pairs"]}, state
