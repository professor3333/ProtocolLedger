# Inference runtimes: scibert-uniform-negatives-s21-7dc7a1893e

Apple M1 (8 GB), 4 inference threads; 200 sequential requests (dev protocols of up to 500 words) after warm-up; each runtime measured in a fresh process. Dev only.

| Runtime | Entity F1 | Relation F1 | Drop (points) | p50 | p95 | Peak RSS | Bundle | Gates |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| torch-fp32 | 0.8003 | 0.6389 | 0.00 | 0.481 s | 2.074 s | 938 MiB | 420 MiB | pass |
| onnx-fp32 | 0.8003 | 0.6389 | 0.00 | 2.293 s | 6.937 s | 1058 MiB | 839 MiB | fail |
| onnx-int8 | 0.7988 | 0.6361 | 0.28 | 0.925 s | 2.899 s | 918 MiB | 526 MiB | pass |

Gates: relation F1 drop ≤ 1 point against torch-fp32; p95 ≤ 3 s.
