import json
from pathlib import Path
from typing import Any

import pytest

from protocolledger.data import dedup

BASE = (
    "Western blot\nLoad 20 ug of lysate per lane on a 10% gel and run at 120 V for "
    "90 min. Transfer to a PVDF membrane at 100 V for one hour on ice. Block in 5% milk."
)


def test_whitespace_normalized_hash_ignores_whitespace_but_not_case() -> None:
    a = "Add  5 mL\u00a0water.\n"
    assert dedup.whitespace_normalized_sha256(a) == dedup.whitespace_normalized_sha256(
        "Add 5 mL water."
    )
    assert dedup.whitespace_normalized_sha256("Add") != dedup.whitespace_normalized_sha256("add")


def test_title_key_normalizes_case_space_and_trailing_period() -> None:
    assert dedup.title_key("Transformation  Protocol. \nStep") == "transformation protocol"
    assert dedup.title_key("Transformation Protocol") == "transformation protocol"


def test_shingles_of_short_text() -> None:
    assert dedup.shingles("Mix well") == frozenset({("mix", "well")})


def test_similar_pairs_classifies_exact_near_title_and_sibling() -> None:
    texts = {
        "train/protocol_1": BASE,
        "dev/protocol_2": BASE.replace("90 min. ", "90 min.\n"),  # re-segmented copy
        "test/protocol_3": BASE.replace("Block in 5% milk.", "Block in 3% BSA overnight."),
        "train/protocol_4": "Something else entirely\nCentrifuge at 4000 g for 5 min.",
    }
    pairs = {(p.a, p.b): p for p in dedup.similar_pairs(texts)}
    seg = pairs[("dev/protocol_2", "train/protocol_1")]
    assert seg.exact and seg.same_protocol
    assert ("train/protocol_1", "train/protocol_4") not in pairs


def test_same_title_lowers_the_same_protocol_threshold() -> None:
    pair = dedup.Pair("a", "b", jaccard=0.6, same_title=True, exact=False)
    sibling = dedup.Pair("a", "b", jaccard=0.6, same_title=False, exact=False)
    assert pair.same_protocol and not sibling.same_protocol
    assert dedup.Pair("a", "b", 0.86, False, False).same_protocol
    assert not dedup.Pair("a", "b", 0.4, True, False).same_protocol


def test_components_merge_chains() -> None:
    groups = dedup.components(["a", "b", "c", "d"], [("a", "b"), ("c", "b")])
    assert groups == [["a", "b", "c"], ["d"]]


def _pair(a: str, b: str, exact: bool = False) -> dedup.Pair:
    return dedup.Pair(a, b, 1.0 if exact else 0.9, True, exact)


def test_resolve_keeps_most_protected_split_and_never_touches_test() -> None:
    split_of = {
        "train_data/protocol_449": "train",
        "dev_data/protocol_31": "dev",
        "dev_data/protocol_8": "dev",
        "test_data_2020/protocol_0628": "test",
        "train_data/protocol_34": "train",
        "train_data/protocol_135": "train",
        "train_data/protocol_7": "train",
    }
    pairs = [
        _pair("dev_data/protocol_31", "train_data/protocol_449", exact=True),
        _pair("dev_data/protocol_8", "test_data_2020/protocol_0628"),
        _pair("train_data/protocol_135", "train_data/protocol_34", exact=True),
    ]
    kept, exclusions, groups = dedup.resolve(split_of, pairs)
    assert kept == {
        "test": ["test_data_2020/protocol_0628"],
        "dev": ["dev_data/protocol_31"],
        "train": ["train_data/protocol_7", "train_data/protocol_34"],
    }
    assert [(e.doc_id, e.kept, e.reason) for e in exclusions] == [
        ("dev_data/protocol_8", "test_data_2020/protocol_0628", "near_duplicate"),
        ("train_data/protocol_135", "train_data/protocol_34", "exact_duplicate"),
        ("train_data/protocol_449", "dev_data/protocol_31", "exact_duplicate"),
    ]
    assert len(groups) == 3


def test_annotation_agreement_counts_matches() -> None:
    a = {
        "text": "Add water.",
        "entities": [
            {"id": "T1", "label": "Action", "start": 0, "end": 3},
            {"id": "T2", "label": "Reagent", "start": 4, "end": 9},
        ],
        "relations": [{"head": "T1", "label": "Acts-on", "tail": "T2"}],
    }
    b = {
        "text": "Add water.",
        "entities": [
            {"id": "T7", "label": "Action", "start": 0, "end": 3},
            {"id": "T8", "label": "Location", "start": 4, "end": 9},
        ],
        "relations": [{"head": "T7", "label": "Site", "tail": "T8"}],
    }
    counts = dedup.annotation_agreement(a, b)
    assert counts["entities_matched"] == 1 and counts["relations_matched"] == 0
    assert dedup.f1(1, 2, 2) == 0.5
    with pytest.raises(ValueError):
        dedup.annotation_agreement(a, {**b, "text": "Add oil."})


MANIFESTS = Path(__file__).resolve().parents[1] / "data" / "manifests"


def _load(name: str) -> Any:
    return json.loads((MANIFESTS / name).read_text(encoding="utf-8"))


def test_committed_splits_are_disjoint_complete_and_leave_test_intact() -> None:
    splits = _load("splits.json")
    kept = {s: set(v["doc_ids"]) for s, v in splits["splits"].items()}
    excluded = {e["doc_id"] for e in splits["excluded"]}
    all_kept = set().union(*kept.values())
    assert sum(len(v) for v in kept.values()) == len(all_kept)  # disjoint
    assert not all_kept & excluded
    assert len(all_kept) + len(excluded) == 603
    assert len(kept["test"]) == 111  # the locked test split is never reduced
    assert all(e["split"] != "test" for e in splits["excluded"])
    for s, v in splits["splits"].items():
        assert v["documents"] == len(v["doc_ids"]), s


def test_no_same_protocol_pair_survives_across_splits() -> None:
    splits, report = _load("splits.json"), _load("dedup_report.json")
    split_of = {d: s for s, v in splits["splits"].items() for d in v["doc_ids"]}
    for p in report["pairs"]:
        if p["class"] == "same_protocol" and p["a"] in split_of and p["b"] in split_of:
            pytest.fail(f"same-protocol pair kept: {p['a']} / {p['b']}")


def test_committed_report_reproduces_audit_unique_text_count() -> None:
    report = _load("dedup_report.json")
    assert report["documents"] == 603
    assert report["unique_whitespace_normalized_texts"] == 581
