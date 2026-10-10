"""Write a tiny, deterministic model bundle for CI container smoke tests.

    uv run python scripts/make_fixture_bundle.py /tmp/bundles/fixture

The model is fit on synthetic protocols in the shape of the worked example; it exists
only to exercise packaging, loading and the API in a real container, never for quality.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from protocolledger.baselines.crf_entities import CRFConfig, CRFTagger
from protocolledger.baselines.logreg_relations import LogRegConfig, LogRegRelations
from protocolledger.serve.bundle import write_traditional_bundle


def synthetic(i: int) -> dict[str, Any]:
    text = f"Example protocol\nAdd {i + 2} mL of water to the tube, then mix for {i + 10} s.\n"

    def ent(eid: str, label: str, surface: str) -> dict[str, Any]:
        start = text.index(surface)
        return {"id": eid, "label": label, "start": start, "end": start + len(surface)}

    return {
        "doc_id": f"fixture/protocol_{i}",
        "text": text,
        "entities": [
            ent("T1", "Action", "Add"),
            ent("T2", "Amount", f"{i + 2} mL"),
            ent("T3", "Reagent", "water"),
            ent("T4", "Location", "tube"),
            ent("T5", "Action", "mix"),
            ent("T6", "Time", f"{i + 10} s"),
        ],
        "relations": [
            {"head": "T1", "label": "Acts-on", "tail": "T3"},
            {"head": "T3", "label": "Measure", "tail": "T2"},
            {"head": "T1", "label": "Site", "tail": "T4"},
            {"head": "T5", "label": "Setting", "tail": "T6"},
        ],
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    docs = [synthetic(i) for i in range(20)]
    tagger = CRFTagger.fit(docs, CRFConfig(max_iterations=80))
    relations = LogRegRelations.fit(docs, LogRegConfig(C=10.0))
    path = write_traditional_bundle(
        Path(sys.argv[1]), tagger, relations, "fixture", {"evaluation": {"note": "CI fixture"}}
    )
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
