"""Launch, monitor and fetch GPU training jobs on Kaggle.

    uv run python scripts/kaggle.py launch --owner <user> scibert-lr5e-5:13 bert-lr5e-5:13
    uv run python scripts/kaggle.py status --owner <user>
    uv run python scripts/kaggle.py fetch  --owner <user> [--checkpoints]

``launch`` refuses to run from a dirty tree or from a commit that is not on GitHub,
because the job clones exactly that commit. ``fetch`` downloads the job's reports
(checkpoints only with ``--checkpoints``) into artifacts/kaggle/<slug>/ and copies the
dev reports into reports/neural/. The Kaggle CLI authenticates from ~/.kaggle; no
credential is ever read, printed or written by this script.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KAGGLE = ["uvx", "--from", "kaggle==2.2.4", "kaggle"]
REPO_URL = "https://github.com/professor3333/ProtocolLedger.git"
DEFAULT_SLUG = "protocolledger-train"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def parse_runs(specs: list[str]) -> list[list[object]]:
    runs: list[list[object]] = []
    for spec in specs:
        name, _, seed = spec.partition(":")
        config = Path("configs/neural") / f"{name}.json"
        if not (ROOT / config).exists():
            raise SystemExit(f"error: no config {config}")
        runs.append([config.as_posix(), int(seed or 13)])
    return runs


def render_job(commit: str, runs: list[list[object]]) -> str:
    template = (ROOT / "kaggle" / "job_template.py").read_text("utf-8")
    job = json.dumps({"repo": REPO_URL, "commit": commit, "runs": runs})
    return template.replace("__JOB_JSON__", job)


def job_dir(slug: str) -> Path:
    return ROOT / "artifacts" / "kaggle" / slug


def launch(args: argparse.Namespace) -> int:
    if git("status", "--porcelain", "--untracked-files=no"):
        print("error: commit your changes first; the job clones a pushed commit", file=sys.stderr)
        return 1
    commit = git("rev-parse", "HEAD")
    git("fetch", "--quiet", "origin")
    if not git("branch", "-r", "--contains", commit):
        print(f"error: {commit[:10]} is not on GitHub; push it first", file=sys.stderr)
        return 1
    runs = parse_runs(args.runs)
    folder = job_dir(args.slug) / "kernel"
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    (folder / "job.py").write_text(render_job(commit, runs), "utf-8")
    metadata = {
        "id": f"{args.owner}/{args.slug}",
        "title": args.slug,
        "code_file": "job.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": True,
        "enable_tpu": False,
        "enable_internet": True,
        "dataset_sources": [],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": [],
    }
    (folder / "kernel-metadata.json").write_text(json.dumps(metadata, indent=1), "utf-8")
    print(f"launching {len(runs)} run(s) at {commit[:10]} on {args.accelerator}")
    return subprocess.run(
        [*KAGGLE, "kernels", "push", "-p", str(folder), "--accelerator", args.accelerator],
        check=False,
    ).returncode


def status(args: argparse.Namespace) -> int:
    return subprocess.run(
        [*KAGGLE, "kernels", "status", f"{args.owner}/{args.slug}"], check=False
    ).returncode


def fetch(args: argparse.Namespace) -> int:
    dest = job_dir(args.slug) / "output"
    dest.mkdir(parents=True, exist_ok=True)
    pattern = r".*" if args.checkpoints else r".*(\.json|\.md|\.log)$"
    command = [*KAGGLE, "kernels", "output", f"{args.owner}/{args.slug}", "-p", str(dest)]
    command += ["--file-pattern", pattern, "-o"]
    code = subprocess.run(command, check=False).returncode
    if code:
        return code
    reports = sorted(dest.rglob("reports/*-dev.json"))
    target = ROOT / "reports" / "neural"
    target.mkdir(parents=True, exist_ok=True)
    for report in reports:
        for suffix in (".json", ".md"):
            src = report.with_suffix(suffix)
            if src.exists():
                shutil.copy2(src, target / src.name)
    status_file = next(iter(dest.rglob("job_status.json")), None)
    if status_file:
        for result in json.loads(status_file.read_text())["results"]:
            print(f"{result['run']}: {result['status']} ({result['minutes']} min)")
    print(f"copied {len(reports)} report(s) to {target.relative_to(ROOT)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("launch", "status", "fetch"):
        p = sub.add_parser(name)
        p.add_argument("--owner", required=True)
        p.add_argument("--slug", default=DEFAULT_SLUG)
        if name == "launch":
            p.add_argument("runs", nargs="+", help="config name[:seed], e.g. scibert-lr5e-5:13")
            p.add_argument("--accelerator", default="NvidiaTeslaT4")
        if name == "fetch":
            p.add_argument("--checkpoints", action="store_true")
    args = parser.parse_args(argv)
    return {"launch": launch, "status": status, "fetch": fetch}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
