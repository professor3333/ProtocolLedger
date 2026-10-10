"""Traditional baseline: CRF entities + logistic-regression relations.

    uv run python scripts/run_traditional.py

Selection, on dev only:
1. CRF regularization (c1, c2) by dev strict entity micro-F1.
2. Logistic-regression C by dev **end-to-end** relation micro-F1, i.e. with the selected
   CRF's predicted entities as endpoints (relations are trained on gold entities).

Writes models to artifacts/traditional/ (not committed) and reports to
reports/baselines/ (committed). The test split is never touched.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import pickle
import subprocess
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from protocolledger.baselines.crf_entities import CRFConfig, CRFTagger, encode_stats
from protocolledger.baselines.logreg_relations import LogRegConfig, LogRegRelations
from protocolledger.data.splits import load_split
from protocolledger.eval.scorer import evaluate, render_markdown

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "traditional"
REPORTS = ROOT / "reports" / "baselines"
CRF_GRID = {"c1": [0.05, 0.2], "c2": [0.01, 0.1]}
LOGREG_GRID = {"C": [0.1, 0.3, 1.0, 3.0]}


def git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def gold_entities(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return [{k: e[k] for k in ("id", "label", "start", "end")} for e in doc["entities"]]


def main() -> int:
    train, dev = load_split(ROOT, "train"), load_split(ROOT, "dev")
    empty = {"relations": []}

    crf_grid: list[dict[str, Any]] = []
    best_crf: tuple[float, CRFTagger] | None = None
    for values in itertools.product(*CRF_GRID.values()):
        config = CRFConfig(**dict(zip(CRF_GRID, values, strict=True)))
        started = time.time()
        tagger = CRFTagger.fit(train, config)
        preds = [
            {"doc_id": d["doc_id"], "entities": tagger.predict_entities(d["text"]), **empty}
            for d in dev
        ]
        f1 = evaluate(dev, preds, resamples=1)["entities"]["micro"]["f1"]
        crf_grid.append({"config": asdict(config), "dev_entity_f1": f1})
        print(f"CRF {asdict(config)}: dev entity F1 {f1} ({time.time() - started:.0f}s)")
        if best_crf is None or f1 > best_crf[0]:
            best_crf = (f1, tagger)
    assert best_crf is not None
    tagger = best_crf[1]
    dev_entities = {d["doc_id"]: tagger.predict_entities(d["text"]) for d in dev}

    logreg_grid: list[dict[str, Any]] = []
    best_lr: tuple[float, LogRegRelations] | None = None
    for values in itertools.product(*LOGREG_GRID.values()):
        lr_config = LogRegConfig(**dict(zip(LOGREG_GRID, values, strict=True)))
        started = time.time()
        relations = LogRegRelations.fit(train, lr_config)
        preds = [
            {
                "doc_id": d["doc_id"],
                "entities": dev_entities[d["doc_id"]],
                "relations": relations.predict_relations(d["text"], dev_entities[d["doc_id"]]),
            }
            for d in dev
        ]
        f1 = evaluate(dev, preds, resamples=1)["relations"]["micro"]["f1"]
        logreg_grid.append({"config": asdict(lr_config), "dev_end_to_end_relation_f1": f1})
        print(
            f"LogReg {asdict(lr_config)}: dev e2e relation F1 {f1} ({time.time() - started:.0f}s)"
        )
        if best_lr is None or f1 > best_lr[0]:
            best_lr = (f1, relations)
    assert best_lr is not None
    relations = best_lr[1]

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "crf.crfsuite").write_bytes(tagger.model_bytes)
    lr_bytes = pickle.dumps((relations.vectorizer, relations.classifier, relations.type_pairs))
    (ARTIFACTS / "logreg.pkl").write_bytes(lr_bytes)

    splits_sha = hashlib.sha256((ROOT / "data/manifests/splits.json").read_bytes()).hexdigest()
    train_enc, dev_enc = encode_stats(train), encode_stats(dev)
    dev_reach = relations.reachability(dev)
    summary: dict[str, Any] = {
        "system": "crf+logreg",
        "code_commit": git_commit(),
        "splits_manifest_sha256": splits_sha,
        "crf_model_sha256": hashlib.sha256(tagger.model_bytes).hexdigest(),
        "selection": {
            "crf": {"metric": "dev strict entity micro-F1", "grid": crf_grid},
            "logreg": {"metric": "dev end-to-end relation micro-F1", "grid": logreg_grid},
        },
        "crf_config": tagger.config_json(),
        "logreg_config": relations.config_json(),
        "representability": {
            "bio_unrepresentable_entities": {
                "train": {"misaligned": train_enc.misaligned, "overlapping": train_enc.overlapping},
                "dev": {"misaligned": dev_enc.misaligned, "overlapping": dev_enc.overlapping},
                "note": "Counted as misses in evaluation; mostly words glued by table flattening.",
            },
            "relation_candidates": {
                "train_candidates": relations.train_stats.candidates,
                "train_label_counts": dict(relations.train_stats.by_label),
                "dev_gold": dev_reach.gold,
                "dev_cross_step": dev_reach.cross_step,
                "dev_unseen_type_pair": dev_reach.unseen_type_pair,
                "dev_multilabel_extra": dev_reach.multilabel_extra,
            },
        },
    }
    markdown = ["# CRF + logistic regression baseline: dev results", ""]
    for mode in ("end_to_end", "gold_entities"):
        preds = []
        for d in dev:
            ents = dev_entities[d["doc_id"]] if mode == "end_to_end" else gold_entities(d)
            rels = relations.predict_relations(d["text"], ents)
            preds.append({"doc_id": d["doc_id"], "entities": ents, "relations": rels})
        report = evaluate(dev, preds)
        summary[mode] = report
        title = "End-to-end" if mode == "end_to_end" else "Relations given gold entities"
        markdown.append(render_markdown(report, title))
        with (ARTIFACTS / f"dev-{mode}.jsonl").open("w", encoding="utf-8") as fh:
            for p in preds:
                fh.write(json.dumps(p) + "\n")
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "crf-logreg-dev.json").write_text(json.dumps(summary, indent=1) + "\n", "utf-8")
    (REPORTS / "crf-logreg-dev.md").write_text("\n".join(markdown), "utf-8")
    e2e = summary["end_to_end"]
    print(
        f"dev end-to-end: entity F1 {e2e['entities']['micro']['f1']}, "
        f"relation F1 {e2e['relations']['micro']['f1']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
