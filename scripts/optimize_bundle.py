"""Compare inference runtimes for a span-relation bundle: accuracy, latency, memory.

    uv run --extra neural python scripts/optimize_bundle.py \\
        --bundle artifacts/bundles/<model_version> --threads 4

For torch-fp32 (the bundle itself), onnx-fp32 and onnx-int8 (derived bundles), measures
dev end-to-end F1 on CPU and, in a fresh process each, per-request latency on dev
protocols of up to 500 words and peak resident memory. Gates from the plan: at most a
1-point end-to-end relation F1 drop against torch-fp32 and p95 <= 3 s. Writes
reports/performance/<model_version>-runtimes.{json,md}. Dev only.
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

ROOT = Path(__file__).resolve().parents[1]
RUNTIMES = ("torch-fp32", "onnx-fp32", "onnx-int8")


def texts(max_words: int) -> list[str]:
    from protocolledger.data.splits import load_split

    out = []
    for doc in load_split(ROOT, "dev"):
        lines, words = [], 0
        for line in doc["text"].splitlines():
            if words + len(line.split()) > max_words:
                break
            lines.append(line)
            words += len(line.split())
        if lines:
            out.append("\n".join(lines) + "\n")
    return out


def measure(bundle: Path, threads: int, requests: int) -> dict[str, Any]:
    """Runs in a fresh process: accuracy on dev, then latency and peak RSS."""
    import torch

    torch.set_num_threads(threads)
    os.environ["PROTOCOLLEDGER_THREADS"] = str(threads)
    from protocolledger.data.splits import load_split
    from protocolledger.eval.scorer import evaluate
    from protocolledger.serve.bundle import load_bundle

    loaded = load_bundle(bundle)
    dev = load_split(ROOT, "dev")
    preds = []
    for doc in dev:
        entities, relations = loaded.extractor.extract(doc["text"])
        preds.append({"doc_id": doc["doc_id"], "entities": entities, "relations": relations})
    report = evaluate(dev, preds, resamples=1)
    bodies = texts(500)
    for text in bodies[:5]:
        loaded.extractor.extract(text)  # warm-up
    latencies = []
    for i in range(requests):
        started = time.perf_counter()
        loaded.extractor.extract(bodies[i % len(bodies)])
        latencies.append(time.perf_counter() - started)
    latencies.sort()
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_mib = peak / 1024 / 1024 if sys.platform == "darwin" else peak / 1024
    return {
        "model_version": loaded.model_version,
        "runtime": loaded.version_info()["runtime"],
        "entity_f1": report["entities"]["micro"]["f1"],
        "relation_f1": report["relations"]["micro"]["f1"],
        "latency_p50": round(latencies[len(latencies) // 2], 4),
        "latency_p95": round(latencies[int(0.95 * len(latencies))], 4),
        "requests": requests,
        "peak_rss_mib": round(peak_mib, 1),
        "bundle_mib": round(
            sum(p.stat().st_size for p in bundle.rglob("*") if p.is_file()) / 1024 / 1024, 1
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--machine", default="Apple M1 (8 GB), 4 inference threads")
    parser.add_argument("--measure-only", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.measure_only:
        print(json.dumps(measure(args.bundle, args.threads, args.requests)))
        return 0

    from protocolledger.serve.neural_bundle import derive_onnx_bundle

    base = args.bundle.resolve()
    version = json.loads((base / "bundle.json").read_text())["model_version"]
    results = []
    for runtime in RUNTIMES:
        bundle = base if runtime == "torch-fp32" else base.parent / f"{version}-{runtime}"
        if runtime != "torch-fp32" and not bundle.exists():
            derive_onnx_bundle(base, bundle, runtime)
        out = subprocess.run(
            [
                sys.executable,
                __file__,
                "--bundle",
                str(bundle),
                "--threads",
                str(args.threads),
                "--requests",
                str(args.requests),
                "--measure-only",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        result = json.loads(out.stdout.strip().splitlines()[-1])
        results.append(result)
        print(f"{runtime}: {result}")

    reference = results[0]["relation_f1"]
    for r in results:
        r["relation_f1_drop_points"] = round((reference - r["relation_f1"]) * 100, 2)
        r["passes_accuracy_gate"] = r["relation_f1_drop_points"] <= 1.0
        r["passes_latency_gate"] = r["latency_p95"] <= 3.0
    summary = {
        "base_model_version": version,
        "machine": args.machine,
        "threads": args.threads,
        "results": results,
    }
    out_dir = ROOT / "reports" / "performance"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{version}-runtimes.json").write_text(json.dumps(summary, indent=1) + "\n")
    lines = [
        f"# Inference runtimes: {version}",
        "",
        f"{args.machine}; {args.requests} sequential requests (dev protocols of up to 500 "
        "words) after warm-up; each runtime measured in a fresh process. Dev only.",
        "",
        "| Runtime | Entity F1 | Relation F1 | Drop (points) | p50 | p95 | Peak RSS | Bundle "
        "| Gates |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in results:
        gates = "pass" if r["passes_accuracy_gate"] and r["passes_latency_gate"] else "fail"
        lines.append(
            f"| {r['runtime']} | {r['entity_f1']:.4f} | {r['relation_f1']:.4f} | "
            f"{r['relation_f1_drop_points']:.2f} | {r['latency_p50']:.3f} s | "
            f"{r['latency_p95']:.3f} s | {r['peak_rss_mib']:.0f} MiB | {r['bundle_mib']:.0f} MiB "
            f"| {gates} |"
        )
    lines += ["", "Gates: relation F1 drop ≤ 1 point against torch-fp32; p95 ≤ 3 s."]
    (out_dir / f"{version}-runtimes.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
