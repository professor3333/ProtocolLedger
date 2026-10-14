"""Calibrate an annotator on train protocols before writing new gold.

    uv run python scripts/annotation_warmup.py prepare
    # annotate each file from scratch in the review UI, saving to data/warmup.db
    uv run python scripts/annotation_warmup.py score --db data/warmup.db

--skip N moves to the next protocols in the same fixed order, e.g. when an earlier pair is
no longer a clean test (the annotator saw model output for it). Use the same --skip for
prepare and score.

``prepare`` picks two train protocols about the size of a new-set protocol and writes
their text to artifacts/warmup/. ``score`` compares the from-scratch annotations in the
database with the corpus gold, using the shared scorer and error taxonomy, and writes
artifacts/warmup/report.md. Only train documents are used; artifacts/ is not committed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from protocolledger.data.annotation_sets import select_warmup, warmup_pairs
from protocolledger.data.splits import load_split
from protocolledger.eval.errors import analyze
from protocolledger.eval.errors import render_markdown as render_errors
from protocolledger.eval.scorer import evaluate, render_markdown

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "warmup"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="write the warm-up texts")
    prepare.add_argument("-n", type=int, default=2)
    prepare.add_argument("--skip", type=int, default=0)
    score = sub.add_parser("score", help="compare your annotations with the corpus gold")
    score.add_argument("--db", type=Path, required=True)
    score.add_argument("-n", type=int, default=2)
    score.add_argument("--skip", type=int, default=0)
    args = parser.parse_args(argv)

    docs = select_warmup(load_split(ROOT, "train"), args.skip + args.n)[args.skip :]
    if args.command == "prepare":
        OUT.mkdir(parents=True, exist_ok=True)
        for doc in docs:
            path = OUT / (doc["doc_id"].replace("/", "__") + ".txt")
            path.write_text(doc["text"], "utf-8")
            print(f"{path.relative_to(ROOT)}  ({len(doc['steps'])} steps)")
        print("Serve with PROTOCOLLEDGER_ANNOTATION_ONLY=1 and PROTOCOLLEDGER_DB=data/warmup.db,")
        print("load each file with the upload button, annotate it and save the review.")
        return 0

    gold, mine = warmup_pairs(args.db, docs)
    if not gold:
        raise SystemExit(f"error: no from-scratch annotation of a warm-up text in {args.db}")
    report = evaluate(gold, mine, resamples=200)
    errors = analyze(gold, mine, examples_per_category=15)
    title = f"Warm-up: your annotation vs. the corpus gold ({len(gold)} train protocols)"
    text = render_markdown(report, title) + "\n" + render_errors(errors, "warm-up")
    OUT.mkdir(parents=True, exist_ok=True)
    suffix = f"-skip{args.skip}" if args.skip else ""
    (OUT / f"report{suffix}.md").write_text(text, "utf-8")
    (OUT / f"report{suffix}.json").write_text(
        json.dumps({"scores": report, "errors": errors}, indent=1, ensure_ascii=False) + "\n",
        "utf-8",
    )
    print(render_markdown(report, title))
    print(f"Disagreements with examples: {(OUT / f'report{suffix}.md').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
