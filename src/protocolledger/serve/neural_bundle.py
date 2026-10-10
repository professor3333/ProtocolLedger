"""Bundles for the span-relation model: self-contained and verified before loading.

Layout::

    bundle.json            manifest: version, labels, type pairs, config, file hashes
    model.safetensors      every model weight (encoder and heads); tensors only, no pickle
    encoder/config.json    encoder architecture, so no network access is needed to serve
    tokenizer/...          tokenizer files saved with case preservation forced

Every file listed in ``bundle.json`` is hash-checked before anything is read. Inference
runs in FP32 PyTorch on CPU; optimized runtimes (ONNX Runtime FP32 / INT8) are added only
after they are benchmarked against the accuracy gate.
"""

from __future__ import annotations

import hashlib
import json
import platform
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from safetensors.torch import load_file, save_file
from transformers import AutoConfig, AutoModel, AutoTokenizer

from protocolledger import __version__
from protocolledger.neural.config import NeuralConfig, preserves_case
from protocolledger.neural.model import SpanRelationModel
from protocolledger.neural.predict import predict_documents
from protocolledger.serve.bundle import BUNDLE_FORMAT, BundleError


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class NeuralExtractor:
    model: SpanRelationModel
    tokenizer: Any
    type_pairs: set[tuple[str, str]]
    device: torch.device
    quantization: str

    def extract(self, text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        (pred,) = predict_documents(
            self.model,
            self.tokenizer,
            [{"doc_id": "input", "text": text}],
            self.type_pairs,
            self.device,
        )
        return pred["entities"], pred["relations"]


def write_neural_bundle(
    directory: Path,
    model: SpanRelationModel,
    tokenizer: Any,
    type_pairs: set[tuple[str, str]],
    model_version: str,
    provenance: Mapping[str, Any],
) -> Path:
    if directory.exists() and any(directory.iterdir()):
        raise BundleError(f"{directory} is not empty; bundles are immutable")
    directory.mkdir(parents=True, exist_ok=True)
    state = {k: v.detach().cpu().contiguous() for k, v in model.state_dict().items()}
    save_file(state, str(directory / "model.safetensors"))
    encoder_config: Any = getattr(model.encoder, "config")  # noqa: B009
    encoder_config.save_pretrained(directory / "encoder")
    tokenizer.save_pretrained(directory / "tokenizer")
    files = sorted(p for p in directory.rglob("*") if p.is_file())
    manifest = {
        "bundle_format": BUNDLE_FORMAT,
        "model_version": model_version,
        "system": "span-relation",
        "preprocessing_version": "neural-1",
        "neural_config": model.config.to_json(),
        "entity_labels": model.entity_labels[1:],
        "relation_labels": model.relation_labels,
        "type_pairs": sorted(type_pairs),
        "hidden_size": int(encoder_config.hidden_size),
        "files": {
            p.relative_to(directory).as_posix(): {
                "path": p.relative_to(directory).as_posix(),
                "sha256": _sha256(p.read_bytes()),
            }
            for p in files
        },
        "runtime": {
            "protocolledger": __version__,
            "python": platform.python_version(),
            "torch": torch.__version__,
        },
        **dict(provenance),
    }
    (directory / "bundle.json").write_text(json.dumps(manifest, indent=1) + "\n", "utf-8")
    return directory


def load_neural_bundle(
    directory: Path, manifest: Mapping[str, Any], raw_manifest: bytes
) -> tuple[NeuralExtractor, str]:
    root = directory.resolve()
    for entry in manifest["files"].values():
        path = (directory / entry["path"]).resolve()
        if root not in path.parents:
            raise BundleError(f"bundle file outside the bundle directory: {entry['path']}")
        if not path.exists():
            raise BundleError(f"bundle file missing: {entry['path']}")
        if _sha256(path.read_bytes()) != entry["sha256"]:
            raise BundleError(f"hash mismatch for {entry['path']}; refusing to load")

    config = NeuralConfig.from_json(dict(manifest["neural_config"]))
    encoder = AutoModel.from_config(  # type: ignore[no-untyped-call]
        AutoConfig.from_pretrained(directory / "encoder")
    )
    tokenizer = AutoTokenizer.from_pretrained(directory / "tokenizer")
    if not preserves_case(tokenizer):
        raise BundleError("bundle tokenizer is not case-preserving")
    model = SpanRelationModel(
        encoder,
        int(manifest["hidden_size"]),
        config,
        list(manifest["entity_labels"]),
        list(manifest["relation_labels"]),
    )
    model.load_state_dict(load_file(str(directory / "model.safetensors")))
    model.eval()
    extractor = NeuralExtractor(
        model,
        tokenizer,
        {(a, b) for a, b in manifest["type_pairs"]},
        torch.device("cpu"),
        "none",
    )
    return extractor, _sha256(raw_manifest)
