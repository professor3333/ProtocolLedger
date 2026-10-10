"""Experiment tracking: a thin MLflow wrapper and a no-op stand-in for tests."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol


class Tracker(Protocol):
    def log_params(self, params: Mapping[str, Any]) -> None: ...
    def log_metrics(self, metrics: Mapping[str, float], step: int) -> None: ...
    def log_artifact(self, path: Path) -> None: ...
    def end(self, status: str = "FINISHED") -> None: ...


class NullTracker:
    def log_params(self, params: Mapping[str, Any]) -> None:
        pass

    def log_metrics(self, metrics: Mapping[str, float], step: int) -> None:
        pass

    def log_artifact(self, path: Path) -> None:
        pass

    def end(self, status: str = "FINISHED") -> None:
        pass


def _flatten(params: Mapping[str, Any], prefix: str = "") -> dict[str, str]:
    flat: dict[str, str] = {}
    for key, value in params.items():
        name = f"{prefix}{key}"
        if isinstance(value, Mapping):
            flat.update(_flatten(value, f"{name}."))
        else:
            flat[name] = str(value)[:500]
    return flat


class MLflowTracker:
    """Logs to a local MLflow file store (``mlruns/``); view with ``mlflow ui``.

    The file store is used deliberately even though MLflow 3 has put it in maintenance
    mode: every Kaggle session writes its own ``mlruns/``, and file stores merge by
    copying run directories, which separate SQLite databases do not.
    """

    def __init__(
        self,
        store: Path,
        experiment: str,
        run_name: str,
        tags: Mapping[str, str],
        run_id: str | None = None,
    ) -> None:
        os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
        os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
        import mlflow

        self._mlflow = mlflow
        mlflow.set_tracking_uri(store.resolve().as_uri())
        mlflow.set_experiment(experiment)
        self.run = mlflow.start_run(run_id=run_id, run_name=None if run_id else run_name)
        mlflow.set_tags(dict(tags))

    @property
    def run_id(self) -> str:
        return str(self.run.info.run_id)

    def log_params(self, params: Mapping[str, Any]) -> None:
        self._mlflow.log_params(_flatten(params))

    def log_metrics(self, metrics: Mapping[str, float], step: int) -> None:
        self._mlflow.log_metrics(dict(metrics), step=step)

    def log_artifact(self, path: Path) -> None:
        self._mlflow.log_artifact(str(path))

    def end(self, status: str = "FINISHED") -> None:
        self._mlflow.end_run(status=status)
