import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("kaggle_cli", ROOT / "scripts" / "kaggle.py")
assert spec and spec.loader
kaggle_cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kaggle_cli)


def test_rendered_job_is_valid_python_pinned_to_the_commit() -> None:
    runs = kaggle_cli.parse_runs(["scibert-lr5e-5:13", "bert-lr5e-5"])
    source = kaggle_cli.render_job("a" * 40, runs)
    compile(source, "job.py", "exec")
    payload = source.split('r"""', 1)[1].split('"""', 1)[0]
    job = json.loads(payload)
    assert job["commit"] == "a" * 40
    assert job["runs"] == [
        ["configs/neural/scibert-lr5e-5.json", 13],
        ["configs/neural/bert-lr5e-5.json", 13],
    ]
    assert "--no-mlflow" in source and "last.pt" in source


def test_unknown_config_is_rejected() -> None:
    with pytest.raises(SystemExit, match="no config"):
        kaggle_cli.parse_runs(["does-not-exist:1"])


def test_every_experiment_config_loads() -> None:
    from protocolledger.neural.config import NeuralConfig

    configs = sorted((ROOT / "configs" / "neural").glob("*.json"))
    assert configs
    for path in configs:
        NeuralConfig.load(path)
