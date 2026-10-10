"""Activate, roll back and inspect releases on a Docker Compose host.

    uv run python scripts/release.py activate --image protocolledger@sha256:... \\
        --bundle artifacts/bundles/crf-logreg-4a9d8cc549 --reason "baseline"
    uv run python scripts/release.py rollback --reason "regression in ..."
    uv run python scripts/release.py status

A release pins **both** the application image (by immutable digest or image id) and the
model bundle (by bundle.json SHA-256). ``activate`` verifies the bundle, records the
release, points deploy/state/active.env at it, restarts the app and runs the smoke
test; if the smoke test fails it automatically restores the previous release. Rollback
restores the previous release's image *and* bundle together. History is append-only
(deploy/state/releases.jsonl).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "deploy"
STATE = DEPLOY / "state"
HISTORY = STATE / "releases.jsonl"
ACTIVE = STATE / "active.env"


def sh(*cmd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)


def resolve_image(image: str) -> str:
    """Immutable reference: the registry digest if pushed, else the local image id."""
    if "@sha256:" in image:
        return image
    out = sh("docker", "image", "inspect", image, "--format", "{{json .RepoDigests}}|{{.Id}}")
    if out.returncode:
        raise SystemExit(f"error: image {image} not found: {out.stderr.strip()}")
    digests, image_id = out.stdout.strip().split("|")
    pushed = json.loads(digests)
    return str(pushed[0]) if pushed else image_id


def bundle_info(bundle: Path) -> dict[str, str]:
    from protocolledger.serve.bundle import load_bundle

    loaded = load_bundle(bundle)  # verifies every file hash
    return {
        "model_version": loaded.model_version,
        "bundle_sha256": hashlib.sha256((bundle / "bundle.json").read_bytes()).hexdigest(),
        "bundles_dir": str(bundle.resolve().parent),
    }


def history() -> list[dict[str, Any]]:
    if not HISTORY.exists():
        return []
    return [json.loads(line) for line in HISTORY.read_text().splitlines() if line.strip()]


def record(entry: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")


def write_env(release: dict[str, Any], args: argparse.Namespace) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    lines = {
        "PROTOCOLLEDGER_IMAGE": release["image"],
        "PROTOCOLLEDGER_MODEL_VERSION": release["model_version"],
        "PROTOCOLLEDGER_BUNDLES_DIR": release["bundles_dir"],
        "PROTOCOLLEDGER_APP_PORT": str(args.app_port),
        "SITE_ADDRESS": args.site_address,
        "HTTP_PORT": str(args.http_port),
        "HTTPS_PORT": str(args.https_port),
    }
    ACTIVE.write_text("".join(f"{k}={v}\n" for k, v in lines.items()))


def compose_up() -> bool:
    out = sh(
        "docker",
        "compose",
        "-f",
        str(DEPLOY / "compose.yaml"),
        "--env-file",
        str(ACTIVE),
        "up",
        "-d",
        "--wait",
        "--wait-timeout",
        "180",
    )
    if out.returncode:
        print(out.stderr.strip()[-2000:], file=sys.stderr)
    return out.returncode == 0


def smoke(release: dict[str, Any], args: argparse.Namespace) -> bool:
    out = sh(
        sys.executable,
        "scripts/smoke_test.py",
        "--base-url",
        f"http://127.0.0.1:{args.app_port}",
        "--expect-model-version",
        release["model_version"],
    )
    print(out.stdout.strip())
    if out.returncode:
        print(out.stderr.strip(), file=sys.stderr)
    return out.returncode == 0


def deploy(release: dict[str, Any], args: argparse.Namespace) -> bool:
    write_env(release, args)
    return compose_up() and smoke(release, args)


def current(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    live = [e for e in entries if e["event"] in ("activated", "rolled_back")]
    return live[-1]["release"] if live else None


def previous(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The most recent good release other than the live one.

    A release is excluded once it has failed its deploy or been rolled back from, so
    repeated rollbacks walk further back instead of reinstalling a rejected release.
    """
    rejected: set[str] = set()
    live_id: str | None = None
    for e in entries:
        if e["event"] == "failed":
            rejected.add(e["release"]["id"])
        elif e["event"] == "rolled_back" and live_id is not None:
            rejected.add(live_id)
        if e["event"] in ("activated", "rolled_back"):
            live_id = e["release"]["id"]
    activated = [e["release"] for e in entries if e["event"] == "activated"]
    for release in reversed(activated):
        if release["id"] != live_id and release["id"] not in rejected:
            return release
    return None


def activate(args: argparse.Namespace) -> int:
    info = bundle_info(Path(args.bundle))
    image = resolve_image(args.image)
    entries = history()
    release = {
        "id": f"r{sum(e['event'] == 'activated' for e in entries) + 1}",
        "image": image,
        **info,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "reason": args.reason,
    }
    replaced = current(entries)
    print(f"activating {release['id']}: {image} + {info['model_version']}")
    if deploy(release, args):
        record(
            {
                "event": "activated",
                "release": release,
                "replaces": replaced["id"] if replaced else None,
            }
        )
        print(f"{release['id']} is live")
        return 0
    record({"event": "failed", "release": release})
    if replaced:
        print(f"smoke test failed; restoring {replaced['id']}", file=sys.stderr)
        ok = deploy(replaced, args)
        record({"event": "rolled_back", "release": replaced, "reason": "automatic"})
        return 1 if ok else 2
    return 1


def rollback(args: argparse.Namespace) -> int:
    entries = history()
    target = previous(entries)
    if target is None:
        print("error: no previous release to roll back to", file=sys.stderr)
        return 1
    print(f"rolling back to {target['id']}: {target['image']} + {target['model_version']}")
    ok = deploy(target, args)
    record({"event": "rolled_back", "release": target, "reason": args.reason})
    return 0 if ok else 1


def status(_: argparse.Namespace) -> int:
    entries = history()
    live = current(entries)
    print(
        json.dumps({"live": live, "previous": previous(entries), "events": len(entries)}, indent=1)
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("activate", "rollback", "status"):
        p = sub.add_parser(name)
        p.add_argument("--app-port", type=int, default=8001)
        p.add_argument("--site-address", default=":80")
        p.add_argument("--http-port", type=int, default=80)
        p.add_argument("--https-port", type=int, default=443)
        if name == "activate":
            p.add_argument("--image", required=True)
            p.add_argument("--bundle", required=True)
        if name in ("activate", "rollback"):
            p.add_argument("--reason", required=True)
    args = parser.parse_args(argv)
    return {"activate": activate, "rollback": rollback, "status": status}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
