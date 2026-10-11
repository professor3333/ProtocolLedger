# Locked test evaluation

Evaluated once on 2026-10-11T05:25:51+00:00 at commit `fe0297caed`, after the targets were frozen in [docs/targets.md](../../docs/targets.md). Split: cleaned test_data_2020 (111 protocols). 95% CIs: document-level bootstrap.

| System | Entity F1 | Relation F1, gold entities | **Relation F1, end-to-end** | Quantity attachment | Complete steps |
|---|---:|---:|---:|---:|---:|
| Rules | 0.647 [0.624, 0.668] | 0.575 | **0.292** [0.270, 0.317] | 0.441 | 0.068 |
| CRF + logistic regression | 0.703 [0.677, 0.727] | 0.768 | **0.504** [0.473, 0.536] | 0.629 | 0.142 |
| **SciBERT span-relation** | 0.766 [0.748, 0.784] | 0.787 | **0.580** [0.552, 0.606] | 0.699 | 0.177 |

## Frozen targets

| Target | Test result | Met |
|---|---|---|
| Strict entity micro-F1 ≥ 0.75 | 0.766 | yes |
| End-to-end relation micro-F1 ≥ 0.65 | 0.580 | **no** |
| ≥ 5 points above the traditional baseline | +7.6 points | yes |
| ≥ 95% relation precision at ≥ 30% coverage | 13.4% coverage at 95% precision | **no** |
| ≤ 5-point F1 loss under perturbations | -0.01 points | yes |

## Slices

| | CRF + LR | SciBERT |
|---|---:|---:|
| Reagent recall, names unseen in train | 0.631 | 0.762 |
| Reagent recall, names seen in train | 0.834 | 0.862 |
| Relation recall, documents without a template sibling (16022 gold) | 0.436 | 0.525 |
| Relation recall, documents with a template sibling (356 gold) | 0.418 | 0.472 |

## Confidence (SciBERT, joint score)

- Precision at 30% coverage: 0.905 [0.891, 0.918]
- Coverage at 95% precision: 13.4%
- Expected calibration error: raw 0.172, with the dev-fitted isotonic calibrator 0.021

Not evaluated: value normalization against an independently checked set, and the user pilot (see docs/targets.md).
