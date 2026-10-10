"""Experiment configuration and pinned encoders."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

NEURAL_VERSION = "1"


@dataclass(frozen=True)
class EncoderSpec:
    name: str
    revision: str
    tokenizer_kwargs: tuple[tuple[str, Any], ...] = ()


# Revisions pinned to the Hugging Face commit inspected on 2026-10-10. SciBERT's cased
# checkpoint ships no tokenizer_config.json, so the tokenizer would default to
# lower-casing; case must be forced off for both encoders.
ENCODERS: dict[str, EncoderSpec] = {
    "scibert": EncoderSpec(
        "allenai/scibert_scivocab_cased",
        "ddf0be025f8e432a1870e34811997ba6725bf04a",
        (("do_lower_case", False),),
    ),
    "bert": EncoderSpec(
        "google-bert/bert-base-cased",
        "cd5ef92a9fb2f889e972770a36d4ed042daf221e",
        (("do_lower_case", False),),
    ),
}


@dataclass(frozen=True)
class NeuralConfig:
    encoder: str = "scibert"
    freeze_encoder: bool = False
    max_span_words: int = 10
    width_embedding_dim: int = 25
    type_embedding_dim: int = 25
    distance_embedding_dim: int = 25
    use_type_features: bool = True
    use_distance_features: bool = True
    dropout: float = 0.1
    negative_spans: int = 100
    negative_pairs: int = 100
    hard_negatives: bool = True
    learning_rate: float = 5e-5
    head_learning_rate: float = 1e-3
    weight_decay: float = 0.01
    warmup_fraction: float = 0.1
    batch_size: int = 16
    grad_accumulation: int = 1
    epochs: int = 10
    patience: int = 3
    relation_threshold: float = 0.5
    restrict_type_pairs: bool = True
    max_subwords: int = 510
    seed: int = 13
    mixed_precision: bool = True

    def to_json(self) -> dict[str, Any]:
        return {"neural_version": NEURAL_VERSION, **asdict(self)}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> NeuralConfig:
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known - {"neural_version"}
        if unknown:
            raise ValueError(f"unknown config keys: {sorted(unknown)}")
        return cls(**{k: v for k, v in data.items() if k in known})

    @classmethod
    def load(cls, path: Path) -> NeuralConfig:
        return cls.from_json(json.loads(path.read_text("utf-8")))
