import json
from pathlib import Path
from typing import Any

import pytest

from protocolledger.data.annotation_sets import (
    MANUAL,
    AnnotationSetError,
    assign_split,
    gold_from_reviews,
    load_sources,
    text_sha256,
)
from protocolledger.eval.scorer import evaluate
from protocolledger.serve.reviews import ReviewStore

TEXT = "Title\nAdd 5 mL of water to the tube.\n"


def source(source_id: str, text: str = TEXT) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "url": f"https://www.protocols.io/view/{source_id}",
        "title": "Title",
        "authors": ["A. Author"],
        "version": 1,
        "published": "2025-01-01",
        "license": "CC BY 4.0",
        "text": text,
        "text_sha256": text_sha256(text),
        "split": assign_split(source_id),
    }


def content() -> dict[str, Any]:
    def e(eid: str, label: str, surface: str) -> dict[str, Any]:
        start = TEXT.index(surface)
        return {
            "id": eid,
            "label": label,
            "start": start,
            "end": start + len(surface),
            "origin": "human",
            "decision": "added",
        }

    return {
        "entities": [e("H1", "Action", "Add"), e("H2", "Reagent", "water")],
        "relations": [
            {
                "id": "H3",
                "head": "H1",
                "label": "Acts-on",
                "tail": "H2",
                "origin": "human",
                "decision": "added",
            }
        ],
    }


def test_split_assignment_is_deterministic_and_roughly_balanced() -> None:
    splits = [assign_split(f"protocol-{i}") for i in range(400)]
    assert splits == [assign_split(f"protocol-{i}") for i in range(400)]
    assert 150 < splits.count("test") < 250


def test_sources_are_validated(tmp_path: Path) -> None:
    bad = source("p1")
    bad["text"] = "tampered"
    (tmp_path / "sources.jsonl").write_text(json.dumps(bad) + "\n")
    with pytest.raises(AnnotationSetError, match="hash"):
        load_sources(tmp_path)


def test_only_from_scratch_annotations_become_gold(tmp_path: Path) -> None:
    db = tmp_path / "reviews.db"
    store = ReviewStore(db)
    store.create(content(), text_sha256(TEXT), TEXT, MANUAL, None)
    store.create(content(), text_sha256(TEXT), TEXT, "some-model", None)  # model-assisted
    gold, counts = gold_from_reviews(db, [source("p1")], "later-domain")
    assert counts["annotated"] == 1 and counts["ignored_reviews"] == 1
    (doc,) = gold
    assert doc["doc_id"] == "later-domain/p1" and doc["source"]["license"] == "CC BY 4.0"
    assert doc["steps"] == [[0, 5], [6, len(TEXT) - 1]]
    pred = {"doc_id": doc["doc_id"], "entities": doc["entities"], "relations": doc["relations"]}
    assert evaluate(gold, [pred], resamples=1)["relations"]["micro"]["f1"] == 1.0
