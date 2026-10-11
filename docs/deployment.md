# Deployment and operations runbook

ProtocolLedger runs as one Docker Compose stack on a single CPU host:

| Service | Role | Exposure |
|---|---|---|
| `caddy` | HTTPS termination (automatic certificates), request-size cap, hides `/metrics` | public 80/443 |
| `app` | FastAPI: API + review interface, one model instance, SQLite reviews | host-only `127.0.0.1:8001` |
| `prometheus` | scrapes `app:8000/metrics` every 15 s, 30-day retention | host-only `127.0.0.1:9090` |

Persistent volumes: `reviews` (SQLite database, WAL mode), `caddy_data`, `prometheus_data`.
Model bundles are mounted **read-only** from the host. Neither the training corpus nor
model weights are baked into the image.

## Releases

A release pins **both** halves of a deployment:

- the application image, by immutable digest or image id, and
- the model bundle, by the SHA-256 of its `bundle.json` (every file in the bundle is
  hash-verified on load).

```bash
# Build (or pull) the image and build a verified bundle.
docker build -t protocolledger:$(git rev-parse --short HEAD) .
uv run python scripts/build_bundle.py

# Activate: verify bundle → write deploy/state/active.env → compose up --wait → smoke test.
uv run python scripts/release.py activate \
    --image protocolledger:$(git rev-parse --short HEAD) \
    --bundle artifacts/bundles/crf-logreg-4a9d8cc549 \
    --reason "describe why" --site-address protocolledger.example.org

uv run python scripts/release.py status
```

If the new release fails `compose up --wait` (unhealthy container) or the smoke test,
`activate` **automatically restores the previous release** and exits non-zero. Every
event (`activated`, `failed`, `rolled_back`) is appended to `deploy/state/releases.jsonl`.

## Serving SciBERT

The default image serves the CRF + logistic-regression bundle. To serve a span-relation
bundle, build with the `serve-neural` extra, which adds CPU PyTorch and transformers
(about 389 MB in total):

```bash
docker build --build-arg EXTRAS=serve-neural -t protocolledger:neural .
uv run python scripts/release.py activate --image protocolledger:neural \
    --bundle artifacts/bundles/scibert-uniform-negatives-s21-7dc7a1893e --reason "SciBERT"
```

Set `PROTOCOLLEDGER_THREADS` (default 4 in `compose.yaml`) to the host's vCPU count.
PyTorch otherwise sizes its thread pool to every host core. In a CPU-limited container
that oversubscribes the CPU: p95 latency measured 3.90 s with the default against 2.40 s
with matched threads.

## Rollback

```bash
uv run python scripts/release.py rollback --reason "describe the regression"
```

Rollback restores the previous good release's image **and** bundle together, then runs
the smoke test. A release that failed or was rolled back from is never chosen as a
rollback target again, so repeated rollbacks walk further back.

**Rehearsed** (2026-10-10, local Docker): release A → release B (different image id and
bundle) → rollback restored A's exact image id and model version, and a review saved
before B was still readable; a deliberately unhealthy release was refused and A was
restored automatically.

## Model lifecycle: from reviewer corrections to a release

Reviewer edits never become training labels automatically.

```bash
# 1. Export saved reviews (only those saved with their text) as a batch awaiting curation.
uv run python scripts/export_review_batch.py --db data/reviews.db
# 2. Curate: in data/corrections/batch-*/curation.json, set "include": true and give a
#    "reason" for each review you accept. Everything starts excluded.
# 3. Build a candidate: refuses uncurated batches, refuses any document that duplicates
#    a dev or test protocol, retrains with the selected configuration, evaluates on dev
#    and refuses a regression of more than 0.5 points of end-to-end relation F1.
uv run python scripts/train_candidate.py --batch data/corrections/batch-<timestamp>
# 4. Release it with smoke test and rollback.
uv run python scripts/release.py activate --image <image> \
    --bundle artifacts/bundles/crf-logreg-candidate-<hash> --reason "correction batch <hash>"
```

Curated batches contain protocol text and live under `data/corrections/`, which is never
committed. Candidate reports in `reports/candidates/` record which reviews were included,
their provenance and the dev scores, but no text.

**Rehearsed** (2026-10-11): four reviews were submitted through the API with reviewer
corrections. Three were short demonstration protocols written for the rehearsal; the
fourth deliberately copied a dev protocol.
- The uncurated batch was refused.
- With all four included, the copied review was refused as a duplicate of
  `dev_data/protocol_0`.
- With it excluded, candidate `crf-logreg-candidate-f2d7f24be9` reached dev relation F1
  0.5835 against 0.5822 live and passed the gate.
- The candidate was released through Compose (r2), smoke-tested, and rolled back to r1.

The neural model follows the same flow with `train_neural.py` on a GPU. The curated
batch must reach the GPU host privately (for example as a private Kaggle dataset); it is
never pushed to the public repository.

## Smoke test

`scripts/smoke_test.py` (standard library only) checks, in order: `/healthz`; `/readyz`
and the expected model version; extraction of the worked example (offsets are raw-text
slices; the implicit object of "mix" is routed to review); `/v1/preview`; review create →
read (text not stored) → CSV export; `/metrics`. CI runs it against the built image with
a tiny fixture bundle (`scripts/make_fixture_bundle.py`).

## Backups

```bash
docker compose -f deploy/compose.yaml --env-file deploy/state/active.env exec app \
    python -c "from pathlib import Path; from protocolledger.serve.reviews import ReviewStore; \
ReviewStore(Path('/data/reviews.db')).backup(Path('/data/reviews-backup.db'))"
docker compose -f deploy/compose.yaml --env-file deploy/state/active.env cp \
    app:/data/reviews-backup.db ./backups/reviews-$(date +%F).db
```

Restore with `scripts/backup_reviews.py restore` (integrity-checked; refuses to overwrite
without `--force`) into a stopped stack's volume.

## Monitoring

Prometheus (`ssh -L 9090:127.0.0.1:9090 host`, then http://localhost:9090) records:

| Metric | Use |
|---|---|
| `protocolledger_http_request_seconds` | latency percentiles per route template |
| `protocolledger_http_requests_total{status}` | error rate |
| `protocolledger_http_in_flight` | saturation |
| `process_resident_memory_bytes` | memory against the 3 GB target |
| `protocolledger_extract_input_chars` | input-length drift |
| `protocolledger_predicted_entities_total{label}` | label-frequency drift |
| `protocolledger_extract_review_items` | how much is routed to review |
| `protocolledger_review_decisions_total{origin,decision}` | correction rates |
| `protocolledger_model_info` | which model is live |

Unlabeled drift indicators trigger investigation only; estimating production accuracy
requires newly reviewed labels. Access logs are JSON lines (method, route template,
status, latency) and never contain submitted text.

## Hosting

Any small CPU VM with Docker works (the plan suggests e.g. a Hetzner CX-class instance;
set a budget before provisioning). Point a DNS record at it, set `--site-address` to the
domain, and Caddy obtains certificates automatically.
