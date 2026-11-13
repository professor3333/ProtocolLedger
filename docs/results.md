# Results

Every number below comes from the shared scorer (`src/protocolledger/eval/scorer.py`).
Locked-test, new-set and development results are kept in separate sections.
Back to the [README](../README.md).

| Metric | What it establishes |
|---|---|
| Strict entity micro-F1 | exact boundaries and types |
| Relation F1 with gold entities | the relation classifier in isolation |
| **End-to-end relation F1** | correct type, direction, both endpoint spans and types |
| Quantity attachment accuracy | each value belongs to the right material or action |
| Complete-step exact match | how often a step needs no correction at all |
| Normalized-value exact match | numeric value, unit, range or symbolic value |
| Precision vs. coverage | reliability of retained predictions as thresholds change |

The scorer reports per-label scores with support, macro-F1 over supported labels, and
document-level bootstrap confidence intervals. Duplicate predictions are collapsed. The
locked test split can be scored only for a declared release. Slices: unseen reagent
names, Unicode perturbations, template siblings, challenge-set categories and recently
published protocols.

## Locked test (evaluated once, 2026-10-11)

The targets were frozen in [targets](targets.md) and merged first. The
declared releases were then evaluated **once** on the cleaned `test_data_2020` (111
protocols) by `scripts/locked_test.py`, at commit `fe0297c`
([full report](../reports/test/locked-test.md)).

| System | Entity F1 | Relation F1, gold entities | **Relation F1, end-to-end** | Quantity attachment |
|---|---:|---:|---:|---:|
| Rules | 0.647 [0.624, 0.668] | 0.575 | 0.292 [0.270, 0.317] | 0.441 |
| CRF + logistic regression | 0.703 [0.677, 0.727] | 0.768 | 0.504 [0.473, 0.536] | 0.629 |
| **SciBERT span-relation** | **0.766** [0.748, 0.784] | **0.787** | **0.580** [0.552, 0.606] | **0.699** |

| Frozen target | Test result | Met |
|---|---|---|
| Strict entity micro-F1 ≥ 0.75 | 0.766 | yes |
| End-to-end relation micro-F1 ≥ 0.65 | 0.580 | **no** |
| ≥ 5 points above the traditional baseline | +7.6 points | yes |
| ≥ 95% relation precision at ≥ 30% coverage | 95% precision at 13.4% coverage | **no** |
| ≤ 5-point F1 loss under whitespace / Unicode perturbations | −0.01 points | yes |
| Optimized artifact ≤ 1-point F1 loss (dev) | ONNX INT8 −0.28 | yes |
| p95 ≤ 3 s, ≥ 99% success, ≤ 3 GB (container, 4 CPUs) | 2.40 s, 100%, 1.06 GB | yes |
| Normalization ≥ 98% exact match, independently checked set | no independent set | not evaluated |
| ≥ 25% faster sheet completion (user pilot) | pilot not run (no participants) | not evaluated |

