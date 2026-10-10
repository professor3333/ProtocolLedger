"""Build a servable model bundle for the traditional baseline.

    uv run python scripts/build_bundle.py

Refits CRF + logistic regression on train with the settings selected in
reports/baselines/crf-logreg-dev.json, then refuses to write the bundle unless the CRF
model hash and the dev end-to-end scores reproduce that committed report exactly.
Writes artifacts/bundles/<model_version>/ (not committed).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from protocolledger.baselines.crf_entities import CRFConfig, CRFTagger
from protocolledger.baselines.logreg_relations import LogRegConfig, LogRegRelations
from protocolledger.data.splits import load_split
from protocolledger.eval.scorer import evaluate
from protocolledger.serve.bundle import load_bundle, write_traditional_bundle

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "baselines" / "crf-logreg-dev.json"


def main() -> int:
    report_bytes = REPORT.read_bytes()
    report = json.loads(report_bytes)
    crf_cfg = {k: v for k, v in report["crf_config"].items() if k != "crf_version"}
    lr_cfg = {k: v for k, v in report["logreg_config"].items() if k != "logreg_version"}
    train, dev = load_split(ROOT, "train"), load_split(ROOT, "dev")

    tagger = CRFTagger.fit(train, CRFConfig(**crf_cfg))
    crf_sha = hashlib.sha256(tagger.model_bytes).hexdigest()
    if crf_sha != report["crf_model_sha256"]:
        print("error: refit CRF does not match the reported model", file=sys.stderr)
        return 1
    relations = LogRegRelations.fit(train, LogRegConfig(**lr_cfg))

    model_version = f"crf-logreg-{crf_sha[:10]}"
    bundle_dir = ROOT / "artifacts" / "bundles" / model_version
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()
    e2e = report["end_to_end"]
    provenance = {
        "training": {
            "split": "train",
            "splits_manifest_sha256": report["splits_manifest_sha256"],
            "selection_report": REPORT.relative_to(ROOT).as_posix(),
            "selection_report_sha256": hashlib.sha256(report_bytes).hexdigest(),
            "code_commit": commit or "unknown",
        },
        "evaluation": {
            "split": "dev",
            "entity_f1": e2e["entities"]["micro"]["f1"],
            "relation_f1_end_to_end": e2e["relations"]["micro"]["f1"],
        },
    }
    write_traditional_bundle(bundle_dir, tagger, relations, model_version, provenance)

    loaded = load_bundle(bundle_dir)
    preds = []
    for d in dev:
        ents = loaded.extractor.predict_entities(d["text"])
        rels = loaded.extractor.predict_relations(d["text"], ents)
        preds.append({"doc_id": d["doc_id"], "entities": ents, "relations": rels})
    check = evaluate(dev, preds, resamples=1)
    got = (check["entities"]["micro"]["f1"], check["relations"]["micro"]["f1"])
    want = (e2e["entities"]["micro"]["f1"], e2e["relations"]["micro"]["f1"])
    if got != want:
        print(f"error: bundle scores {got} differ from report {want}", file=sys.stderr)
        return 1
    print(f"wrote {bundle_dir.relative_to(ROOT)} (dev entity F1 {got[0]}, relation F1 {got[1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
