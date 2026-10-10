"""Precision-coverage and calibration report for scored dev predictions.

    uv run python scripts/calibrate.py --pred artifacts/traditional/dev-end_to_end-scored.jsonl \\
        --name crf-logreg

Writes reports/calibration/<name>-dev.{json,md}; the fitted calibrator (isotonic step
function) is included in the JSON for later use by a model bundle. Dev only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from protocolledger.data.splits import load_split
from protocolledger.eval.confidence import confidence_report

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pred", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument(
        "--joint", action="store_true", help="score = P(relation) x P(head) x P(tail)"
    )
    args = parser.parse_args(argv)
    dev = load_split(ROOT, "dev")
    preds = [json.loads(line) for line in args.pred.read_text("utf-8").splitlines() if line]
    report = confidence_report(dev, preds, joint=args.joint)
    out = ROOT / "reports" / "calibration"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{args.name}-dev.json").write_text(json.dumps(report, indent=1) + "\n", "utf-8")

    t = report["target"]
    p30, c95 = t["precision_at_30pct_coverage"], t["coverage_at_95pct_precision"]
    cal = report["calibration"]
    lines = [
        f"# Confidence: {args.name} (dev, end-to-end relations)",
        "",
        f"{report['predicted_relations']} scored predictions; {report['gold_relations']} gold; "
        f"score = {report['score']}.",
        "",
        "| Target | Result |",
        "|---|---|",
        f"| Precision at 30% coverage | {p30['precision']:.3f} "
        f"[{p30['precision_ci95'][0]:.3f}, {p30['precision_ci95'][1]:.3f}] ({p30['kept']} kept) |",
        f"| Coverage at 95% precision | {c95['coverage']:.1%} ({c95['kept']} kept) |",
        f"| ECE before / after isotonic calibration | {cal['before']['ece']:.3f} / "
        f"{cal['after']['ece']:.3f} |",
        f"| Brier before / after | {cal['before']['brier']:.3f} / {cal['after']['brier']:.3f} |",
        "",
        "| Coverage | Kept | Score ≥ | Precision | Retained recall |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in report["precision_coverage"]:
        lines.append(
            f"| {row['coverage']:.0%} | {row['kept']} | {row['score_threshold']:.3f} | "
            f"{row['precision']:.3f} | {row['retained_recall']:.3f} |"
        )
    (out / f"{args.name}-dev.md").write_text("\n".join(lines) + "\n", "utf-8")
    print("\n".join(lines[4:10]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