Test is harder than dev for every system: CRF + logistic regression falls from 0.582 to
0.504, and SciBERT from 0.639 to 0.580. SciBERT's margin over the traditional baseline
grows on test, from +5.7 to +7.6 points. Its largest advantage is on reagent names never
seen in training: recall 0.762 against 0.631. Part of the dev-to-test drop is consistent
with residual training overlap, which is far more common in dev (see the [containment audit](dataset_card.md#residual-overlap-containment-audit)). On dev
documents with almost no overlap (containment < 0.1), SciBERT scores 0.617 and
CRF + logistic regression 0.546, closer to their test scores. The dev-fitted isotonic
calibrator transfers to test, reducing expected calibration error from 0.172 to 0.021. The two relation-quality
targets are missed; the misses are reported here and the targets were not changed.

## New protocols.io sets: locked test portions (scored once, 2026-10-15)

The same declared releases were scored once on the locked test portions of the
later-domain and challenge sets, with `scripts/evaluate_annotation_set.py --split test`.
No human gold exists for these sets, so the reference is the **machine labels**, which no
person has reviewed: the numbers are **agreement with those labels, not accuracy**. For
test portions the script writes error counts but no example sentences, and no errors were
inspected. Reports: `reports/annotation_sets/*-test-*-vs-machine*.{json,md}`.

| Locked test portion, vs. machine labels | System | Entity F1 | Relation F1, end-to-end | Quantity attachment | Reagent recall, unseen / seen names |
|---|---|---:|---:|---:|---:|
| Later-domain (16 protocols, 128 steps) | CRF + logistic regression | 0.710 [0.669, 0.757] | 0.527 [0.471, 0.592] | 0.683 (376) | 0.658 (234) / 0.824 (210) |
| Later-domain (16 protocols, 128 steps) | **SciBERT** | **0.802** [0.768, 0.831] | **0.636** [0.594, 0.683] | **0.795** (376) | 0.829 (234) / 0.919 (210) |
| Challenge (5 protocols, 15 steps) | CRF + logistic regression | 0.790 [0.737, 0.824] | 0.604 [0.529, 0.661] | 0.773 (66) | 0.794 (34) / 0.773 (44) |
| Challenge (5 protocols, 15 steps) | **SciBERT** | **0.818** [0.790, 0.841] | **0.641** [0.520, 0.711] | **0.864** (66) | 0.824 (34) / 0.886 (44) |

| Challenge test category (SciBERT) | Steps | Entity F1 (support) | Relation F1 (support) |
|---|---:|---:|---:|
| conditional wording | 4 | 0.841 (64) | 0.726 (49) |
| implicit references | 7 | 0.833 (101) | 0.711 (77) |
| multiple actions | 9 | 0.826 (172) | 0.672 (134) |
| ranges | 2 | 0.788 (17) | 0.741 (13) |
| repeated materials | 8 | 0.851 (159) | 0.667 (127) |
| unusual symbols | 7 | 0.778 (109) | 0.614 (85) |

SciBERT keeps its lead over the traditional baseline on newer text: +10.9 points of
end-to-end relation F1 on the later-domain test portion. The challenge test portion is
only 15 steps, so its category scores are weak, and the two systems' relation CIs
overlap. The machine labels were aligned with train conventions, which both models also
learned, so agreement with them can overstate accuracy; measuring accuracy needs human
gold.

## Development set

> [!NOTE]
> The results below are **development-set** results, used to build, select and compare
> systems before the single test evaluation above.

| System (dev, 112 documents) | Entity F1 | Relation F1, gold entities | **Relation F1, end-to-end** | Quantity attachment | Complete steps |
|---|---:|---:|---:|---:|---:|
| Rules | 0.692 [0.666, 0.715] | 0.604 [0.577, 0.633] | **0.355** [0.322, 0.386] | 0.521 | 0.112 |
| CRF + logistic regression | 0.756 [0.733, 0.779] | 0.812 [0.795, 0.829] | **0.582** [0.553, 0.611] | 0.708 | 0.231 |
| **SciBERT span-relation, selected** (uniform negatives, 3 seeds) | **0.800** | 0.826 | **0.640 ± 0.004** | 0.758 | — |
| SciBERT span-relation, hard negatives (3 seeds) | 0.802 | 0.822 | 0.636 ± 0.006 | 0.768 | — |
| BERT-base-cased control (1 seed) | 0.795 | 0.821 | 0.634 [0.611, 0.657] | 0.764 | — |

<sub>Strict matching; 95% document-level bootstrap intervals in brackets for single runs,
mean ± sd over seeds otherwise. All experiments, including ablations:
<a href="../reports/experiments-dev.md">reports/experiments-dev.md</a>. Full per-label
tables: <a href="../reports/baselines/rules-dev.md">rules</a>,
<a href="../reports/baselines/crf-logreg-dev.md">CRF + logistic regression</a>,
<a href="../reports/neural/scibert-lr2e-5-s13-dev.md">SciBERT</a>.</sub>

**What the experiments answer** (dev):

| Question from the plan | Answer |
|---|---|
| Rules → CRF: does supervision help? | Yes: relation F1 0.355 → 0.582 |
| CRF → SciBERT: does a contextual encoder help? | Yes: 0.582 → 0.640 ± 0.004 (3 seeds), entity F1 0.756 → 0.800 |
| BERT → SciBERT: does scientific pretraining help? | Barely: 0.634 vs 0.641 at the same settings, well within noise |
| Frozen → fine-tuned encoder: worth the compute? | Decisively: 0.487 frozen vs 0.641 fine-tuned |
| Uniform → hard negatives: are hard attachments learned better? | No: uniform 0.640 ± 0.004 vs hard 0.636 ± 0.006 (3 seeds each) |
| Remove type and distance features | Small end-to-end cost (−0.7), but −3.8 points given gold entities |

**Targets are frozen** in [targets](targets.md), unchanged from the plan and
committed before the locked test split was touched.

**Selected configuration:** SciBERT, lr 2e-5, uniform negatives, the highest 3-seed dev
mean. The served model is its **median** seed (21), not the best, to avoid an optimistic
pick.

Against the targets, the selected configuration clears **entity F1 ≥ 0.75** on dev and
is **≥ 5 points above the traditional baseline** (+5.8 on the 3-seed mean). It does
**not** reach end-to-end relation F1 ≥ 0.65 on dev (0.640 ± 0.004). The targets were frozen
unchanged despite this, and the miss is reported as it stands.

- **Supervision pays off.** The CRF + logistic-regression baseline raises end-to-end
  relation F1 from 0.355 to 0.582. Most of the gain is in attachment: given the same gold
  entities, relation F1 rises from 0.604 to 0.812.
- **Entity errors compound.** Even with relation F1 0.812 on gold entities, end-to-end F1
  is 0.582. Every missed or mis-bounded entity also breaks the relations that touch it.
- **Quantities are easy; open vocabulary is not.** Temperature, Speed and Time exceed 0.91
  entity F1, while Method (0.46), Modifier (0.53) and Device (0.58) lag. Rare relations
  such as Commands (37 dev instances) and Of-Type (26) score 0.
- **Reference point.** Duplicate copies of the same protocol in the corpus agree with
  each other at relation F1 0.711.

**Where SciBERT's gains come from** (served model vs CRF + logistic regression, dev;
[error report](../reports/errors/scibert-uniform-s21-dev.md)):

| | CRF + LR | SciBERT |
|---|---:|---:|
| Gold relations correct | 54.5% | **62.7%** |
| Failed through an endpoint entity error | 34.4% | 27.7% |
| Genuine attachment errors | 3.0% | 2.9% |
| Reagent recall, names **unseen** in training | 0.570 | **0.658** |
| Relation recall, documents **without** a template sibling | 0.524 | **0.613** |

The gains are largest where generalization matters: unseen names, and documents that
share no template with training.

**Confidence** (served model, joint score P(relation) × P(head) × P(tail);
[report](../reports/calibration/scibert-uniform-s21-joint-dev.md)):
- **Precision:** 0.920 at 30% coverage. 95% precision is reachable only at 18.7%
  coverage, so the target of 95% precision at ≥ 30% coverage is **not met**.
- **Calibration:** isotonic calibration brings the expected calibration error from 0.183
  to 0.009.

**Baseline error analysis** (CRF + logistic regression, dev; [full report with
examples](../reports/errors/crf-logreg-dev.md)):

| Gold relations (10,065) | Share |
|---|---:|
| correct | 54.5% |
| **endpoint entity wrong** (entity error cascading) | **34.4%** |
| missed (endpoints right, no relation) | 5.6% |
| wrong attachment (same label, wrong head or tail) | 3.0% |
| wrong label | 2.5% |
| wrong direction | 0.1% |

About three of every four relation errors start as entity errors, so better entity
boundaries are where a contextual encoder has the most to gain.

Two slices stand out:
- **Unseen reagent names.** Reagent names never seen in training are found with recall
  **0.570**, against **0.873** for seen names. This is the slice where scientific
  pretraining should help.
- **Template siblings.** Dev documents that share a vendor template with a training
  document get relation recall 0.719, against 0.524 without, which is why template
  siblings are reported separately.

**Confidence** (CRF + logistic regression, dev; [report](../reports/calibration/crf-logreg-dev.md)):
- **Raw relation scores are badly calibrated.** Expected calibration error (ECE) is
  0.214. Isotonic regression, cross-fitted by document on dev, brings it to 0.009.
- **The baseline's confidence can't support the 95%-precision target.** Its most
  confident relations reach about 85% precision (0.808 at 30% coverage), because a
  relation score cannot see whether its endpoint entities are right. The neural model
  will also be scored with a joint confidence, P(relation) × P(head) × P(tail).

## Serving performance

| System | Machine | p95 latency | Success (1,000 requests) | Peak memory |
|---|---|---:|---:|---:|
| CRF + logistic regression | Apple M1 host, Docker limited to 4 CPUs / 4 GB | 0.035 s | 100% | 125 MiB |
| **SciBERT, PyTorch FP32 (served)**, container | Apple M1 host, Docker limited to 4 CPUs / 4 GB, `PROTOCOLLEDGER_THREADS=4` | **2.40 s** | 100% | 1,058 MiB |
| SciBERT, same container, default threads | same, threads not matched to the CPU quota | 3.90 s | 100% | 1,064 MiB |
| SciBERT, PyTorch FP32, in-process | Apple M1 (8 GB), 4 inference threads | 2.07 s | — | 938 MiB |
| SciBERT, ONNX Runtime FP32 | same | 6.94 s | — | 1,058 MiB |
| SciBERT, ONNX Runtime INT8 (−0.28 F1) | same | 2.90 s | — | 918 MiB |

<sub>Concurrency 1, dev protocols of up to 500 words, after warm-up
(<a href="../reports/performance/crf-logreg-m1-4cpu.md">report</a>, <code>scripts/load_test.py</code>).
Targets: p95 ≤ 3 s, ≥ 99% success, ≤ 3 GB. SciBERT runtimes:
<a href="../reports/performance/scibert-uniform-negatives-s21-7dc7a1893e-runtimes.md">report</a>.
On this ARM machine ONNX Runtime is slower than PyTorch, so PyTorch FP32 is served.
Matching inference threads to the container's CPU quota matters: with PyTorch's default
(one thread per host core) the CPU-limited container missed the p95 target (3.90 s).
Re-measure on the deployment host before changing runtimes.</sub>
