"""Build machine-generated labels for an annotation set from its label specs.

    uv run python scripts/build_machine_labels.py --set later-domain

Reads data/annotation/<set>/machine_specs/<source_id>.txt (format: see
parse_label_spec in protocolledger/data/annotation_sets.py), resolves every entity to
exact offsets, and writes data/annotation/<set>/machine_labels.jsonl. These labels are
machine-generated and not human-reviewed; they are kept apart from the human gold.jsonl,
and reports scored against them say so. Relations whose (head type, tail
type) pair occurs fewer than 5 times in train are listed for a second look.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from protocolledger.data.annotation_sets import load_sources, machine_document
from protocolledger.data.splits import load_split

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--set", required=True, dest="set_name")
    parser.add_argument("--quiet", action="store_true", help="do not list rare type pairs")
    args = parser.parse_args(argv)
    set_dir = ROOT / "data" / "annotation" / args.set_name
    sources = load_sources(set_dir)
    pairs: defaultdict[str, Counter[tuple[str, str]]] = defaultdict(Counter)
    for doc in load_split(ROOT, "train"):
        labels = {e["id"]: e["label"] for e in doc["entities"]}
        for r in doc["relations"]:
            pairs[r["label"]][(labels[r["head"]], labels[r["tail"]])] += 1

    docs, missing, rare = [], [], 0
    for source in sources:
        path = set_dir / "machine_specs" / f"{source['source_id']}.txt"
        if not path.exists():
            missing.append(source["source_id"])
            continue
        doc = machine_document(source, args.set_name, path.read_text("utf-8"))
        docs.append(doc)
        by_id = {e["id"]: e for e in doc["entities"]}
        for r in doc["relations"]:
            h, t = by_id[r["head"]], by_id[r["tail"]]
            if pairs[r["label"]][(h["label"], t["label"])] < 5:
                rare += 1
                if not args.quiet:
                    print(
                        f"  rare pair {source['source_id']}: {h['text']} ({h['label']})"
                        f" -{r['label']}-> {t['text']} ({t['label']})"
                    )
    with (set_dir / "machine_labels.jsonl").open("w", encoding="utf-8") as fh:
        for doc in docs:
            fh.write(json.dumps(doc, ensure_ascii=False) + "\n")
    counts = {
        "labelled": len(docs),
        "missing": len(missing),
        "entities": sum(len(d["entities"]) for d in docs),
        "relations": sum(len(d["relations"]) for d in docs),
        "rare_pairs": rare,
    }
    print(f"{args.set_name}: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
