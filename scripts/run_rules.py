"""Fit the rule-based baseline on train, select its thresholds on dev, write reports.

    uv run python scripts/run_rules.py

Writes the fitted model to artifacts/rules/ (not committed) and the dev reports to
reports/baselines/ (committed). The test split is never touched.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

from protocolledger.baselines.rules import RULES_VERSION, RulesConfig, RulesModel
from protocolledger.data.splits import load_split
from protocolledger.eval.scorer import evaluate, render_markdown

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "rules"
REPORTS = ROOT / "reports" / "baselines"

GRID = {
    "lexicon_min_count": [1, 2],
    "lexicon_min_precision": [0.3, 0.5, 0.7],
    "attach_min_rate": [0.3, 0.5],
}


def git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main() -> int:
    train, dev = load_split(ROOT, "train"), load_split(ROOT, "dev")

    grid_results: list[dict[str, Any]] = []
    for values in itertools.product(*GRID.values()):
        config = RulesConfig(**dict(zip(GRID, values, strict=True)))
        model = RulesModel.fit(train, config)
        report = evaluate(dev, [model.predict(d) for d in dev], resamples=1)
        grid_results.append(
            {
                "config": asdict(config),
                "dev_entity_f1": report["entities"]["micro"]["f1"],
                "dev_relation_f1": report["relations"]["micro"]["f1"],
            }
        )
        point = dict(zip(GRID, values, strict=True))
        print(f"{point}: rel F1 {grid_results[-1]['dev_relation_f1']}")
    best = max(grid_results, key=lambda r: (r["dev_relation_f1"], r["dev_entity_f1"]))
    config = RulesConfig(**best["config"])
    model = RulesModel.fit(train, config)

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    model_json = json.dumps(model.to_json(), ensure_ascii=False, indent=1).encode("utf-8")
    (ARTIFACTS / "model.json").write_bytes(model_json)

    splits_sha = hashlib.sha256((ROOT / "data/manifests/splits.json").read_bytes()).hexdigest()
    REPORTS.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {
        "system": "rules",
        "rules_version": RULES_VERSION,
        "code_commit": git_commit(),
        "splits_manifest_sha256": splits_sha,
        "model_sha256": hashlib.sha256(model_json).hexdigest(),
        "selection": {"metric": "dev end-to-end relation micro-F1", "grid": grid_results},
        "config": asdict(config),
        "fitted": {
            "units": len(model.units),
            "lexicon_entries": len(model.lexicon),
            "attachment_rules": len(model.attachment),
        },
    }
    markdown = ["# Rule-based baseline: dev results", ""]
    for mode, gold_entities in (("end_to_end", False), ("gold_entities", True)):
        preds = [model.predict(d, gold_entities=gold_entities) for d in dev]
        report = evaluate(dev, preds)
        summary[mode] = report
        title = "End-to-end" if not gold_entities else "Relations given gold entities"
        markdown.append(render_markdown(report, title))
        with (ARTIFACTS / f"dev-{mode}.jsonl").open("w", encoding="utf-8") as fh:
            for p in preds:
                fh.write(json.dumps(p) + "\n")
    (REPORTS / "rules-dev.json").write_text(json.dumps(summary, indent=1) + "\n", "utf-8")
    (REPORTS / "rules-dev.md").write_text("\n".join(markdown), "utf-8")
    e2e = summary["end_to_end"]
    print(
        f"selected {asdict(config)}\n"
        f"dev end-to-end: entity F1 {e2e['entities']['micro']['f1']}, "
        f"relation F1 {e2e['relations']['micro']['f1']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
