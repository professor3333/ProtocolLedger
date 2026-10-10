"""Record committed evaluation reports as MLflow runs (idempotent).

    uv run --extra neural python scripts/log_reports_mlflow.py
    MLFLOW_ALLOW_FILE_STORE=true uvx mlflow ui --backend-store-uri mlruns

Baseline reports (reports/baselines/) go to the ``protocolledger-baselines`` experiment;
neural reports (reports/neural/, including runs fetched from Kaggle) go to
``protocolledger-neural`` with their per-epoch history replayed as steps. Each run is
tagged with its report's SHA-256, and a report already logged is skipped.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def headline(block: dict[str, Any]) -> dict[str, float]:
    return {
        "entity_f1": block["entities"]["micro"]["f1"],
        "relation_f1": block["relations"]["micro"]["f1"],
        "quantity_attachment": block["quantity_attachment"]["accuracy"],
        "complete_steps": block["complete_steps"]["exact_match"],
    }


def main() -> int:
    os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
    os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
    import mlflow
    from mlflow.tracking import MlflowClient

    mlflow.set_tracking_uri((ROOT / "mlruns").resolve().as_uri())
    client = MlflowClient()
    sources = [
        ("protocolledger-baselines", sorted((ROOT / "reports" / "baselines").glob("*-dev.json"))),
        ("protocolledger-neural", sorted((ROOT / "reports" / "neural").glob("*-dev.json"))),
    ]
    for experiment_name, paths in sources:
        experiment = mlflow.set_experiment(experiment_name)
        for path in paths:
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            found = client.search_runs(
                [experiment.experiment_id], f"tags.report_sha256 = '{digest}'"
            )
            if found:
                print(f"{path.name}: already logged")
                continue
            report = json.loads(raw)
            meta = report.get("metadata", {})
            tags = {
                "system": report["system"],
                "report_sha256": digest,
                "report": path.relative_to(ROOT).as_posix(),
                "code_commit": report.get("code_commit", meta.get("code_commit", "unknown")),
                "splits_manifest_sha256": report.get(
                    "splits_manifest_sha256", meta.get("splits_manifest_sha256", "unknown")
                ),
            }
            tags.update({k: str(v) for k, v in meta.items() if k not in tags})
            with mlflow.start_run(run_name=report.get("run", path.stem)):
                mlflow.set_tags(tags)
                for key, values in report.items():
                    if key.endswith("config") and isinstance(values, dict):
                        mlflow.log_params({f"{key}.{k}": str(v) for k, v in values.items()})
                for row in report.get("history", []):
                    step = int(row["epoch"])
                    mlflow.log_metrics({k: v for k, v in row.items() if k != "epoch"}, step=step)
                for mode in ("end_to_end", "gold_entities"):
                    mlflow.log_metrics(
                        {f"{mode}.{k}": v for k, v in headline(report[mode]).items()}
                    )
                if "best_epoch" in report:
                    mlflow.log_metric("best_epoch", report["best_epoch"])
                mlflow.log_artifact(str(path))
            print(f"{path.name}: logged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
