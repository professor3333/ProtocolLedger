# Model card: ProtocolLedger span-relation extractor

| | |
|---|---|
| Served model | `scibert-uniform-negatives-s21-7dc7a1893e` |
| Architecture | SpERT-style span and directed-relation classifier over a shared encoder (independent implementation of Eberts and Ulges, arXiv:1909.07755) |
| Encoder | `allenai/scibert_scivocab_cased` at revision `ddf0be025f8e432a1870e34811997ba6725bf04a` (Apache-2.0), fine-tuned |
| Training data | WNUT-2020 Wet Lab Protocols, cleaned **train** split (314 protocols); see the [dataset card](dataset_card.md) |
| Selection | dev end-to-end relation micro-F1; configuration chosen on a 3-seed mean, then the **median** seed served |
| Status | Evaluated once on the locked test split (2026-10-11) after targets were frozen |

## Intended use

The model extracts actions, materials, quantities, equipment and locations, conditions,
and the directed relations between them, from English wet-lab protocol text. Its output
is a set of **suggested** preparation-sheet entries, each linked to its source
characters, which a reviewer confirms or corrects in the ProtocolLedger interface before
export.

## Not for

- Judging whether a protocol is scientifically complete, correct or safe.
- Executing or automating protocols from unreviewed output.
- Using unreviewed results as final records.
- Filling in implicit arguments, or treating "not explicitly stated" as "not required".
  The system never does this; downstream users should not either.
- Entity or relation types outside the 18-entity and 14-relation schema.
- Non-English text, or PDF / OCR input.
- Other domains or protocol sources without local validation.

## Provenance

- **Encoder.** SciBERT cased, pinned by Hugging Face commit. Case preservation is forced
  and checked at load time, because the cased checkpoint ships no tokenizer config and
  would otherwise lowercase `mM` to `mm`.
- **Encoder view.** Characters the vocabulary cannot represent (for example the micro
  sign in `µL`, which SciBERT maps to `[UNK]`) are substituted only in the text handed to
  the encoder. Offsets always refer to the original text.
- **Heads.**
  - A span is the max-pool of its words plus a width embedding.
  - Entity logits come from the span concatenated with the CLS vector.
  - Relation logits use both spans, the max-pooled words between them, both entity types
    and a signed distance bucket.
  - Relations are multilabel (sigmoid).
- **Training.**
  - AdamW: encoder learning rate 2e-5, heads 1e-3, 10% warmup with linear decay.
  - Batch size 16, at most 10 epochs, patience 3, mixed precision on one Tesla T4 (Kaggle).
  - About 100 sampled negative spans and pairs per step, sampled uniformly.
  - Seed 21; best epoch 9.
- **Reproducibility.** Code commit, split-manifest hash, encoder revision, checkpoint
  hash and the selection-report hash are all recorded in the bundle's `bundle.json`. The
  bundle was rebuilt on CPU and reproduces the GPU dev scores exactly (entity F1 0.8003,
  relation F1 0.6389).

## Training data and splits

The released WNUT-2020 splits were the starting point, with these changes:
- **Deduplication.** Exact and near-duplicate copies and revisions were removed by
  document, always keeping the copy in the most protected split.
- **Correction ledger.** 291 whitespace-trimming corrections were applied identically to
  every split.
- **Locked test.** `test_data_2020` is never used for any decision.

Cleaned sizes: train 314, dev 112, test 111 protocols.

## Metrics (dev, 112 protocols)

| Metric | Selected configuration (3 seeds) | Served seed | CRF + logistic regression |
|---|---:|---:|---:|
| Strict entity micro-F1 | 0.800 | 0.800 | 0.756 |
| **End-to-end relation micro-F1** (primary) | **0.640 ± 0.004** | 0.639 [0.614, 0.665] | 0.582 |
| Relation F1 given gold entities | 0.826 | 0.830 | 0.812 |
| Quantity attachment accuracy | 0.758 | 0.757 | 0.708 |

**Proposed targets** (not yet frozen):
- Entity F1 ≥ 0.75: met.
- At least 5 points above the traditional baseline: met (+5.8).
- **End-to-end relation F1 ≥ 0.65: not met** (0.640).

**Confidence** (served seed, joint score P(relation) × P(head) × P(tail)):
- **Precision.** 0.920 at 30% coverage. 95% precision is reachable only at 18.7%
  coverage, so the target of 95% precision at ≥ 30% coverage is not met.
- **Calibration.** Isotonic calibration, cross-fitted by document on dev, reduces the
  expected calibration error from 0.183 to 0.009.

**Error profile** (served seed):
- **Correct:** 62.7% of gold relations.
- **Endpoint entity wrong:** 27.7%.
- **Missed:** 4.8%.
- **Genuine attachment errors:** 2.9%.
- **Wrong label:** 1.8%.

**Slices:**

