"""Error taxonomy and slices for a system's dev predictions.

    uv run python scripts/analyze_errors.py --pred artifacts/traditional/dev-end_to_end.jsonl \\
        --name crf-logreg

Writes reports/errors/<name>-dev.{json,md}. The "unseen reagent names" slice uses names
from the training split only; the template-sibling slice uses splits.json. Test is never
touched.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from protocolledger.data.splits import load_split
from protocolledger.eval.errors import analyze, render_markdown

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pred", type=Path, required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args(argv)
    train, dev = load_split(ROOT, "train"), load_split(ROOT, "dev")
    seen = {
        d["text"][e["start"] : e["end"]].casefold()
        for d in train
        for e in d["entities"]
        if e["label"] == "Reagent"
    }
    dev_names = {
        d["text"][e["start"] : e["end"]].casefold()
        for d in dev
        for e in d["entities"]
        if e["label"] == "Reagent"
    }
    manifest = json.loads((ROOT / "data/manifests/splits.json").read_text("utf-8"))
    siblings = {k for k in manifest["template_siblings"] if k.startswith("dev_data/")}
    preds = [json.loads(line) for line in args.pred.read_text("utf-8").splitlines() if line]
    report = analyze(dev, preds, unseen_names=dev_names - seen, sibling_docs=siblings)
    report["source"] = {"predictions": str(args.pred), "split": "dev"}
    out = ROOT / "reports" / "errors"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{args.name}-dev.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False) + "\n", "utf-8"
    )
    (out / f"{args.name}-dev.md").write_text(render_markdown(report, f"{args.name} (dev)"), "utf-8")
    e, r = report["entities"]["categories"], report["relations"]["categories"]
    print(
        f"{args.name}: entity correct {e['correct']['share']:.1%}; relation causes "
        + ", ".join(
            f"{k} {v['share']:.1%}" for k, v in sorted(r.items(), key=lambda kv: -kv[1]["count"])
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
