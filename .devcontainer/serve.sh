#!/usr/bin/env bash
# Start the review service on port 8000 in the background, with the public-demo banner.
# Codespaces runs this on every start. Saved reviews live in /tmp and do not persist.
set -euo pipefail
cd "$(dirname "$0")/.."
bundle=$(python -m uv run --no-sync python scripts/fetch_demo_bundle.py)
PROTOCOLLEDGER_BUNDLE="$bundle" PROTOCOLLEDGER_DB=/tmp/protocolledger-demo.db \
  PROTOCOLLEDGER_PUBLIC_DEMO=1 PROTOCOLLEDGER_THREADS="$(nproc)" \
  setsid nohup .venv/bin/uvicorn --factory protocolledger.serve.app:create_app_from_env \
  --host 0.0.0.0 --port 8000 >/tmp/protocolledger.log 2>&1 </dev/null &
echo "Starting ProtocolLedger on port 8000 (log: /tmp/protocolledger.log)"
