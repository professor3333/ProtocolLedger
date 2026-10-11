"""Retrain the CRF + logistic-regression model with a curated correction batch.

    uv run python scripts/train_candidate.py --batch data/corrections/batch-<timestamp>

Steps, each of which can refuse:
1. apply curation.json: only documents a person included, each with a reason;
2. leakage check: an included document that duplicates a dev or test protocol is refused;
3. retrain on train + included documents with the configuration selected on dev;
4. evaluate on dev with the shared scorer; refuse if end-to-end relation F1 drops more
   than --max-drop points below the live model's dev report;
5. write a candidate bundle under artifacts/bundles/ and a report under
   reports/candidates/ (no protocol text). Activate it with scripts/release.py, which
   smoke-tests and keeps rollback.

The locked test split is not used: it has already been evaluated once.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from protocolledger.baselines.crf_entities import CRFConfig, CRFTagger
from protocolledger.baselines.logreg_relations import LogRegConfig, LogRegRelations
from protocolledger.data.review_batch import BatchError, apply_curation, batch_sha256, leakage
from protocolledger.data.splits import load_split
from protocolledger.eval.scorer import evaluate
from protocolledger.serve.bundle import write_traditional_bundle

ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / "reports" / "baselines" / "crf-logreg-dev.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--max-drop", type=float, default=0.5, help="points of dev relation F1")
    args = parser.parse_args(argv)

    docs = [
        json.loads(line)
        for line in (args.batch / "documents.jsonl").read_text().splitlines()
        if line.strip()
    ]
    curation = json.loads((args.batch / "curation.json").read_text())
    try:
        included = apply_curation(docs, curation)
    except BatchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    train, dev, test = load_split(ROOT, "train"), load_split(ROOT, "dev"), load_split(ROOT, "test")
    leaks = leakage(included, [*dev, *test])
    if leaks:
        for leak in leaks:
            print(
                f"refused: {leak['candidate']} duplicates {leak['protected']} "
                f"(jaccard {leak['jaccard']})",
                file=sys.stderr,
            )
        return 1

    selection = json.loads(SELECTION.read_text())
    crf_cfg = {k: v for k, v in selection["crf_config"].items() if k != "crf_version"}
    lr_cfg = {k: v for k, v in selection["logreg_config"].items() if k != "logreg_version"}
    training = [*train, *included]
    tagger = CRFTagger.fit(training, CRFConfig(**crf_cfg))
    relations = LogRegRelations.fit(training, LogRegConfig(**lr_cfg))

    preds = []
    for d in dev:
        entities = tagger.predict_entities(d["text"])
        preds.append(
            {
                "doc_id": d["doc_id"],
                "entities": entities,
                "relations": relations.predict_relations(d["text"], entities),
            }
        )
    report = evaluate(dev, preds)
    live = selection["end_to_end"]["relations"]["micro"]["f1"]
    got = report["relations"]["micro"]["f1"]
    drop = round((live - got) * 100, 2)
    batch_hash = batch_sha256(included)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()
    summary = {
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "code_commit": commit,
        "batch_sha256": batch_hash,
        "included_documents": len(included),
        "included": [{"doc_id": d["doc_id"], **d["provenance"]} for d in included],
        "dev_entity_f1": report["entities"]["micro"]["f1"],
        "dev_relation_f1": got,
        "live_dev_relation_f1": live,
        "relation_f1_drop_points": drop,
        "max_drop_points": args.max_drop,
        "passes_gate": drop <= args.max_drop,
    }
    out = ROOT / "reports" / "candidates"
    out.mkdir(parents=True, exist_ok=True)
    name = f"crf-logreg-candidate-{batch_hash[:10]}"
    if not summary["passes_gate"]:
        (out / f"{name}-rejected.json").write_text(json.dumps(summary, indent=1) + "\n")
        print(
            f"rejected: dev relation F1 {got} is {drop} points below the live {live}",
            file=sys.stderr,
        )
        return 1
    bundle = write_traditional_bundle(
        ROOT / "artifacts" / "bundles" / name,
        tagger,
        relations,
        name,
        {
            "training": {
                "base": "train split",
                "correction_batch_sha256": batch_hash,
                "included_documents": len(included),
                "code_commit": commit,
            },
            "evaluation": {
                "split": "dev",
                "entity_f1": summary["dev_entity_f1"],
                "relation_f1_end_to_end": got,
            },
        },
    )
    summary["bundle"] = bundle.relative_to(ROOT).as_posix()
    summary["bundle_sha256"] = hashlib.sha256((bundle / "bundle.json").read_bytes()).hexdigest()
    (out / f"{name}.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(f"candidate {name}: dev relation F1 {got} (live {live}); bundle {summary['bundle']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
