"""Train and evaluate one span-relation configuration on train/dev.

    uv run --extra neural python scripts/train_neural.py configs/neural/scibert-lr5e-5.json \\
        --out runs --seed 13

Writes runs/<name>-s<seed>/ (checkpoints, history; not committed), logs the run to the
MLflow file store (default mlruns/), and writes the dev report for the selected epoch
to reports/neural/<name>-s<seed>-dev.{json,md}. Re-running the same command resumes
from runs/<name>-s<seed>/last.pt. The test split is never touched.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import torch

from protocolledger.data.splits import load_split
from protocolledger.eval.scorer import render_markdown
from protocolledger.neural.config import ENCODERS, NeuralConfig
from protocolledger.neural.train import dev_metrics, load_best, train
from protocolledger.text.normalize import ENCODER_VIEW_VERSION

ROOT = Path(__file__).resolve().parents[1]


def git_commit() -> str:
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return out.stdout.strip() or "unknown"


def load_encoder(key: str) -> tuple[Any, Any, int]:
    from transformers import AutoModel, AutoTokenizer

    spec = ENCODERS[key]
    tokenizer = AutoTokenizer.from_pretrained(
        spec.name, revision=spec.revision, **dict(spec.tokenizer_kwargs)
    )
    if not tokenizer.is_fast:
        raise RuntimeError("a fast tokenizer is required for word alignment")
    if tokenizer.tokenize("mM DNA") != ["mM", "DNA"]:
        raise RuntimeError(f"{spec.name} tokenizer is not case-preserving")
    encoder = AutoModel.from_pretrained(spec.name, revision=spec.revision)
    return encoder, tokenizer, int(encoder.config.hidden_size)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("config", type=Path)
    parser.add_argument("--out", type=Path, default=ROOT / "runs")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--mlflow-store", type=Path, default=ROOT / "mlruns")
    parser.add_argument("--reports", type=Path, default=ROOT / "reports" / "neural")
    parser.add_argument("--max-steps-per-epoch", type=int, default=None, help="smoke tests only")
    parser.add_argument("--dev-limit", type=int, default=None, help="smoke tests only")
    parser.add_argument("--no-mlflow", action="store_true")
    args = parser.parse_args(argv)

    config = NeuralConfig.from_json(json.loads(args.config.read_text("utf-8")))
    if args.seed is not None:
        config = dataclasses.replace(config, seed=args.seed)
    name = f"{args.config.stem}-s{config.seed}"
    smoke = args.max_steps_per_epoch is not None or args.dev_limit is not None
    if smoke:
        name += "-smoke"
    run_dir = args.out / name
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    train_docs, dev_docs = load_split(ROOT, "train"), load_split(ROOT, "dev")
    if args.dev_limit:
        dev_docs = dev_docs[: args.dev_limit]
    splits_sha = hashlib.sha256((ROOT / "data/manifests/splits.json").read_bytes()).hexdigest()
    spec = ENCODERS[config.encoder]
    metadata = {
        "encoder_name": spec.name,
        "encoder_revision": spec.revision,
        "encoder_view_version": ENCODER_VIEW_VERSION,
        "splits_manifest_sha256": splits_sha,
        "code_commit": git_commit(),
        "torch": torch.__version__,
        "device": torch.cuda.get_device_name(0) if device.type == "cuda" else device.type,
        "smoke": smoke,
    }

    tracker: Any = None
    run_id_file = run_dir / "mlflow_run_id"
    if not args.no_mlflow:
        from protocolledger.neural.tracking import MLflowTracker

        run_dir.mkdir(parents=True, exist_ok=True)
        previous = run_id_file.read_text().strip() if run_id_file.exists() else None
        tracker = MLflowTracker(
            args.mlflow_store,
            "protocolledger-neural" if not smoke else "protocolledger-smoke",
            name,
            {k: str(v) for k, v in metadata.items()},
            run_id=previous,
        )
        run_id_file.write_text(tracker.run_id)
        if previous is None:
            tracker.log_params(config.to_json())

    encoder, tokenizer, hidden = load_encoder(config.encoder)
    status = "FAILED"
    try:
        result = train(
            config,
            encoder,
            hidden,
            tokenizer,
            train_docs,
            dev_docs,
            run_dir,
            tracker=tracker,
            device=device,
            max_steps_per_epoch=args.max_steps_per_epoch,
            metadata=metadata,
        )
        fresh_encoder, _, _ = load_encoder(config.encoder)
        model, type_pairs, _ = load_best(run_dir / "best.pt", fresh_encoder, device)
        _, e2e, gold = dev_metrics(model, tokenizer, dev_docs, type_pairs, device, resamples=1000)
        report = {
            "system": "span-relation",
            "run": name,
            "config": config.to_json(),
            "metadata": metadata,
            "best_epoch": result.best_epoch,
            "history": result.history,
            "coverage": {"train": result.train_coverage, "dev": result.dev_coverage},
            "end_to_end": e2e,
            "gold_entities": gold,
        }
        args.reports.mkdir(parents=True, exist_ok=True)
        json_path = args.reports / f"{name}-dev.json"
        json_path.write_text(json.dumps(report, indent=1) + "\n", "utf-8")
        md = [
            f"# {name}: dev results (best epoch {result.best_epoch})",
            "",
            render_markdown(e2e, "End-to-end"),
            render_markdown(gold, "Relations given gold entities"),
        ]
        (args.reports / f"{name}-dev.md").write_text("\n".join(md), "utf-8")
        if tracker is not None:
            tracker.log_metrics(
                {
                    "final_dev_entity_f1": e2e["entities"]["micro"]["f1"],
                    "final_dev_relation_f1": e2e["relations"]["micro"]["f1"],
                    "final_dev_relation_f1_gold_entities": gold["relations"]["micro"]["f1"],
                },
                step=result.best_epoch,
            )
            tracker.log_artifact(json_path)
        print(
            f"{name}: best epoch {result.best_epoch}, dev entity F1 "
            f"{e2e['entities']['micro']['f1']}, relation F1 {e2e['relations']['micro']['f1']} "
            f"{e2e['relations']['micro']['f1_ci95']}"
        )
        status = "FINISHED"
        return 0
    finally:
        if tracker is not None:
            tracker.end(status)


if __name__ == "__main__":
    sys.exit(main())
