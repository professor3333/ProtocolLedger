"""Bundles for the span-relation model: self-contained and verified before loading.

Layout::

    bundle.json            manifest: version, labels, type pairs, config, file hashes
    model.safetensors      every model weight (encoder and heads); tensors only, no pickle
    encoder/config.json    encoder architecture, so no network access is needed to serve
    tokenizer/...          tokenizer files saved with case preservation forced

Every file listed in ``bundle.json`` is hash-checked before anything is read. Inference
runs on CPU. ``derive_onnx_bundle`` creates a separate, immutable bundle whose encoder runs
in ONNX Runtime (``onnx-fp32``) or with ONNX Runtime dynamic INT8 weights (``onnx-int8``);
the span and relation heads stay in PyTorch.
"""

from __future__ import annotations

import hashlib
import json
import os
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


ENCODER_RUNTIMES = ("torch-fp32", "onnx-fp32", "onnx-int8")


class _EncoderOutput:
    def __init__(self, hidden: torch.Tensor) -> None:
        self.last_hidden_state = hidden


class OnnxEncoder(torch.nn.Module):
    """Drop-in replacement for the transformer encoder, backed by ONNX Runtime."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        import onnxruntime

        options = onnxruntime.SessionOptions()
        threads = int(os.environ.get("PROTOCOLLEDGER_THREADS", "0"))
        if threads:
            options.intra_op_num_threads = threads
        self.session = onnxruntime.InferenceSession(
            str(path), options, providers=["CPUExecutionProvider"]
        )

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> _EncoderOutput:
        (hidden,) = self.session.run(
            None,
            {"input_ids": input_ids.cpu().numpy(), "attention_mask": attention_mask.cpu().numpy()},
        )
        return _EncoderOutput(torch.from_numpy(hidden))


class _HiddenStates(torch.nn.Module):
    def __init__(self, encoder: torch.nn.Module) -> None:
        super().__init__()
        self.encoder = encoder

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        hidden: torch.Tensor = self.encoder(
            input_ids=input_ids, attention_mask=attention_mask
        ).last_hidden_state
        return hidden


@dataclass
class NeuralExtractor:
    model: SpanRelationModel
    tokenizer: Any
    type_pairs: set[tuple[str, str]]
    device: torch.device
    runtime: str

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

    threads = int(os.environ.get("PROTOCOLLEDGER_THREADS", "0"))
    if threads:
        # Match the container's CPU quota; PyTorch otherwise sizes its pool to every host
        # core and oversubscribes a CPU-limited container.
        torch.set_num_threads(threads)
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
    runtime = str(manifest.get("encoder_runtime", "torch-fp32"))
    if runtime not in ENCODER_RUNTIMES:
        raise BundleError(f"unknown encoder runtime {runtime!r}")
    if runtime != "torch-fp32":
        model.encoder = OnnxEncoder(directory / "encoder.onnx")  # frees the torch encoder
    extractor = NeuralExtractor(
        model,
        tokenizer,
        {(a, b) for a, b in manifest["type_pairs"]},
        torch.device("cpu"),
        runtime,
    )
    return extractor, _sha256(raw_manifest)


def derive_onnx_bundle(source: Path, destination: Path, runtime: str) -> Path:
    """Copy a torch-fp32 bundle and add an ONNX encoder (``onnx-fp32`` or ``onnx-int8``)."""
    if runtime not in ("onnx-fp32", "onnx-int8"):
        raise BundleError(f"unsupported derived runtime {runtime!r}")
    raw = (source / "bundle.json").read_bytes()
    manifest = json.loads(raw)
    if manifest.get("encoder_runtime", "torch-fp32") != "torch-fp32":
        raise BundleError("derive from the torch-fp32 bundle")
    extractor, source_sha = load_neural_bundle(source, manifest, raw)
    if destination.exists() and any(destination.iterdir()):
        raise BundleError(f"{destination} is not empty; bundles are immutable")
    destination.mkdir(parents=True, exist_ok=True)
    for name in manifest["files"]:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((source / name).read_bytes())

    example = extractor.tokenizer(
        [["Add", "5", "mL", "of", "water"]], is_split_into_words=True, return_tensors="pt"
    )
    fp32_path = destination / ("encoder.onnx" if runtime == "onnx-fp32" else "encoder.fp32.onnx")
    batch, seq = torch.export.Dim("batch"), torch.export.Dim("seq")
    torch.onnx.export(
        _HiddenStates(extractor.model.encoder).eval(),
        (example["input_ids"], example["attention_mask"]),
        str(fp32_path),
        input_names=["input_ids", "attention_mask"],
        output_names=["hidden"],
        dynamic_shapes={"input_ids": {0: batch, 1: seq}, "attention_mask": {0: batch, 1: seq}},
        dynamo=True,
        external_data=False,
    )
    if runtime == "onnx-int8":
        from onnxruntime.quantization import QuantType, quantize_dynamic

        quantize_dynamic(
            str(fp32_path), str(destination / "encoder.onnx"), weight_type=QuantType.QInt8
        )
        fp32_path.unlink()
    files = sorted(p for p in destination.rglob("*") if p.is_file() and p.name != "bundle.json")
    manifest.update(
        {
            "model_version": f"{manifest['model_version']}-{runtime}",
            "encoder_runtime": runtime,
            "derived_from": {
                "model_version": manifest["model_version"],
                "bundle_sha256": source_sha,
            },
            "files": {
                p.relative_to(destination).as_posix(): {
                    "path": p.relative_to(destination).as_posix(),
                    "sha256": _sha256(p.read_bytes()),
                }
                for p in files
            },
        }
    )
    manifest.pop("evaluation", None)  # must be re-measured for the derived runtime
    (destination / "bundle.json").write_text(json.dumps(manifest, indent=1) + "\n", "utf-8")
    return destination
