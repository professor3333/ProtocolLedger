"""Deploy the public SciBERT demo to an Oracle Cloud Always Free VM over SSH.

    uv run python scripts/deploy_oracle.py --host <public-ip>

Steps (each stops on failure):
1. refuse unless the working tree is clean and HEAD is on GitHub (the VM builds HEAD);
2. upload and run deploy/oracle/bootstrap.sh (Docker, host firewall, uv; idempotent);
3. on the VM: check out HEAD, build the SciBERT image, download the model bundle from
   Hugging Face at a pinned revision, and activate it with scripts/release.py, which
   smoke-tests and restores the previous release on failure;
4. from here: check https://<ip>.sslip.io/readyz serves the expected model.

Uses the dedicated key ~/.ssh/protocolledger_oci; first contact records the VM's host key
(accept-new), and a changed host key is refused.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_REPO = "professor3333/protocolledger-scibert"
MODEL_REVISION = "905ca6ebea0d1acfcc5204df99aea827b243fd44"
MODEL_VERSION = "scibert-uniform-negatives-s21-7dc7a1893e"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", required=True, help="the VM's public IPv4 address")
    parser.add_argument("--user", default="ubuntu")
    parser.add_argument("--key", type=Path, default=Path.home() / ".ssh" / "protocolledger_oci")
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args(argv)

    if git("status", "--porcelain", "--untracked-files=no"):
        raise SystemExit("error: commit your changes first; the VM builds a pushed commit")
    commit = git("rev-parse", "HEAD")
    git("fetch", "--quiet", "origin")
    if not git("branch", "-r", "--contains", commit):
        raise SystemExit(f"error: {commit[:10]} is not on GitHub")
    site = f"{args.host}.sslip.io"
    target = f"{args.user}@{args.host}"
    ssh = [
        "ssh",
        "-i",
        str(args.key),
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        "ConnectTimeout=20",
        target,
    ]

    def run(command: str) -> None:
        print(f"[vm] {command.splitlines()[0][:100]}", flush=True)
        subprocess.run([*ssh, command], check=True)

    subprocess.run(
        [
            "scp",
            "-i",
            str(args.key),
            "-o",
            "StrictHostKeyChecking=accept-new",
            str(ROOT / "deploy/oracle/bootstrap.sh"),
            f"{target}:bootstrap.sh",
        ],
        check=True,
    )
    run("bash bootstrap.sh")
    short = commit[:10]
    remote = f"""set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
[ -d ProtocolLedger ] || git clone --quiet https://github.com/professor3333/ProtocolLedger.git
cd ProtocolLedger
git fetch --quiet origin && git checkout --quiet {commit}
docker build -q --build-arg EXTRAS=serve-neural -t protocolledger:{short} . >/dev/null
uv sync --quiet --locked --extra serve-neural
if [ ! -f artifacts/bundles/{MODEL_VERSION}/bundle.json ]; then
  DL='import sys; from huggingface_hub import snapshot_download as d
d(sys.argv[1], revision=sys.argv[2], local_dir=sys.argv[3])'
  uv run python -c "$DL" {MODEL_REPO} {MODEL_REVISION} artifacts/bundles/{MODEL_VERSION}
  rm -rf artifacts/bundles/{MODEL_VERSION}/.cache
fi
PROTOCOLLEDGER_THREADS={args.threads} uv run python scripts/release.py activate \\
  --image protocolledger:{short} --bundle artifacts/bundles/{MODEL_VERSION} \\
  --reason "public demo at {short}" --site-address {site} --public-demo
"""
    run(remote)

    url = f"https://{site}/readyz"
    for _ in range(30):
        try:
            with urllib.request.urlopen(url, timeout=20) as res:
                body = json.loads(res.read())
            break
        except OSError:
            time.sleep(10)  # Caddy may still be obtaining the certificate
    else:
        print(f"error: {url} did not become reachable", file=sys.stderr)
        return 1
    ok = body.get("model_version") == MODEL_VERSION and body.get("public_demo") is True
    print(f"{url}: {body.get('model_version')} public_demo={body.get('public_demo')}")
    print(f"demo: https://{site}" if ok else "error: unexpected model or demo flag")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
