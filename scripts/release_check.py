"""Check the release gates for a span-relation bundle (run on every version tag).

    uv run python scripts/release_check.py --bundle artifacts/bundles/<model_version> \\
        --machine "GitHub Actions ubuntu-latest, 4 vCPU" --out artifacts/release

Needs the dev split (scripts/acquire.py, convert.py, build_splits.py). Checks each gate in
configs/release_gates.json:
1. accuracy: CPU dev entity and end-to-end relation F1 reproduce the evaluation recorded
   in the bundle's bundle.json;
2. calibration: precision at 30% coverage and ECE after cross-fitted isotonic calibration
   reproduce the committed calibration report;
3. performance: p95 latency and peak resident memory of in-process extraction on dev
   protocols of up to 500 words, on this machine.
ONNX / INT8 parity is not gated: the served runtime is PyTorch FP32. Dev only; no test
split is read. Writes <out>/release-manifest.json and <out>/release-notes.md and exits 1
if any gate fails.
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from optimize_bundle import texts  # scripts/ is on sys.path

ROOT = Path(__file__).resolve().parents[1]


def gate(name: str, measured: float, limit: str, passed: bool) -> dict[str, Any]:
    return {"gate": name, "measured": measured, "limit": limit, "passed": passed}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--machine", required=True, help="describe the hardware honestly")
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts" / "release")
    parser.add_argument("--tag", default=os.environ.get("GITHUB_REF_NAME", "untagged"))
    parser.add_argument("--threads", type=int, default=os.cpu_count() or 1)
    args = parser.parse_args(argv)
    gates = json.loads((ROOT / "configs" / "release_gates.json").read_text("utf-8"))

    import torch

    torch.set_num_threads(args.threads)
    os.environ["PROTOCOLLEDGER_THREADS"] = str(args.threads)
    from protocolledger.data.splits import load_split
    from protocolledger.eval.confidence import confidence_report
    from protocolledger.eval.scorer import evaluate
    from protocolledger.serve.bundle import load_bundle

    loaded = load_bundle(args.bundle)  # verifies every file's hash
    recorded = json.loads((args.bundle / "bundle.json").read_text("utf-8"))["evaluation"]
    dev = load_split(ROOT, "dev")
    started = time.time()
    preds = []
    for doc in dev:
        entities, relations = loaded.extractor.extract(doc["text"])
        preds.append({"doc_id": doc["doc_id"], "entities": entities, "relations": relations})
    dev_seconds = time.time() - started
    report = evaluate(dev, preds, resamples=1)
    entity_f1 = report["entities"]["micro"]["f1"]
    relation_f1 = report["relations"]["micro"]["f1"]

    acc = gates["accuracy"]
    results = [
        gate(
            "dev entity F1 reproduces bundle.json",
            entity_f1,
            f"{recorded['entity_f1']} ± {acc['entity_f1_max_abs_diff']}",
            abs(entity_f1 - recorded["entity_f1"]) <= acc["entity_f1_max_abs_diff"],
        ),
        gate(
            "dev end-to-end relation F1 reproduces bundle.json",
            relation_f1,
            f"{recorded['relation_f1_end_to_end']} ± {acc['relation_f1_max_abs_diff']}",
            abs(relation_f1 - recorded["relation_f1_end_to_end"])
            <= acc["relation_f1_max_abs_diff"],
        ),
    ]

    cal = gates["calibration"]
    committed = json.loads((ROOT / cal["report"]).read_text("utf-8"))
    conf = confidence_report(dev, preds, joint=True)
    p30 = conf["target"]["precision_at_30pct_coverage"]["precision"]
    p30_ref = committed["target"]["precision_at_30pct_coverage"]["precision"]
    ece_after = conf["calibration"]["after"]["ece"]
    ece_ref = committed["calibration"]["after"]["ece"]
    results += [
        gate(
            "precision at 30% coverage reproduces the calibration report",
            p30,
            f"{p30_ref} ± {cal['precision_at_30pct_coverage_max_abs_diff']}",
            abs(p30 - p30_ref) <= cal["precision_at_30pct_coverage_max_abs_diff"],
        ),
        gate(
            "ECE after isotonic calibration",
            ece_after,
            f"≤ {ece_ref} + {cal['ece_after_max_increase']}",
            ece_after <= ece_ref + cal["ece_after_max_increase"],
        ),
    ]

    perf = gates["performance"]
    bodies = texts(perf["max_words"])
    for text in bodies[:5]:
        loaded.extractor.extract(text)  # warm-up
    latencies = []
    for i in range(perf["requests"]):
        t0 = time.perf_counter()
        loaded.extractor.extract(bodies[i % len(bodies)])
        latencies.append(time.perf_counter() - t0)
    latencies.sort()
    p50 = round(latencies[len(latencies) // 2], 4)
    p95 = round(latencies[int(0.95 * len(latencies))], 4)
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_mib = round(peak / 1024 / 1024 if sys.platform == "darwin" else peak / 1024, 1)
    results += [
        gate(
            f"p95 latency, ≤ {perf['max_words']}-word dev protocols (s)",
            p95,
            f"≤ {perf['latency_p95_max_s']}",
            p95 <= perf["latency_p95_max_s"],
        ),
        gate(
            "peak resident memory (MiB)",
            peak_mib,
            f"≤ {perf['peak_rss_max_mib']}",
            peak_mib <= perf["peak_rss_max_mib"],
        ),
    ]

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    passed = all(r["passed"] for r in results)
    manifest = {
        "tag": args.tag,
        "code_commit": commit,
        "passed": passed,
        "machine": args.machine,
        "threads": args.threads,
        **{k: v for k, v in loaded.version_info().items() if k != "evaluation"},
        "dev": {
            "documents": len(dev),
            "seconds": round(dev_seconds, 1),
            "entity_f1": entity_f1,
            "relation_f1_end_to_end": relation_f1,
            "precision_at_30pct_coverage": p30,
            "coverage_at_95pct_precision": conf["target"]["coverage_at_95pct_precision"][
                "coverage"
            ],
            "ece_before": conf["calibration"]["before"]["ece"],
            "ece_after": ece_after,
        },
        "performance": {
            "requests": perf["requests"],
            "latency_p50_s": p50,
            "latency_p95_s": p95,
            "peak_rss_mib": peak_mib,
        },
        "onnx_int8_parity": "not gated: the served runtime is PyTorch FP32",
        "gates": results,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "release-manifest.json").write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", "utf-8"
    )
    lines = [
        f"Model `{manifest['model_version']}` (bundle.json SHA-256 "
        f"`{manifest['bundle_sha256']}`), runtime {manifest['runtime']}, code "
        f"`{commit[:10]}`. Gates checked on {args.machine}, dev split only "
        f"({len(dev)} protocols); configuration: `configs/release_gates.json`.",
        "",
        "| Gate | Measured | Limit | Passed |",
        "|---|---:|---|---|",
        *(
            f"| {r['gate']} | {r['measured']} | {r['limit']} | "
            f"{'yes' if r['passed'] else '**no**'} |"
            for r in results
        ),
        "",
        f"p50 latency {p50} s over {perf['requests']} sequential requests. "
        "ONNX / INT8 parity is not gated: the served runtime is PyTorch FP32.",
    ]
    (args.out / "release-notes.md").write_text("\n".join(lines) + "\n", "utf-8")
    print("\n".join(lines))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
