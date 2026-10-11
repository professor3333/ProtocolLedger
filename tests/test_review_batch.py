from pathlib import Path
from typing import Any

import pytest

from protocolledger.data.review_batch import (
    BatchError,
    apply_curation,
    curation_template,
    export_reviews,
    leakage,
)
from protocolledger.serve.reviews import ReviewStore

TEXT = "Title\nAdd 5 mL of water to the tube, then mix for 30 s.\n"


def ent(eid: str, label: str, surface: str, **extra: Any) -> dict[str, Any]:
    start = TEXT.index(surface)
    return {
        "id": eid,
        "label": label,
        "start": start,
        "end": start + len(surface),
        "origin": "model",
        "decision": "accepted",
        **extra,
    }


def content() -> dict[str, Any]:
    return {
        "entities": [
            ent("P1", "Action", "Add"),
            ent("P2", "Reagent", "water"),
            ent("P3", "Location", "tube", decision="rejected"),
            ent("H1", "Amount", "5 mL", origin="human", decision="added"),
        ],
        "relations": [
            {
                "id": "R1",
                "head": "P1",
                "label": "Acts-on",
                "tail": "P2",
                "origin": "model",
                "decision": "accepted",
            },
            {
                "id": "R2",
                "head": "P1",
                "label": "Site",
                "tail": "P3",
                "origin": "model",
                "decision": "rejected",
            },
            {
                "id": "H2",
                "head": "P2",
                "label": "Measure",
                "tail": "H1",
                "origin": "human",
                "decision": "added",
            },
        ],
    }


@pytest.fixture
def store(tmp_path: Path) -> Path:
    db = tmp_path / "reviews.db"
    s = ReviewStore(db)
    kept = s.create(content(), "hash", TEXT, "model-1", None)
    s.add_revision(kept.review_id, kept.token, content())
    s.create(content(), "hash2", None, "model-1", None)  # text not stored
    return db


def test_export_uses_latest_revision_drops_rejections_and_skips_textless(store: Path) -> None:
    docs, counts = export_reviews(store)
    assert counts == {"reviews": 2, "exported": 1, "skipped_no_text": 1}
    (doc,) = docs
    assert doc["doc_id"].endswith("/r2")
    assert {e["id"] for e in doc["entities"]} == {"P1", "P2", "H1"}
    assert {(r["head"], r["label"], r["tail"]) for r in doc["relations"]} == {
        ("P1", "Acts-on", "P2"),
        ("P2", "Measure", "H1"),
    }
    assert all(TEXT[e["start"] : e["end"]] == e["text"] for e in doc["entities"])
    assert (
        doc["provenance"]["reviewer_changes"] == 4
    )  # 1 added entity, 1 added relation, 2 rejected


def test_curation_starts_excluded_and_requires_reasons(store: Path) -> None:
    docs, _ = export_reviews(store)
    curation = curation_template(docs)
    assert [c["include"] for c in curation] == [False]
    with pytest.raises(BatchError, match="nothing to train on"):
        apply_curation(docs, curation)
    curation[0]["include"] = True
    with pytest.raises(BatchError, match="reason"):
        apply_curation(docs, curation)
    curation[0]["reason"] = "checked against the source protocol"
    assert len(apply_curation(docs, curation)) == 1
    with pytest.raises(BatchError, match="unknown"):
        apply_curation(docs, [*curation, {"doc_id": "nope", "include": True, "reason": "x"}])


def test_leakage_of_protected_protocols_is_detected() -> None:
    protected = [
        {
            "doc_id": "dev_data/protocol_1",
            "text": TEXT.replace("Title", "Protocol title") + "Spin briefly at 4000 g.\n",
        }
    ]
    leaked = [{"doc_id": "review/a/r1", "text": protected[0]["text"]}]
    fresh = [
        {"doc_id": "review/b/r1", "text": "Other\nHeat the oven to 200 C for one hour today.\n"}
    ]
    assert [x["candidate"] for x in leakage(leaked, protected)] == ["review/a/r1"]
    assert leakage(fresh, protected) == []
