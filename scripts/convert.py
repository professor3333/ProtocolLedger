"""Convert the verified raw corpus into canonical JSONL graphs plus a conversion report.

    uv run python scripts/convert.py

Writes data/processed/wnut2020/conversion-v<N>/<split>.jsonl (regenerable, not
committed) and data/manifests/conversion_report.json (committed). Exits non-zero if any
document has an error-level issue or the raw tree does not match the acquisition
manifest.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from protocolledger.data import acquire
from protocolledger.data.convert import CONVERSION_VERSION, Document, build_report, convert_split

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "processed" / "wnut2020" / f"conversion-v{CONVERSION_VERSION}"
REPORT = ROOT / "data" / "manifests" / "conversion_report.json"


def write_jsonl(docs: list[Document], path: Path) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(
        json.dumps(d.to_json(), ensure_ascii=False, separators=(",", ":")) + "\n" for d in docs
    ).encode("utf-8")
    path.write_bytes(payload)
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "documents": len(docs),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def main() -> int:
    paths = acquire.Paths.under(ROOT)
    problems = acquire.verify(paths)
    if problems:
        print(f"error: raw data does not match the manifest: {problems[0]}", file=sys.stderr)
        return 1

    docs_by_split = {}
    for split_dir in acquire.SELECTED_DIRS:
        docs = convert_split(paths.raw, split_dir)
        docs_by_split[docs[0].split] = docs

    errors = [(d.doc_id, i) for docs in docs_by_split.values() for d in docs for i in d.errors]
    for doc_id, err in errors:
        print(f"{doc_id} {err.record}: {err.code}: {err.detail}", file=sys.stderr)
    if errors:
        print(f"error: {len(errors)} error-level issues; nothing written", file=sys.stderr)
        return 1

    outputs = {
        split: write_jsonl(docs, OUT_DIR / f"{split}.jsonl")
        for split, docs in docs_by_split.items()
    }
    report = build_report(docs_by_split, outputs)
    report["source"] = {
        "commit": acquire.COMMIT,
        "acquisition_manifest_sha256": acquire.sha256_file(paths.manifest),
    }
    REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    total = report["total"]
    print(
        f"converted {total['documents']} documents: {total['entities']} entities, "
        f"{total['relations_raw']} relations ({total['relations_merged']} after merging)"
    )
    print(f"wrote {REPORT.relative_to(ROOT)} and {OUT_DIR.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
