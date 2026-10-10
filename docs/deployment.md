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
