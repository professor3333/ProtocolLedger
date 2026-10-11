"""Turn a trained span-relation checkpoint into a verified, servable bundle.

    uv run --extra neural python scripts/build_neural_bundle.py \\
        --checkpoint artifacts/kaggle/.../runs/<run>/best.pt \\
        --report reports/neural/<run>-dev.json

Rebuilds the model from the pinned encoder configuration (weights come from the
checkpoint), writes artifacts/bundles/<model_version>/, reloads it through the
hash-verifying loader and re-evaluates dev on CPU. Refuses to keep the bundle if CPU dev
end-to-end F1 differs from the report by more than --tolerance (GPU and CPU arithmetic
differ slightly). Dev only; the test split is never touched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

import torch
from transformers import AutoConfig, AutoModel, AutoTokenizer

from protocolledger.data.splits import load_split
from protocolledger.eval.scorer import evaluate
from protocolledger.neural.config import ENCODERS, NeuralConfig, preserves_case
from protocolledger.neural.train import load_best
from protocolledger.serve.bundle import load_bundle
from protocolledger.serve.neural_bundle import write_neural_bundle

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--tolerance", type=float, default=0.002)
    args = parser.parse_args(argv)

    report_bytes = args.report.read_bytes()
    report = json.loads(report_bytes)
    config = NeuralConfig.from_json(report["config"])
    spec = ENCODERS[config.encoder]
    encoder_config = AutoConfig.from_pretrained(spec.name, revision=spec.revision)
    encoder = AutoModel.from_config(encoder_config)  # type: ignore[no-untyped-call]
    tokenizer = AutoTokenizer.from_pretrained(
        spec.name, revision=spec.revision, **dict(spec.tokenizer_kwargs)
    )
    if not preserves_case(tokenizer):
        raise SystemExit("error: tokenizer is not case-preserving")
    cpu = torch.device("cpu")
    model, type_pairs, _ = load_best(args.checkpoint, encoder, cpu)

    checkpoint_sha = hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
    model_version = f"{report['run']}-{checkpoint_sha[:10]}"
    directory = ROOT / "artifacts" / "bundles" / model_version
    if directory.exists():
        raise SystemExit(f"error: {directory} exists; bundles are immutable")
    reported = report["end_to_end"]
    provenance = {
        "training": {
            "run": report["run"],
            "report": args.report.relative_to(ROOT).as_posix(),
            "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
            "checkpoint_sha256": checkpoint_sha,
            "best_epoch": report["best_epoch"],
            "encoder": spec.name,
            "encoder_revision": spec.revision,
            **{k: report["metadata"][k] for k in ("splits_manifest_sha256", "code_commit")},
        },
    }
    write_neural_bundle(directory, model, tokenizer, type_pairs, model_version, provenance)

    dev = load_split(ROOT, "dev")
    loaded = load_bundle(directory)
    started = time.time()
    preds = []
    for doc in dev:
        entities, relations = loaded.extractor.extract(doc["text"])
        preds.append({"doc_id": doc["doc_id"], "entities": entities, "relations": relations})
    seconds = time.time() - started
    measured = evaluate(dev, preds, resamples=1)
    got = (measured["entities"]["micro"]["f1"], measured["relations"]["micro"]["f1"])
    want = (reported["entities"]["micro"]["f1"], reported["relations"]["micro"]["f1"])
    print(
        f"CPU dev entity F1 {got[0]} (report {want[0]}), relation F1 {got[1]} "
        f"(report {want[1]}); {seconds:.0f}s for {len(dev)} documents"
    )
    if any(abs(a - b) > args.tolerance for a, b in zip(got, want, strict=True)):
        shutil.rmtree(directory)
        print("error: bundle does not reproduce the report; removed", file=sys.stderr)
        return 1
    manifest_path = directory / "bundle.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["evaluation"] = {
        "split": "dev",
        "device": "cpu",
        "entity_f1": got[0],
        "relation_f1_end_to_end": got[1],
        "reported_gpu": {"entity_f1": want[0], "relation_f1_end_to_end": want[1]},
    }
    manifest_path.write_text(json.dumps(manifest, indent=1) + "\n", "utf-8")
    with (directory.parent / f"{model_version}-dev-predictions.jsonl").open("w") as fh:
        for p in preds:
            fh.write(json.dumps(p) + "\n")
    print(f"wrote {directory.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