| Slice | Served seed | CRF + logistic regression |
|---|---:|---:|
| Reagent recall, names unseen in train | 0.658 | 0.570 |
| Reagent recall, names seen in train | 0.903 | 0.873 |
| Relation recall, documents without a template sibling in train | 0.613 | 0.524 |
| Relation recall, documents with a template sibling in train | 0.740 | 0.719 |

**Reference point.** Duplicate copies of the same protocol in the corpus agree with each
other at entity F1 0.863 and relation F1 0.711.

## Locked test results (evaluated once)

| Metric (cleaned `test_data_2020`, 111 protocols) | SciBERT (served) | CRF + logistic regression |
|---|---:|---:|
| Strict entity micro-F1 | 0.766 [0.748, 0.784] | 0.703 |
| **End-to-end relation micro-F1** | **0.580** [0.552, 0.606] | 0.504 |
| Relation F1 given gold entities | 0.787 | 0.768 |
| Quantity attachment accuracy | 0.699 | 0.629 |
| Reagent recall, names unseen in train | 0.762 | 0.631 |
| Precision at 30% coverage (joint score) | 0.905 | — |
| Coverage at 95% precision | 13.4% | — |
| ECE raw / with the dev-fitted calibrator | 0.172 / 0.021 | — |

Frozen targets on test:
- **Met:** entity F1 ≥ 0.75, at least 5 points above the traditional baseline (+7.6),
  and robustness (−0.01).
- **Not met:** end-to-end relation F1 ≥ 0.65, and 95% precision at ≥ 30% coverage.

Test is harder than dev for every system. Full report:
[reports/test/locked-test.md](../reports/test/locked-test.md).

## New protocols.io sets (vs. machine labels)

Recent protocols (2025–2026) that no system was built around. No human gold exists for
them, so the reference is machine-generated labels that no person has reviewed: these are
**agreement scores, not accuracy**. The test portions were scored once, on 2026-10-15.

| Metric | Later-domain dev (22) | Later-domain test (16) | Challenge dev (6) | Challenge test (5) |
|---|---:|---:|---:|---:|
| Strict entity micro-F1 | 0.812 | 0.802 | 0.663 | 0.818 |
| End-to-end relation micro-F1 | 0.664 | 0.636 | 0.557 | 0.641 |
| Quantity attachment accuracy | 0.778 | 0.795 | 0.641 | 0.864 |

The challenge portions have 18 and 15 steps, so their scores vary a lot between portions.
Details and CIs: the [README](../README.md#new-protocolsio-sets-locked-test-portions-scored-once-2026-10-15).

## Inference performance

Measured on an Apple M1 (8 GB) with 4 inference threads: 200 sequential requests of dev
protocols up to 500 words, each runtime in a fresh process
([report](../reports/performance/scibert-uniform-negatives-s21-7dc7a1893e-runtimes.md)).

| Runtime | Relation F1 | p50 | p95 | Peak RSS |
|---|---:|---:|---:|---:|
| **PyTorch FP32 (served)** | 0.6389 | 0.48 s | **2.07 s** | 938 MiB |
| ONNX Runtime FP32 | 0.6389 | 2.29 s | 6.94 s | 1,058 MiB |
| ONNX Runtime INT8 (dynamic) | 0.6361 | 0.93 s | 2.90 s | 918 MiB |

On this ARM machine PyTorch FP32 is the fastest runtime and loses no accuracy, so it is
served. INT8 stays within the 1-point accuracy gate but is slower here. Re-measure on the
deployment host (likely x86) with `scripts/optimize_bundle.py` before changing runtimes.

## Known failure modes

- **Entity errors cascade into relations.** Most relation errors come from a wrong or
  missed endpoint entity.
- **Open-vocabulary types are weakest.** Modifier, Method, Device and Generic-Measure
  score lowest.
- **Unseen reagent names** are found less often than seen ones.
- **Amount-first lists** ("250 µL, of the NTP buffer mix ... 25 µL, of RNasin Plus"):
  each amount is attached to the previous material (seen on later-domain dev).
- **Rare relations** are unreliable: Commands (37 dev instances), Of-Type (26) and
  Product.
- **Implicit references** such as "it", and cross-step coreference, are not resolved.
- **Negation, alternatives and conditional instructions** are not modelled.
- **Text glued together by table flattening** (for example `100 µlof`) cannot be
  segmented.
- **Template overlap.** Protocols that share a vendor template with training data score
  higher than the rest.

## Release process

- **Selection.** Thresholds and the configuration are chosen on dev only, never on test.
- **Bundle.** Weights are stored as safetensors (no pickle). The encoder config and
  tokenizer are included, and every file is hash-verified on load, so serving needs no
  network access.
- **Release.** A release pins the image digest together with the bundle hash.
  `scripts/release.py` smoke-tests each activation and restores the previous image and
  bundle together if it fails.
