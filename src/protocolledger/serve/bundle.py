"""Versioned model bundles: everything inference needs, with verified hashes.

A bundle is a directory containing ``bundle.json`` and the files it lists. Loading
checks every file's SHA-256 against ``bundle.json`` before deserializing anything,
because the relation model is a pickle and must only be loaded from verified bytes.
"""

from __future__ import annotations

import hashlib
import json
import platform
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import sklearn

from protocolledger import __version__
from protocolledger.baselines.crf_entities import CRFConfig, CRFTagger
from protocolledger.baselines.logreg_relations import LogRegRelations

BUNDLE_FORMAT = 1
PREPROCESSING_VERSION = "1"  # raw text, line steps, protocolledger.text.tokenize


class BundleError(RuntimeError):
    """The bundle is missing, incomplete, or does not match its manifest."""


class Extractor(Protocol):
    def extract(self, text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """(entities, relations) with raw-text code-point offsets."""
        ...


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class TraditionalExtractor:
    """CRF entities followed by logistic-regression relations."""

    tagger: CRFTagger
    relations: LogRegRelations

    def extract(self, text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        entities = self.tagger.predict_entities(text)
        return entities, self.relations.predict_relations(text, entities)


@dataclass
class LoadedBundle:
    path: Path
    manifest: dict[str, Any]
    manifest_sha256: str
    extractor: Extractor

    @property
    def model_version(self) -> str:
        return str(self.manifest["model_version"])

    def version_info(self) -> dict[str, Any]:
        return {
            "model_version": self.model_version,
            "system": self.manifest["system"],
            "bundle_sha256": self.manifest_sha256,
            "preprocessing_version": self.manifest["preprocessing_version"],
            "runtime": getattr(self.extractor, "runtime", "native"),
            "evaluation": self.manifest.get("evaluation", {}),
        }


def write_traditional_bundle(
    directory: Path,
    tagger: CRFTagger,
    relations: LogRegRelations,
    model_version: str,
    provenance: Mapping[str, Any],
) -> Path:
    if directory.exists() and any(directory.iterdir()):
        raise BundleError(f"{directory} is not empty; bundles are immutable")
    directory.mkdir(parents=True, exist_ok=True)
    files = {
        "crf": ("crf.crfsuite", tagger.model_bytes),
        "logreg": ("logreg.pkl", relations.to_bytes()),
    }
    for name, data in files.values():
        (directory / name).write_bytes(data)
    manifest = {
        "bundle_format": BUNDLE_FORMAT,
        "model_version": model_version,
        "system": "crf+logreg",
        "preprocessing_version": PREPROCESSING_VERSION,
        "crf_config": tagger.config_json(),
        "files": {
            key: {"path": name, "sha256": _sha256(data)} for key, (name, data) in files.items()
        },
        "runtime": {
            "protocolledger": __version__,
            "python": platform.python_version(),
            "scikit_learn": sklearn.__version__,
        },
        **dict(provenance),
    }
    (directory / "bundle.json").write_text(json.dumps(manifest, indent=1) + "\n", "utf-8")
    return directory


def load_bundle(directory: Path) -> LoadedBundle:
    manifest_path = directory / "bundle.json"
    if not manifest_path.exists():
        raise BundleError(f"{manifest_path} not found")
    raw = manifest_path.read_bytes()
    manifest: dict[str, Any] = json.loads(raw)
    if manifest.get("bundle_format") != BUNDLE_FORMAT:
        raise BundleError("unsupported bundle format")
    system = manifest.get("system")
    if system == "span-relation":
        from protocolledger.serve.neural_bundle import load_neural_bundle

        neural, digest = load_neural_bundle(directory, manifest, raw)
        return LoadedBundle(directory, manifest, digest, neural)
    if system != "crf+logreg":
        raise BundleError(f"unsupported system {system!r}")
    blobs: dict[str, bytes] = {}
    for key, entry in manifest["files"].items():
        path = directory / entry["path"]
        if path.resolve().parent != directory.resolve():
            raise BundleError(f"bundle file outside the bundle directory: {entry['path']}")
        if not path.exists():
            raise BundleError(f"bundle file missing: {entry['path']}")
        data = path.read_bytes()
        if _sha256(data) != entry["sha256"]:
            raise BundleError(f"hash mismatch for {entry['path']}; refusing to load")
        blobs[key] = data
    crf_config = {k: v for k, v in manifest["crf_config"].items() if k != "crf_version"}
    extractor = TraditionalExtractor(
        CRFTagger(CRFConfig(**crf_config), blobs["crf"]),
        LogRegRelations.from_bytes(blobs["logreg"]),
    )
    return LoadedBundle(directory, manifest, _sha256(raw), extractor)
