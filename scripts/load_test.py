"""Latency, reliability and memory load test against a running container.

    uv run python scripts/load_test.py --base-url http://127.0.0.1:8001 \\
        --container protocolledger-load --requests 1000 --machine "M1, Docker --cpus 4"

Request bodies are dev protocols cut to at most --max-words words, sent in a fixed
seeded order at concurrency 1 after a warm-up. Peak memory is sampled from
``docker stats`` while the test runs. Writes reports/performance/<name>.json and .md.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from protocolledger.data.splits import load_split

ROOT = Path(__file__).resolve().parents[1]


def bodies(max_words: int, seed: int) -> list[str]:
    texts = []
    for doc in load_split(ROOT, "dev"):
        lines, words = [], 0
        for line in doc["text"].splitlines():
            n = len(line.split())
            if words + n > max_words:
                break
            lines.append(line)
            words += n
        if lines:
            texts.append("\n".join(lines) + "\n")
    random.Random(seed).shuffle(texts)
    return texts


def post(url: str, text: str) -> tuple[int, float]:
    data = json.dumps({"text": text}).encode()
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=60) as res:
            res.read()
            status = res.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    except OSError:
        status = 0
    return status, time.perf_counter() - started


def parse_mem(value: str) -> float:
    number, unit = float(value[:-3]) if value.endswith("iB") else float(value[:-1]), value[-3:]
    scale = {"KiB": 1 / 1024, "MiB": 1.0, "GiB": 1024.0}.get(unit, 1 / 1024 / 1024)
    return number * scale


def sample_memory(container: str, stop: threading.Event, peaks: list[float]) -> None:
    while not stop.is_set():
        out = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", container],
            capture_output=True,
            text=True,
            check=False,
        )
        if out.returncode == 0 and out.stdout.strip():
            peaks.append(parse_mem(out.stdout.split("/")[0].strip()))
        stop.wait(0.5)


def pct(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(q * len(ordered)))]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--container", required=True)
    parser.add_argument("--requests", type=int, default=1000)
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--max-words", type=int, default=500)
    parser.add_argument("--machine", required=True, help="describe the hardware honestly")
    parser.add_argument("--name", required=True)
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args(argv)
    url = args.base_url.rstrip("/") + "/v1/extract"
    texts = bodies(args.max_words, args.seed)
    ready = json.loads(urllib.request.urlopen(args.base_url + "/readyz", timeout=10).read())

    for i in range(args.warmup):
        post(url, texts[i % len(texts)])
    stop, peaks = threading.Event(), []
    sampler = threading.Thread(target=sample_memory, args=(args.container, stop, peaks))
    sampler.start()
    latencies, statuses, words = [], [], []
    started = time.perf_counter()
    for i in range(args.requests):
        text = texts[i % len(texts)]
        status, seconds = post(url, text)
        statuses.append(status)
        latencies.append(seconds)
        words.append(len(text.split()))
    wall = time.perf_counter() - started
    stop.set()
    sampler.join()

    ok = sum(s == 200 for s in statuses)
    report = {
        "name": args.name,
        "machine": args.machine,
        "model_version": ready["model_version"],
        "system": ready["system"],
        "concurrency": 1,
        "requests": args.requests,
        "warmup_requests": args.warmup,
        "input_words": {"max": max(words), "median": statistics.median(words)},
        "success_rate": round(ok / args.requests, 4),
        "status_counts": {str(s): statuses.count(s) for s in sorted(set(statuses))},
        "latency_seconds": {
            "p50": round(pct(latencies, 0.50), 4),
            "p95": round(pct(latencies, 0.95), 4),
            "p99": round(pct(latencies, 0.99), 4),
            "max": round(max(latencies), 4),
        },
        "throughput_rps": round(args.requests / wall, 2),
        "peak_memory_mib": round(max(peaks), 1) if peaks else None,
        "targets": {"p95_seconds": 3.0, "success_rate": 0.99, "peak_memory_mib": 3072},
    }
    out = ROOT / "reports" / "performance"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{args.name}.json").write_text(json.dumps(report, indent=1) + "\n", "utf-8")
    lat, t = report["latency_seconds"], report["targets"]
    md = [
        f"# Load test: {args.name}",
        "",
        f"{report['system']} `{report['model_version']}` on **{args.machine}**; "
        f"{args.requests} sequential requests (concurrency 1) after {args.warmup} warm-up; "
        f"dev protocols of up to {args.max_words} words "
        f"(median {report['input_words']['median']}).",
        "",
        "| Measure | Result | Target |",
        "|---|---:|---:|",
        f"| p50 latency | {lat['p50']:.3f} s | |",
        f"| **p95 latency** | **{lat['p95']:.3f} s** | ≤ {t['p95_seconds']} s |",
        f"| p99 latency | {lat['p99']:.3f} s | |",
        f"| Success rate | {report['success_rate']:.1%} | ≥ {t['success_rate']:.0%} |",
        f"| Peak memory (container) | {report['peak_memory_mib']} MiB "
        f"| ≤ {t['peak_memory_mib']} MiB |",
        f"| Throughput | {report['throughput_rps']} req/s | |",
    ]
    (out / f"{args.name}.md").write_text("\n".join(md) + "\n", "utf-8")
    print("\n".join(md))
    return 0 if ok / args.requests >= 0.99 else 1


if __name__ == "__main__":
    raise SystemExit(main())
