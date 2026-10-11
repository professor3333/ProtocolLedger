"""The single evaluation of the locked test split, against the frozen targets.

    uv run --extra neural python scripts/locked_test.py

Refuses to run unless docs/targets.md is committed at HEAD, the tree is clean, HEAD is on
GitHub, and no locked-test report exists yet: the test split is evaluated once. Scores
the declared releases from docs/targets.md (rules, CRF + logistic regression, SciBERT)
and writes reports/test/locked-test.{json,md}.
"""

from __future__ import annotations

import hashlib
import json
import random
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import torch

from protocolledger.baselines.rules import RulesModel
from protocolledger.data.splits import load_split
from protocolledger.eval.confidence import (
    ece,
    max_coverage_at_precision,
    precision_at_coverage,
    scored_relations,
)
from protocolledger.eval.errors import analyze
from protocolledger.eval.robustness import perturb
from protocolledger.eval.scorer import evaluate
from protocolledger.neural.predict import predict_documents
from protocolledger.serve.bundle import load_bundle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "test"
RULES_MODEL = ROOT / "artifacts" / "rules" / "model.json"
CRF_BUNDLE = ROOT / "artifacts" / "bundles" / "crf-logreg-4a9d8cc549"
SCIBERT_BUNDLE = ROOT / "artifacts" / "bundles" / "scibert-uniform-negatives-s21-7dc7a1893e"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def preconditions() -> str:
    if (OUT / "locked-test.json").exists():
        raise SystemExit("error: the locked test split has already been evaluated")
    if git("status", "--porcelain", "--untracked-files=no"):
        raise SystemExit("error: commit your changes first")
    commit = git("rev-parse", "HEAD")
    if not git("ls-tree", "--name-only", "HEAD", "docs/targets.md"):
        raise SystemExit("error: docs/targets.md is not committed")
    git("fetch", "--quiet", "origin")
    if not git("branch", "-r", "--contains", commit):
        raise SystemExit("error: HEAD is not on GitHub")
    return commit


def summary(report: dict[str, Any]) -> dict[str, Any]:
    e = report["entities"]["micro"]
    r = report["relations"]["micro"]
    return {
        "entity_f1": e["f1"],
        "entity_f1_ci95": e["f1_ci95"],
        "relation_f1": r["f1"],
        "relation_f1_ci95": r["f1_ci95"],
        "relation_precision": r["precision"],
        "relation_recall": r["recall"],
        "entity_macro_f1": report["entities"]["macro_f1"],
        "relation_macro_f1": report["relations"]["macro_f1"],
        "quantity_attachment": report["quantity_attachment"]["accuracy"],
        "complete_steps": report["complete_steps"]["exact_match"],
    }


