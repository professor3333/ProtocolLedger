# Frozen acceptance targets

**Frozen on 2026-10-11, before any evaluation of the locked test split.** The targets
below are exactly the ones proposed in the project plan. None was changed after the
development-set feasibility assessment, including the ones dev shows will probably be
missed. The locked test split (`test_data_2020`, cleaned) is evaluated **once**, after
this file is merged to `main`. Every target is then reported as met or not met, with no
further changes.

## Declared releases for the single locked-test evaluation

| System | Model version |
|---|---|
| Rules | `reports/baselines/rules-dev.json` configuration (fit on train) |
| CRF + logistic regression | `crf-logreg-4a9d8cc549` |
| **SciBERT span-relation (primary)** | `scibert-uniform-negatives-s21-7dc7a1893e` |

## Targets and development-set status

| Area | Target | Dev status (feasibility only) |
|---|---|---|
| Entity quality | Strict entity micro-F1 ≥ 0.75 on the cleaned held-out set | 0.800 (3-seed mean); likely met |
| End-to-end relations | Micro-F1 ≥ 0.65 **and** ≥ 5 points above the traditional baseline | 0.640 ± 0.004; +5.8 points; F1 part likely **not met** |
| High-confidence predictions | ≥ 95% relation precision at ≥ 30% retained coverage | 95% precision reached at 18.7% coverage (joint score); likely **not met** |
| Value normalization | ≥ 98% exact match on an independently checked set of supported formats | **Not evaluable:** no independently checked set exists yet |
| Robustness | ≤ 5-point F1 loss under meaning-preserving whitespace / Unicode perturbations | −0.01 points; likely met |
| Optimization | ≤ 1-point end-to-end F1 loss for an optimized inference artifact | ONNX INT8: −0.28 points (not served; PyTorch FP32 is faster on the measured host) |
| Performance | Warm p95 ≤ 3 s for ≤ 500-word inputs at concurrency 1 on a named 4-vCPU machine | 2.40 s: Apple M1 host, Docker limited to 4 CPUs, 4 inference threads |
| Memory | Peak serving RSS ≤ 3 GB under the declared workload | 1,058 MiB |
| Reliability | ≥ 99% valid-request success across a 1,000-request load test | 100% |
| Usefulness | ≥ 25% reduction in median preparation-sheet completion time without reduced final accuracy | **Not evaluated:** no user pilot has been run |

The performance, memory, reliability and optimization targets are properties of the
service, not of a data split. They were measured on dev inputs and are not re-measured
on test text.
