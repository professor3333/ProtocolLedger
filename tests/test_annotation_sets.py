import json
from pathlib import Path
from typing import Any

import pytest

from protocolledger.data.annotation_sets import (
    MANUAL,
    AnnotationSetError,
    agreement_pairs,
    assign_split,
    gold_from_reviews,
    load_sources,
    machine_document,
    parse_label_spec,
    select_warmup,
    text_sha256,
    warmup_pairs,
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


WORKED = "Title\nAdd 5 mL of water to the tube, then mix for 30 s.\n"
WORKED_SPEC = """
# the worked example from the project guide
L1
a Action Add
b Amount 5 mL
c Reagent water
d Location tube
e Action mix
f Time 30 s
a Acts-on c
c Measure b
a Site d
e Setting f
"""


def test_label_spec_resolves_exact_offsets() -> None:
    entities, relations = parse_label_spec(WORKED, WORKED_SPEC)
    line = WORKED.index("Add")
    spans = [(e["label"], e["start"] - line, e["end"] - line) for e in entities]
    assert spans == [
        ("Action", 0, 3),
        ("Amount", 4, 8),
        ("Reagent", 12, 17),
        ("Location", 25, 29),
        ("Action", 36, 39),
        ("Time", 44, 48),
    ]
    assert all(WORKED[e["start"] : e["end"]] == e["text"] for e in entities)
    by_id = {e["id"]: e["text"] for e in entities}
    triples = [(by_id[r["head"]], r["label"], by_id[r["tail"]]) for r in relations]
    assert triples == [
        ("Add", "Acts-on", "water"),
        ("water", "Measure", "5 mL"),
        ("Add", "Site", "tube"),
        ("mix", "Setting", "30 s"),
    ]


def test_label_spec_occurrences_and_word_boundaries() -> None:
    text = "T\nmix cells, remix cells and mix again\nrinse anddry\n"
    entities, _ = parse_label_spec(
        text,
        "L1\na Action mix\nb Action mix\nc Reagent cells@2\nL2\nd Action ~dry\n",
    )
    starts = [e["start"] for e in entities]
    # "mix" inside "remix" is not a word; the second free "mix" is the one before "again"
    assert starts[0] == text.index("mix cells")
    assert starts[1] == text.index("mix again")
    assert starts[2] == text.index("cells and")
    assert text[starts[3] : starts[3] + 3] == "dry"


def test_label_spec_uses_raw_characters() -> None:
    text = "T\nIncubate at 28\u00a0\u00b0C.\n"
    with pytest.raises(AnnotationSetError, match="not found"):
        parse_label_spec(text, "L1\na Temperature 28 \u00b0C\n")
    entities, _ = parse_label_spec(text, "L1\na Temperature 28\u00a0\u00b0C\n")
    assert text[entities[0]["start"] : entities[0]["end"]] == "28\u00a0\u00b0C"


@pytest.mark.parametrize(
    ("spec", "message"),
    [
        ("a Action Add\n", "no L<n> line"),
        ("L9\na Action Add\n", "lines"),
        ("L1\na Verb Add\n", "unknown label"),
        ("L1\na Action Add\na Action mix\n", "duplicate key"),
        ("L1\na Action Add\nb Action Add@1\n", "already labelled"),
        ("L1\na Action Add\na Acts-on z\n", "unknown entity key"),
        ("L1\na Action Add\nb Reagent water\na Acts-on b\na Acts-on b\n", "duplicate"),
        ("L1\na Action Add\na Acts-on a\n", "self relation"),
        ("L1\na Action\n", "three fields"),
    ],
)
def test_label_spec_rejects_what_it_cannot_resolve(spec: str, message: str) -> None:
    with pytest.raises(AnnotationSetError, match=message):
        parse_label_spec(WORKED, spec)


def test_machine_document_is_kept_apart_from_gold() -> None:
    doc = machine_document(source("pio-1", WORKED), "later-domain", WORKED_SPEC)
    assert doc["doc_id"] == "later-domain/pio-1"
    assert doc["text"] == WORKED
    assert doc["annotation"]["labeller"] != MANUAL
    assert doc["annotation"]["spec_sha256"] == text_sha256(WORKED_SPEC)
    assert doc["source"]["license"] == "CC BY 4.0"
    assert len(doc["entities"]) == 6 and len(doc["relations"]) == 4


def train_doc(doc_id: str, steps: int, words: int) -> dict[str, Any]:
    text = "\n".join(" ".join(["mix"] * (words // steps)) for _ in range(steps))
    return {"doc_id": doc_id, "text": text, "steps": [[0, 1]] * steps}


def test_warmup_selection_is_deterministic_and_size_matched() -> None:
    docs = [train_doc(f"train_data/protocol_{i}", 8, 200) for i in range(20)]
    docs += [train_doc("train_data/long", 30, 900), train_doc("train_data/short", 2, 20)]
    picked = select_warmup(docs, 3)
    assert [d["doc_id"] for d in picked] == [d["doc_id"] for d in select_warmup(docs[::-1], 3)]
    assert len(picked) == 3 and all(
        d["doc_id"] not in ("train_data/long", "train_data/short") for d in picked
    )


def test_warmup_pairs_match_reviews_to_train_gold(tmp_path: Path) -> None:
    db = tmp_path / "warmup.db"
    gold = {
        **source("p1"),
        "doc_id": "train_data/protocol_1",
        "steps": [[0, 5], [6, len(TEXT) - 1]],
    }
    gold.update(entities=[], relations=[])
    store = ReviewStore(db)
    store.create(content(), text_sha256(TEXT), TEXT, MANUAL, None)
    pairs, mine = warmup_pairs(db, [gold])
    assert [d["doc_id"] for d in pairs] == ["train_data/protocol_1"]
    assert [e["label"] for e in mine[0]["entities"]] == ["Action", "Reagent"]
    assert warmup_pairs(db, [{**gold, "text": "other"}]) == ([], [])


def test_agreement_pairs_compare_shared_dev_documents_only() -> None:
    def doc(doc_id: str, split: str, text: str = TEXT) -> dict[str, Any]:
        return {
            "doc_id": doc_id,
            "split": split,
            "text": text,
            "steps": [[0, len(text)]],
            "entities": [],
            "relations": [],
        }

    first = [doc("s/a", "dev"), doc("s/b", "dev"), doc("s/t", "test")]
    second = [doc("s/a", "dev"), doc("s/c", "dev"), doc("s/t", "test")]
    reference, other, counts = agreement_pairs(first, second)
    assert [d["doc_id"] for d in reference] == ["s/a"] == [d["doc_id"] for d in other]
    assert counts == {"compared": 1, "first_only": 1, "second_only": 1}
    with pytest.raises(AnnotationSetError, match="different text"):
        agreement_pairs(first, [doc("s/a", "dev", "changed")])
