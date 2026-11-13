# New annotation sets (protocols.io)

Back to the [README](../README.md). Dataset-level summary: [dataset card](dataset_card.md#new-annotation-sets-protocolsio-20252026).

Two new test sets measure how the model does on text it was not built around. Both are
collected from **recent public protocols.io protocols** through the official API, and
neither shares a protocol with WNUT-2020 or with the other set.

| Set | Purpose | Protocols | Steps | Published |
|---|---|---:|---:|---|
| `later-domain` | protocols written about five years after the corpus | 38 (dev 22, test 16) | 301 (dev 173, test 128) | 2025-09 to 2026-08 |
| `challenge` | steps chosen for six hard phenomena | 11 (dev 6, test 5) | 33 (dev 18, test 15) | 2025-10 to 2026-07 |

**Collection** (`scripts/collect_protocolsio.py`, rules in
`src/protocolledger/data/protocolsio.py`):
- **Candidates.** The newest public protocols for ten wet-lab search terms, interleaved
  across terms.
- **Eligibility.** Published on or after 2025-01-01, English, at least 5 usable steps,
  and at least 30% of steps state a quantity. A protocol that is the same as a WNUT-2020
  document (the dedup rule above) or as an earlier candidate is excluded.
- **Step text.** Taken from the API's HTML rendering, so embedded amounts, durations and
  temperatures appear as the reader sees them. Each step is one line. Notes, tables and
  figures are dropped and counted. Steps are usable when they keep 3–120 words, contain
  at least one train-split action word, and are not in an introduction, safety or
  results section.
- **Later-domain set.** The first 8 usable steps of each protocol.
- **Challenge set.** Up to 3 steps per protocol, chosen round-robin until each category
  has at least 10 steps. The categories are multiple actions, repeated materials,
  ranges, unusual symbols, implicit references and conditional wording, each a fixed
  text test using train-only vocabularies.
- **Splits.** Dev or test is assigned per whole protocol from a hash of its id, before
  any annotation. The **test portions are locked** like `test_data_2020`.
- **Reproducibility.** The collected sets are committed in `data/annotation/<set>/`
  (`sources.jsonl` and `texts/`), because protocols.io search results change over time.
  The raw API responses are cached under `data/raw/protocolsio/` (not committed), so
  re-running on the same machine rebuilds byte-identical sets. Every decision is in
  `data/manifests/protocolsio_collection.json`.

Each source keeps its URL, DOI, authors, version and publication date. Protocol text is
protocols.io user content under CC BY, redistributed here with that attribution; the
repository's MIT license covers the code, not this text.

**Annotating.** No human gold has been written yet. The tooling for it is in place: an
annotation-only server mode, a warm-up check against train gold, and guidelines for one
annotator labelling from scratch without model suggestions
([annotation guidelines](annotation_guidelines.md)).
Where the original schema leaves a choice open, the guideline adopts the convention the
cleaned training split uses most often, with counts. In from-scratch mode the interface
preselects no entity type, relation label or direction. Agreement figures on such gold
would be **repeat-annotation consistency**, not inter-annotator agreement.

**Machine labels (provisional).** Until the human gold exists, both sets also have
machine-generated labels that no person has reviewed (`machine_labels.jsonl`, built by
`scripts/build_machine_labels.py`; see the [dataset card](dataset_card.md)). Scores
against them show **agreement with those labels, not accuracy**. The dev portions are
below; the locked test portions were scored once, in
[results](results.md#new-protocolsio-sets-locked-test-portions-scored-once-2026-10-15):

| Dev portion, vs. machine labels | Entity F1 | Relation F1, end-to-end | Quantity attachment |
|---|---:|---:|---:|
| Later-domain (22 docs), CRF + logistic regression | 0.739 [0.706, 0.777] | 0.567 [0.515, 0.620] | 0.663 (320) |
| Later-domain (22 docs), SciBERT selected (seed 21) | 0.812 [0.786, 0.843] | 0.664 [0.613, 0.714] | 0.778 (320) |
| Challenge (6 docs, 18 steps), CRF + logistic regression | 0.567 [0.506, 0.640] | 0.390 [0.279, 0.502] | 0.436 (39) |
| Challenge (6 docs, 18 steps), SciBERT selected (seed 21) | 0.663 [0.575, 0.756] | 0.557 [0.462, 0.651] | 0.641 (39) |

What the disagreements show, for SciBERT (dev only):

- **Unseen names.** Reagent recall is 0.789 for names absent from train vs. 0.915 for
  seen ones (later-domain), the same gap as on WNUT dev. Newer vocabulary gets the wrong
  type: "probe" read as a Device, "12S"/"16S" as a Generic-Measure, "NTC" as a
  Measure-Type.
- **Quantities.** Of 179 gold `Measure` links in later-domain, 133 are correct, 36 fail
  on an endpoint's span or type, 7 are missed and only 3 go to the wrong material. In
  amount-first lists
  ("250 µL, of the NTP buffer mix ... 25 µL, of RNasin Plus") the model attaches each
  amount to the previous material.
- **Challenge categories.** The weakest are repeated materials (entity F1 0.600, 67 gold)
  and ranges (relation F1 0.503, 81 gold). Each covers only a few steps, so these
  differences are weak.
- **Boundaries.** Many boundary disagreements are adjectives inside or outside a name
  ("barcoded primer" vs. "primer"). Train itself is split on this: a separate Modifier
  1,418 times, inside the name 526 times.

Before scoring, the machine labels were aligned with train conventions: `Or` runs from
the earlier to the later mention; "approximately"/"up to"/"within" stay outside quantity
spans; "not" is left unlabelled; and nouns such as "Preparation" in titles are Methods
without relations.
Reports and error taxonomies: `reports/annotation_sets/*-vs-machine*.{json,md}`.

```bash
# 1. Collect (needs a protocols.io client access token in ~/.config/protocolledger/protocolsio_token)
uv run python -I scripts/collect_protocolsio.py

# 2. Warm up on two train protocols and compare with the corpus gold
uv run python scripts/annotation_warmup.py prepare   # writes artifacts/warmup/*.txt
#    (annotate them as in step 3, but with PROTOCOLLEDGER_DB=data/warmup.db)
uv run python scripts/annotation_warmup.py score --db data/warmup.db

# 3. Serve the interface in annotation-only mode (model extraction switched off, so no
#    suggestion can bias the gold), load a file from data/annotation/<set>/texts/ with
#    the upload button, label it, and save the review
PROTOCOLLEDGER_ANNOTATION_ONLY=1 PROTOCOLLEDGER_BUNDLE=artifacts/bundles/crf-logreg-4a9d8cc549 \
  PROTOCOLLEDGER_DB=data/annotation.db \
  uv run uvicorn --factory protocolledger.serve.app:create_app_from_env --port 8000

#    To continue an annotation later, use "Open a saved review" in the interface. If the
#    browser no longer lists it, issue a new token from the database and paste it there:
uv run python scripts/reopen_review.py --db data/annotation.db \
  --text-file data/annotation/later-domain/texts/<id>.txt

# 4. Export the saved annotations as gold, then score a model on the dev portion.
#    The export prints how much of each portion is annotated. The test portion can be
#    scored against gold only when it is complete, and only once per model.
uv run python scripts/export_annotations.py --db data/annotation.db --set later-domain
uv run --extra neural python scripts/evaluate_annotation_set.py --set later-domain \
  --split dev --bundle artifacts/bundles/scibert-uniform-negatives-s21-7dc7a1893e

# 5. Compare annotations of the dev portion: a blind second pass (repeat-annotation
#    consistency), or the machine labels against the human gold
uv run python scripts/annotation_agreement.py --set later-domain \
  --first data/annotation.db --second data/annotation-repeat.db
uv run python scripts/annotation_agreement.py --set later-domain \
  --first data/annotation.db --second machine
```
