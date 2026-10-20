"""Download the served SciBERT bundle from the Hugging Face Hub at its pinned revision.

    uv run python scripts/fetch_demo_bundle.py

Writes artifacts/bundles/<model version>/ and prints its path. Does nothing if the bundle
is already there. The server verifies every file's hash when it loads the bundle, so a
corrupted download is refused at start-up. Used by the Codespaces demo
(.devcontainer/) and by scripts/deploy_vm.py; no token is needed (public repo).
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_REPO = "professor3333/protocolledger-scibert"
MODEL_REVISION = "905ca6ebea0d1acfcc5204df99aea827b243fd44"
MODEL_VERSION = "scibert-uniform-negatives-s21-7dc7a1893e"


def main() -> int:
    target = ROOT / "artifacts" / "bundles" / MODEL_VERSION
    if not (target / "bundle.json").is_file():
        from huggingface_hub import snapshot_download

        snapshot_download(MODEL_REPO, revision=MODEL_REVISION, local_dir=target)
        shutil.rmtree(target / ".cache", ignore_errors=True)
    print(target.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
