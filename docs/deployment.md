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

### Versioned releases (`.github/workflows/release.yml`)

Pushing a tag `v*` runs the release workflow on a GitHub-hosted runner:

1. installs CPU PyTorch, downloads the corpus at the pinned commit (hash-verified) and
   builds the dev split, and fetches the bundle at its pinned Hub revision;
2. `scripts/release_check.py` checks the gates in `configs/release_gates.json` on dev
   only: entity and end-to-end relation F1 within 0.002 of the bundle's recorded CPU
   evaluation, precision at 30% coverage and post-calibration ECE matching the committed
   calibration report, p95 latency ≤ 3 s and peak memory ≤ 3 GB on the runner;
3. builds the SciBERT image and smoke-tests it with the pinned bundle;
4. pushes `ghcr.io/professor3333/protocolledger:<tag>` and creates a GitHub release
   with `release-manifest.json` (gates, metrics, bundle hash, image digest).

Any failed step stops the release. Running the workflow manually does steps 1–3 and
publishes nothing. ONNX / INT8 parity is not gated, because the served runtime is
PyTorch FP32.

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

## Live demo (GitHub Codespaces)

`.devcontainer/` defines a Codespace that serves the SciBERT model with the public-demo
banner. Open it from the README badge or **Code → Codespaces** on GitHub.

1. `setup.sh` (once, on creation): installs uv 0.12.5, runs `uv sync --locked
   --extra serve-neural` (CPU PyTorch) and `scripts/fetch_demo_bundle.py`, which downloads
   the bundle from the Hub at the pinned revision.
2. `serve.sh` (on every start, and when a browser attaches): starts uvicorn on port 8000
   in the background, logging to `/tmp/protocolledger.log`, and waits until `/readyz`
   answers. It does nothing if the service is already up. The bundle's file hashes are
   verified when it loads. It ignores SIGHUP before forking: Codespaces ends the start
   command's session as soon as the script exits, which killed the server before it
   detached.

The Codespace needs 2 cores and 8 GB. It stops when idle, and reviews saved in it are
kept in `/tmp` only. Check it with `curl -s localhost:8000/readyz` in the Codespace
terminal.

## Always-on public demo (AWS EC2)

The public demo runs at **https://44.222.11.189.sslip.io** on one AWS EC2 `t4g.small`
in `us-east-1`: 2 Graviton (ARM) vCPUs, 2 GB RAM plus 4 GB swap, 30 GB encrypted gp3
disk, an Elastic IP, Ubuntu 24.04. It is paid from the account's Free-plan credit
(about USD 17.50 a month at on-demand prices: instance, public IPv4 and disk), and a
monthly budget on gross usage alerts at 80% of USD 25. AWS closes Free-plan accounts when
the plan ends unless they are upgraded, so the demo runs until **2027-03-22** at most.

The security group allows 80/443 from anywhere and SSH only from the owner's address.
Hugging Face requires a paid plan for Docker Spaces, so the model is hosted on the Hub
(`professor3333/protocolledger-scibert`, pinned by revision) and the app runs on the VM.

Deploy or update (any Ubuntu 24.04 VM, ARM or x86, reachable over SSH):

```bash
uv run python scripts/deploy_vm.py --host <public-ip> --threads <vCPUs>
```

The script:
1. Refuses an unpushed commit.
2. Runs `deploy/vm/bootstrap.sh` (idempotent). This installs Docker and uv, adds 4 GB of
   swap when the VM has under 3.5 GB of RAM, and opens ports 80/443 in the host firewall
   when the image rejects them by default (Oracle's Ubuntu images do).
3. Builds the SciBERT image at `HEAD` on the VM.
4. Downloads the bundle at the pinned revision.
5. Activates it with `release.py --public-demo`, which smoke-tests the release and rolls
   back on failure.
6. Checks `https://<ip>.sslip.io/readyz`. Caddy obtains a certificate automatically for
   the free `sslip.io` hostname.

The first deploy took 803 s (2026-10-20, measured once). The public-demo banner warns that
saved reviews are temporary and that confidential protocols must not be pasted.
`/metrics` answers 404 through Caddy; Prometheus is reachable only through an SSH tunnel.

**CPU credits.** A `t4g.small` sustains 20% of its two vCPUs and bursts above that on
earned CPU credits. The instance uses *standard* credits, so it slows to the baseline
instead of billing extra when the credits run out. Building the image uses up the launch
credits: for about an hour after a deploy the demo is several times slower.
With credits available, 100 requests of dev protocols cut to at most 500 words, sent at
concurrency 1 on the VM itself after 10 warm-up requests, took p50 2.41 s, p95 7.01 s and
at most 9.76 s, with the app at 945 MiB (2026-10-20, measured once). This is slower than
the 3 s gate, which is defined for a 4-vCPU host; the demo VM is not that host.

**Stopping it.** Terminate the instance tagged `Name=protocolledger-demo` and release
its Elastic IP (an unattached Elastic IP is still billed), then delete the security
group and key pair of the same name.

## Hosting

Any small CPU VM with Docker works (set a budget before provisioning). Point a DNS record
at it, pass the domain to `release.py activate --site-address`, and Caddy obtains
certificates automatically.
