"""Deploy the public SciBERT demo to an Ubuntu 24.04 VM over SSH.

    uv run python scripts/deploy_vm.py --host <public-ip> --threads <vCPUs>

Steps (each stops on failure):
1. refuse unless the working tree is clean and HEAD is on GitHub (the VM builds HEAD);
2. upload and run deploy/vm/bootstrap.sh (Docker, swap, host firewall, uv; idempotent);
3. on the VM: check out HEAD, build the SciBERT image, download the model bundle from
   Hugging Face at a pinned revision, and activate it with scripts/release.py, which
   smoke-tests and restores the previous release on failure;
4. from here: check https://<ip>.sslip.io/readyz serves the expected model.

Uses the dedicated key ~/.ssh/protocolledger_vm; first contact records the VM's host key
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

from fetch_demo_bundle import MODEL_VERSION  # scripts/ is on sys.path

ROOT = Path(__file__).resolve().parents[1]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", required=True, help="the VM's public IPv4 address")
    parser.add_argument("--user", default="ubuntu")
    parser.add_argument("--key", type=Path, default=Path.home() / ".ssh" / "protocolledger_vm")
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
            str(ROOT / "deploy/vm/bootstrap.sh"),
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
uv run python scripts/fetch_demo_bundle.py >/dev/null
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
