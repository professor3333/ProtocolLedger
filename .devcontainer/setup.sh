#!/usr/bin/env bash
# Install the serving dependencies (CPU PyTorch) and the pinned SciBERT bundle.
# Codespaces runs this once, when the container is created.
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pip install --quiet --no-cache-dir uv==0.12.5
python -m uv sync --quiet --locked --no-dev --extra serve-neural
python -m uv run --no-sync python scripts/fetch_demo_bundle.py
