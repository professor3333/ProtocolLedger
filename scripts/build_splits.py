"""Deduplicate, apply the correction ledger and freeze the cleaned train/dev/test splits.

    uv run python scripts/build_splits.py                 # verify ledger, build splits
    uv run python scripts/build_splits.py --write-ledger  # (re)generate the ledger

Reads the canonical JSONL written by scripts/convert.py (hash-checked against the
conversion report) and writes:

* data/manifests/corrections.jsonl  committed correction ledger
* data/manifests/dedup_report.json  committed duplicate / near-duplicate evidence
* data/manifests/splits.json        committed split manifest with output hashes
* data/processed/wnut2020/clean-v<N>/{train,dev,test}.jsonl  regenerable, not committed
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from protocolledger.data import corrections as corr
from protocolledger.data import dedup

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = ROOT / "data" / "manifests"
CONVERSION_REPORT = MANIFESTS / "conversion_report.json"
LEDGER = MANIFESTS / "corrections.jsonl"
DEDUP_REPORT = MANIFESTS / "dedup_report.json"
SPLITS = MANIFESTS / "splits.json"
SPLITS_VERSION = "1"
OUT_DIR = ROOT / "data" / "processed" / "wnut2020" / f"clean-v{SPLITS_VERSION}"
SPLIT_NAMES = {"train_data": "train", "dev_data": "dev", "test_data_2020": "test"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_converted() -> dict[str, dict[str, Any]]:
    report = json.loads(CONVERSION_REPORT.read_text(encoding="utf-8"))
    docs: dict[str, dict[str, Any]] = {}
    for split, out in report["outputs"].items():
        path = ROOT / out["path"]
        if not path.exists() or sha256_file(path) != out["sha256"]:
            raise SystemExit(f"error: {out['path']} missing or stale; run scripts/convert.py")
        for line in path.read_text(encoding="utf-8").splitlines():
            doc = json.loads(line)
            doc["split"] = SPLIT_NAMES[split]
            docs[doc["doc_id"]] = doc
    return docs


def agreement_summary(docs: dict[str, dict[str, Any]], pairs: list[dedup.Pair]) -> dict[str, Any]:
    rows = []
    for p in pairs:
        if docs[p.a]["text"] != docs[p.b]["text"]:
            continue
        counts = dedup.annotation_agreement(docs[p.a], docs[p.b])
        rows.append({"a": p.a, "b": p.b, **counts})
    tot = defaultdict(int)
    for row in rows:
        for k, v in row.items():
            if isinstance(v, int):
                tot[k] += v
    return {
        "definition": (
            "Byte-identical duplicate texts annotated separately in the release. Entities "
            "match on (label, start, end); relations on (head span, label, tail span). "
            "Annotator identity is unknown, so this is duplicate-copy agreement, not "
            "inter-annotator agreement."
        ),
        "pairs": len(rows),
        "entity_f1": round(
            dedup.f1(tot["entities_matched"], tot["entities_a"], tot["entities_b"]), 4
        ),
        "relation_f1": round(
            dedup.f1(tot["relations_matched"], tot["relations_a"], tot["relations_b"]), 4
        ),
        "totals": dict(tot),
        "per_pair": rows,
    }


def write_jsonl(docs: list[dict[str, Any]], path: Path) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(
        json.dumps(d, ensure_ascii=False, separators=(",", ":")) + "\n" for d in docs
    ).encode("utf-8")
    path.write_bytes(payload)
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "documents": len(docs),
        "entities": sum(len(d["entities"]) for d in docs),
        "relations": sum(len(d["relations"]) for d in docs),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def dump(obj: Any, path: Path) -> None:
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write-ledger", action="store_true", help="regenerate the ledger")
    args = parser.parse_args(argv)

    docs = load_converted()
    split_of = {d: doc["split"] for d, doc in docs.items()}

    # Correction ledger: committed, and must equal what the rules generate.
    generated = corr.build_ledger(docs[d] for d in sorted(docs))
    if args.write_ledger or not LEDGER.exists():
        corr.write_ledger(generated, LEDGER)
        print(f"wrote {LEDGER.relative_to(ROOT)} ({len(generated)} corrections)")
    elif corr.read_ledger(LEDGER) != generated:
        print(
            "error: committed ledger differs from the rules; review, then --write-ledger",
            file=sys.stderr,
        )
        return 1
    ledger = corr.read_ledger(LEDGER)

    # Duplicates and near-duplicates.
    pairs = dedup.similar_pairs({d: doc["text"] for d, doc in docs.items()})
    kept, exclusions, groups = dedup.resolve(split_of, pairs)
    excluded = {e.doc_id for e in exclusions}
    exact_keys = {dedup.whitespace_normalized_sha256(doc["text"]) for doc in docs.values()}

    siblings: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in pairs:
        if p.same_protocol or p.a in excluded or p.b in excluded:
            continue
        if split_of[p.a] == split_of[p.b]:
            continue
        hi, lo = sorted((p.a, p.b), key=lambda d: dedup.SPLIT_PRIORITY.index(split_of[d]))
        siblings[hi].append({"doc_id": lo, "split": split_of[lo], "jaccard": p.jaccard})

    dedup_report = {
        "rules": {
            "exact": "SHA-256 of whitespace-collapsed text, no case folding",
            "shingle_words": dedup.SHINGLE_WORDS,
            "same_protocol": (
                f"jaccard >= {dedup.SAME_DOC_JACCARD}, or jaccard >= "
                f"{dedup.SAME_TITLE_JACCARD} with equal normalized titles"
            ),
            "template_sibling": f"jaccard >= {dedup.SIBLING_JACCARD}, not same protocol",
            "keeper": "most protected split (test > dev > train), then lowest protocol number",
        },
        "documents": len(docs),
        "unique_whitespace_normalized_texts": len(exact_keys),
        "same_protocol_components": groups,
        "excluded": len(exclusions),
        "pairs": [
            {
                "a": p.a,
                "b": p.b,
                "jaccard": p.jaccard,
                "exact": p.exact,
                "same_title": p.same_title,
                "class": "same_protocol" if p.same_protocol else "template_sibling",
                "cross_split": split_of[p.a] != split_of[p.b],
            }
            for p in pairs
        ],
        "duplicate_copy_agreement": agreement_summary(docs, pairs),
    }

    by_doc: dict[str, list[corr.Correction]] = defaultdict(list)
    for c in ledger:
        by_doc[c.doc_id].append(c)
    outputs = {}
    for split in ("train", "dev", "test"):
        cleaned = [corr.apply_corrections(docs[d], by_doc.get(d, [])) for d in kept[split]]
        outputs[split] = write_jsonl(cleaned, OUT_DIR / f"{split}.jsonl")

    splits = {
        "splits_version": SPLITS_VERSION,
        "sources": {
            "conversion_report_sha256": sha256_file(CONVERSION_REPORT),
            "corrections_sha256": sha256_file(LEDGER),
            "corrections": len(ledger),
        },
        "rules": dedup_report["rules"],
        "splits": {
            split: {**outputs[split], "doc_ids": kept[split]} for split in ("train", "dev", "test")
        },
        "excluded": [e.to_json() for e in exclusions],
        "template_siblings": {k: siblings[k] for k in sorted(siblings)},
    }
    dump(dedup_report, DEDUP_REPORT)
    dump(splits, SPLITS)

    for split in ("train", "dev", "test"):
        o = outputs[split]
        print(
            f"{split:5} {o['documents']:4} docs {o['entities']:6} entities "
            f"{o['relations']:6} relations"
        )
    agree = dedup_report["duplicate_copy_agreement"]
    print(f"excluded {len(exclusions)} documents in {len(groups)} same-protocol groups")
    print(
        f"duplicate-copy agreement over {agree['pairs']} pairs: "
        f"entity F1 {agree['entity_f1']}, relation F1 {agree['relation_f1']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