def gold_view(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return [{k: e[k] for k in ("id", "label", "start", "end")} for e in doc["entities"]]


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--rehearse-on-dev",
        type=Path,
        default=None,
        metavar="OUT_DIR",
        help="run every step on dev into OUT_DIR, without touching test",
    )
    args = parser.parse_args(argv)
    global OUT
    if args.rehearse_on_dev:
        commit, OUT, split, prefix = "rehearsal", args.rehearse_on_dev, "dev", "dev_data/"
        split_label = "dev (REHEARSAL ONLY: not a test result)"
    else:
        commit, split, prefix = preconditions(), "test", "test_data_2020/"
        split_label = "cleaned test_data_2020 (111 protocols)"
    test, train = load_split(ROOT, split), load_split(ROOT, "train")
    rules_report = json.loads((ROOT / "reports/baselines/rules-dev.json").read_text())
    if hashlib.sha256(RULES_MODEL.read_bytes()).hexdigest() != rules_report["model_sha256"]:
        raise SystemExit("error: rules model does not match its dev report")

    systems: dict[str, Any] = {}
    preds: dict[str, list[dict[str, Any]]] = {}

    rules = RulesModel.from_json(json.loads(RULES_MODEL.read_text()))
    preds["rules"] = [rules.predict(d) for d in test]
    rules_gold = [rules.predict(d, gold_entities=True) for d in test]
    systems["rules"] = {
        "release": "rules (fit on train)",
        "end_to_end": evaluate(test, preds["rules"]),
        "gold_entities": evaluate(test, rules_gold),
    }
    print("rules done", flush=True)

    crf = load_bundle(CRF_BUNDLE)
    preds["crf-logreg"], crf_gold = [], []
    for d in test:
        entities, relations = crf.extractor.extract(d["text"])
        preds["crf-logreg"].append(
            {"doc_id": d["doc_id"], "entities": entities, "relations": relations}
        )
        gold = gold_view(d)
        crf_gold.append(
            {
                "doc_id": d["doc_id"],
                "entities": gold,
                "relations": crf.extractor.relations.predict_relations(d["text"], gold),
            }
        )  # type: ignore[attr-defined]
    systems["crf-logreg"] = {
        "release": crf.model_version,
        "end_to_end": evaluate(test, preds["crf-logreg"]),
        "gold_entities": evaluate(test, crf_gold),
    }
    print("crf-logreg done", flush=True)

    sci = load_bundle(SCIBERT_BUNDLE)
    ex = sci.extractor
    preds["scibert"] = predict_documents(
        ex.model,
        ex.tokenizer,
        test,
        ex.type_pairs,  # type: ignore[attr-defined]
        torch.device("cpu"),
    )  # type: ignore[attr-defined]
    sci_gold = predict_documents(
        ex.model,
        ex.tokenizer,
        test,
        ex.type_pairs,  # type: ignore[attr-defined]
        torch.device("cpu"),
        gold_entities=True,
    )
    rng = random.Random(13)
    perturbed = [{**d, "text": perturb(d["text"], rng)} for d in test]
    sci_perturbed = predict_documents(
        ex.model,
        ex.tokenizer,
        perturbed,
        ex.type_pairs,  # type: ignore[attr-defined]
        torch.device("cpu"),
    )
    systems["scibert"] = {
        "release": sci.model_version,
        "end_to_end": evaluate(test, preds["scibert"]),
        "gold_entities": evaluate(test, sci_gold),
        "perturbed": evaluate(test, sci_perturbed, resamples=1),
    }
    print("scibert done", flush=True)

    # Error slices (names from train only; template siblings from splits.json).
    manifest = json.loads((ROOT / "data/manifests/splits.json").read_text())
    siblings = {k for k in manifest["template_siblings"] if k.startswith(prefix)}
    seen = {
        d["text"][e["start"] : e["end"]].casefold()
        for d in train
        for e in d["entities"]
        if e["label"] == "Reagent"
    }
    test_names = {
        d["text"][e["start"] : e["end"]].casefold()
        for d in test
        for e in d["entities"]
        if e["label"] == "Reagent"
    }
    errors = {
        name: analyze(test, preds[name], unseen_names=test_names - seen, sibling_docs=siblings)
        for name in ("crf-logreg", "scibert")
    }

    # Confidence: joint scores; calibrator fitted on dev only.
    items, _ = scored_relations(test, preds["scibert"], joint=True)
    calibrator = json.loads(
        (ROOT / "reports/calibration/scibert-uniform-s21-joint-dev.json").read_text()
    )["calibrator"]
    raw = [s.score for s in items]
    calibrated = list(np.interp(raw, calibrator["x"], calibrator["y"]))
    correct = [s.correct for s in items]
    confidence = {
        "score": "P(relation) x P(head) x P(tail)",
        "precision_at_30pct_coverage": precision_at_coverage(items, 0.30),
        "coverage_at_95pct_precision": max_coverage_at_precision(items, 0.95),
        "ece_raw": ece(raw, correct)["ece"],
        "ece_dev_calibrated": ece([float(c) for c in calibrated], correct)["ece"],
    }

    s = {name: summary(v["end_to_end"]) for name, v in systems.items()}
    sci_rel, crf_rel = s["scibert"]["relation_f1"], s["crf-logreg"]["relation_f1"]
    drop = round((sci_rel - summary(systems["scibert"]["perturbed"])["relation_f1"]) * 100, 2)
    targets = [
        (
            "Strict entity micro-F1 ≥ 0.75",
            f"{s['scibert']['entity_f1']:.3f}",
            s["scibert"]["entity_f1"] >= 0.75,
        ),
        ("End-to-end relation micro-F1 ≥ 0.65", f"{sci_rel:.3f}", sci_rel >= 0.65),
        (
            "≥ 5 points above the traditional baseline",
            f"+{(sci_rel - crf_rel) * 100:.1f} points",
            sci_rel - crf_rel >= 0.05,
        ),
        (
            "≥ 95% relation precision at ≥ 30% coverage",
            f"{confidence['coverage_at_95pct_precision']['coverage']:.1%} coverage at 95% "
            "precision",
            confidence["coverage_at_95pct_precision"]["coverage"] >= 0.30,
        ),
        ("≤ 5-point F1 loss under perturbations", f"{drop:+.2f} points", drop <= 5.0),
    ]
    result = {
        "evaluated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "code_commit": commit,
        "targets_file_sha256": hashlib.sha256((ROOT / "docs/targets.md").read_bytes()).hexdigest(),
        "split": split_label,
        "systems": {
            name: {
                "release": v["release"],
                **summary(v["end_to_end"]),
                "relation_f1_gold_entities": v["gold_entities"]["relations"]["micro"]["f1"],
            }
            for name, v in systems.items()
        },
        "scibert_per_label": systems["scibert"]["end_to_end"]["relations"]["per_label"],
        "scibert_perturbed_relation_f1": summary(systems["scibert"]["perturbed"])["relation_f1"],
        "error_slices": {
            name: {"relation_categories": r["relations"]["categories"], **r["slices"]}
            for name, r in errors.items()
        },
        "confidence": confidence,
        "targets": [{"target": t, "result": v, "met": m} for t, v, m in targets],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "locked-test.json").write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")

    lines = [
        "# Locked test evaluation",
        "",
        f"Evaluated once on {result['evaluated_at']} at commit `{commit[:10]}`, after the targets "
        f"were frozen in [docs/targets.md](../../docs/targets.md). Split: {split_label}. "
        "95% CIs: document-level bootstrap.",
        "",
        "| System | Entity F1 | Relation F1, gold entities | **Relation F1, end-to-end** "
        "| Quantity attachment | Complete steps |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, label in (
        ("rules", "Rules"),
        ("crf-logreg", "CRF + logistic regression"),
        ("scibert", "**SciBERT span-relation**"),
    ):
        v = result["systems"][name]
        ent_ci = v["entity_f1_ci95"]
        lines.append(
            f"| {label} | {v['entity_f1']:.3f} [{ent_ci[0]:.3f}, {ent_ci[1]:.3f}] "
            f"| {v['relation_f1_gold_entities']:.3f} | **{v['relation_f1']:.3f}** "
            f"[{v['relation_f1_ci95'][0]:.3f}, {v['relation_f1_ci95'][1]:.3f}] "
            f"| {v['quantity_attachment']:.3f} | {v['complete_steps']:.3f} |"
        )
    lines += ["", "## Frozen targets", "", "| Target | Test result | Met |", "|---|---|---|"]
    lines += [f"| {t} | {v} | {'yes' if m else '**no**'} |" for t, v, m in targets]
    sl = result["error_slices"]
    names_crf, names_sci = sl["crf-logreg"]["reagent_names"], sl["scibert"]["reagent_names"]
    lines += [
        "",
        "## Slices",
        "",
        "| | CRF + LR | SciBERT |",
        "|---|---:|---:|",
        f"| Reagent recall, names unseen in train | {names_crf['unseen']['recall']:.3f} "
        f"| {names_sci['unseen']['recall']:.3f} |",
        f"| Reagent recall, names seen in train | {names_crf['seen']['recall']:.3f} "
        f"| {names_sci['seen']['recall']:.3f} |",
    ]
    for group in ("without", "with_template_sibling"):
        if group in sl["scibert"].get("template_siblings", {}):
            a = sl["crf-logreg"]["template_siblings"][group]
            b = sl["scibert"]["template_siblings"][group]
            label = (
                "with a template sibling" if group != "without" else "without a template sibling"
            )
            lines.append(
                f"| Relation recall, documents {label} ({b['gold_relations']} gold) "
                f"| {a['relation_recall']:.3f} | {b['relation_recall']:.3f} |"
            )
    c = confidence
    lines += [
        "",
        "## Confidence (SciBERT, joint score)",
        "",
        f"- Precision at 30% coverage: {c['precision_at_30pct_coverage']['precision']:.3f} "
        f"[{c['precision_at_30pct_coverage']['precision_ci95'][0]:.3f}, "
        f"{c['precision_at_30pct_coverage']['precision_ci95'][1]:.3f}]",
        f"- Coverage at 95% precision: {c['coverage_at_95pct_precision']['coverage']:.1%}",
        f"- Expected calibration error: raw {c['ece_raw']:.3f}, with the dev-fitted isotonic "
        f"calibrator {c['ece_dev_calibrated']:.3f}",
        "",
        "Not evaluated: value normalization against an independently checked set, and the "
        "user pilot (see docs/targets.md).",
        "",
    ]
    (OUT / "locked-test.md").write_text("\n".join(lines))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
