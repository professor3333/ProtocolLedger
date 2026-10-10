"""Record the committed baseline reports as MLflow runs (idempotent).

    uv run --extra neural python scripts/log_baselines_mlflow.py

Each run is tagged with the SHA-256 of its source report; a report already logged is
skipped, so re-running never duplicates runs.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = {"rules": "rules-dev.json", "crf+logreg": "crf-logreg-dev.json"}
EXPERIMENT = "protocolledger-baselines"


def main() -> int:
    os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
    os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
    import mlflow
    from mlflow.tracking import MlflowClient

    mlflow.set_tracking_uri((ROOT / "mlruns").resolve().as_uri())
    experiment = mlflow.set_experiment(EXPERIMENT)
    client = MlflowClient()
    for system, filename in REPORTS.items():
        path = ROOT / "reports" / "baselines" / filename
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        existing = client.search_runs(
            [experiment.experiment_id], f"tags.report_sha256 = '{digest}'"
        )
        if existing:
            print(f"{system}: already logged ({existing[0].info.run_id})")
            continue
        report = json.loads(raw)
        params = {k: v for k, v in report.items() if k.endswith("config")}
        with mlflow.start_run(run_name=f"{system}-dev"):
            mlflow.set_tags(
                {
                    "system": system,
                    "report_sha256": digest,
                    "code_commit": report.get("code_commit", "unknown"),
                    "splits_manifest_sha256": report["splits_manifest_sha256"],
                }
            )
            for group, values in params.items():
                mlflow.log_params({f"{group}.{k}": str(v) for k, v in values.items()})
            for mode in ("end_to_end", "gold_entities"):
                block = report[mode]
                mlflow.log_metrics(
                    {
                        f"{mode}.entity_f1": block["entities"]["micro"]["f1"],
                        f"{mode}.relation_f1": block["relations"]["micro"]["f1"],
                        f"{mode}.quantity_attachment": block["quantity_attachment"]["accuracy"],
                        f"{mode}.complete_steps": block["complete_steps"]["exact_match"],
                    }
                )
            mlflow.log_artifact(str(path))
        print(f"{system}: logged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
