#!/usr/bin/env bash
# Start the review service on port 8000 in the background, with the public-demo banner.
# Codespaces runs this on every start and when a browser attaches; it does nothing if the
# service already answers. Saved reviews live in /tmp and do not persist.
set -euo pipefail
cd "$(dirname "$0")/.."
if curl -sf --max-time 2 localhost:8000/healthz >/dev/null; then
  echo "ProtocolLedger is already running on port 8000"
  exit 0
fi
bundle=$(python -m uv run --no-sync python scripts/fetch_demo_bundle.py)
# Codespaces ends this command's session as soon as the script exits, which kills any child
# that has not detached yet. Ignore the hang-up before forking, then wait until it serves.
trap '' HUP
PROTOCOLLEDGER_BUNDLE="$bundle" PROTOCOLLEDGER_DB=/tmp/protocolledger-demo.db \
  PROTOCOLLEDGER_PUBLIC_DEMO=1 PROTOCOLLEDGER_THREADS="$(nproc)" \
  setsid nohup .venv/bin/uvicorn --factory protocolledger.serve.app:create_app_from_env \
  --host 0.0.0.0 --port 8000 >/tmp/protocolledger.log 2>&1 </dev/null &
for _ in $(seq 120); do
  if curl -sf --max-time 2 localhost:8000/readyz >/dev/null; then
    echo "ProtocolLedger is ready on port 8000 (log: /tmp/protocolledger.log)"
    exit 0
  fi
  sleep 1
done
echo "ProtocolLedger did not become ready in 2 minutes; see /tmp/protocolledger.log" >&2
exit 1
