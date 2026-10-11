# Load test: scibert-uniform-s21-m1-4cpu

span-relation `scibert-uniform-negatives-s21-7dc7a1893e` on **Apple M1 (8 GB) host, Docker limited to 4 CPUs / 4 GB**; 1000 sequential requests (concurrency 1) after 20 warm-up; dev protocols of up to 500 words (median 216.0).

| Measure | Result | Target |
|---|---:|---:|
| p50 latency | 0.928 s | |
| **p95 latency** | **3.896 s** | ≤ 3.0 s |
| p99 latency | 6.695 s | |
| Success rate | 100.0% | ≥ 99% |
| Peak memory (container) | 1063.9 MiB | ≤ 3072 MiB |
| Throughput | 0.75 req/s | |
