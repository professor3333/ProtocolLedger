# Load test: crf-logreg-m1-4cpu

crf+logreg `crf-logreg-4a9d8cc549` on **Apple M1 (8 GB) host, Docker limited to 4 CPUs / 4 GB**; 1000 sequential requests (concurrency 1) after 20 warm-up; dev protocols of up to 500 words (median 216.0).

| Measure | Result | Target |
|---|---:|---:|
| p50 latency | 0.015 s | |
| **p95 latency** | **0.035 s** | ≤ 3.0 s |
| p99 latency | 0.052 s | |
| Success rate | 100.0% | ≥ 99% |
| Peak memory (container) | 124.9 MiB | ≤ 3072 MiB |
| Throughput | 57.82 req/s | |
