"""Publish the served model and the public demo to Hugging Face (free CPU Space).

    uv run --extra neural python scripts/publish_demo.py \\
        --bundle artifacts/bundles/scibert-uniform-negatives-s21-7dc7a1893e

1. Uploads the bundle (hash-verified locally first) and a model card to the model repo.
2. Writes the Space's Dockerfile and README from deploy/huggingface/, pinning the GitHub
   commit (must be pushed) and the model repo revision, and uploads them to the Space.
Uses the Hugging Face login on this machine; no token is read or printed by this script.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

from protocolledger.serve.bundle import load_bundle

ROOT = Path(__file__).resolve().parents[1]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def model_card(model_version: str) -> str:
    card = (ROOT / "docs" / "model_card.md").read_text("utf-8")
    card = card.replace(
        "](dataset_card.md)",
        "](https://github.com/professor3333/ProtocolLedger/blob/main/docs/dataset_card.md)",
    )
    card = card.replace(
        "](../reports/", "](https://github.com/professor3333/ProtocolLedger/blob/main/reports/"
    )
    front = (
        "---\nlicense: apache-2.0\nlanguage: en\nlibrary_name: pytorch\n"
        "base_model: allenai/scibert_scivocab_cased\n"
        "tags: [information-extraction, relation-extraction, named-entity-recognition, "
        "scientific-text, lab-protocols]\n---\n\n"
    )
    usage = (
        "\n## Loading\n\nThis repository is a ProtocolLedger bundle (`bundle.json` lists every "
        "file with its SHA-256). Load it with the project's verified loader:\n\n```python\n"
        "from pathlib import Path\nfrom protocolledger.serve.bundle import load_bundle\n\n"
        f"bundle = load_bundle(Path('{model_version}'))\n"
        "entities, relations = bundle.extractor.extract('Add 5 mL of water to the tube.')\n```\n"
    )
    return front + card + usage


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--owner", default="professor3333")
    parser.add_argument("--model-repo", default="protocolledger-scibert")
    parser.add_argument("--space", default="protocolledger")
    args = parser.parse_args(argv)

    if git("status", "--porcelain", "--untracked-files=no"):
        raise SystemExit("error: commit your changes first; the Space builds a pushed commit")
    commit = git("rev-parse", "HEAD")
    git("fetch", "--quiet", "origin")
    if not git("branch", "-r", "--contains", commit):
        raise SystemExit(f"error: {commit[:10]} is not on GitHub")
    loaded = load_bundle(args.bundle)  # verifies every file before anything is uploaded
    version = loaded.model_version
    api = HfApi()
    model_repo = f"{args.owner}/{args.model_repo}"
    space_repo = f"{args.owner}/{args.space}"

    api.create_repo(model_repo, repo_type="model", exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / "model"
        shutil.copytree(args.bundle, staging)
        (staging / "README.md").write_text(model_card(version), "utf-8")
        info = api.upload_folder(
            repo_id=model_repo,
            folder_path=str(staging),
            commit_message=f"Bundle {version} from {commit[:10]}",
        )
    revision = info.oid
    print(f"model: https://huggingface.co/{model_repo} @ {revision}")

    api.create_repo(space_repo, repo_type="space", space_sdk="docker", exist_ok=True)
    values = {
        "__COMMIT__": commit,
        "__MODEL_REPO__": model_repo,
        "__MODEL_REVISION__": revision,
        "__MODEL_VERSION__": version,
    }
    with tempfile.TemporaryDirectory() as tmp:
        space = Path(tmp)
        for template, name in (
            ("Dockerfile.template", "Dockerfile"),
            ("SPACE_README.template.md", "README.md"),
        ):
            text = (ROOT / "deploy" / "huggingface" / template).read_text("utf-8")
            for key, value in values.items():
                text = text.replace(key, value)
            (space / name).write_text(text, "utf-8")
        api.upload_folder(
            repo_id=space_repo,
            repo_type="space",
            folder_path=str(space),
            commit_message=f"Deploy {version} at {commit[:10]}",
        )
    print(f"space: https://huggingface.co/spaces/{space_repo} (building)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
