from typing import Any

from protocolledger.baselines.rules import RulesConfig, RulesModel, clause_spans
from protocolledger.text.tokenize import tokenize


def test_tokenizer_splits_digits_from_letters_and_keeps_offsets() -> None:
    text = "Spin 14,000xg for 30s at 4\u00b0C in 0.5 \u00b5l."
    toks = tokenize(text)
    assert [t.text for t in toks] == [
        "Spin", "14,000", "xg", "for", "30", "s", "at", "4", "\u00b0", "C",
        "in", "0.5", "\u00b5l", ".",
    ]  # fmt: skip
    assert all(text[t.start : t.end] == t.text for t in toks)


def doc(doc_id: str, text: str, ents: list[tuple[str, str, str]], rels: Any = ()) -> dict[str, Any]:
    """Build a gold document; entities are (id, label, surface) found left to right."""
    entities, cursor = [], 0
    for eid, label, surface in ents:
        start = text.index(surface, cursor)
        entities.append(
            {
                "id": eid,
                "label": label,
                "start": start,
                "end": start + len(surface),
                "text": surface,
            }
        )
        cursor = start + len(surface)
    relations = [{"head": h, "label": lab, "tail": t} for h, lab, t in rels]
    return {"doc_id": doc_id, "text": text, "entities": entities, "relations": relations}


TRAIN = [
    doc(
        "train/protocol_1",
        "Title\nAdd 5 mL of water to the tube, then mix for 30 s.\n",
        [
            ("T1", "Action", "Add"),
            ("T2", "Amount", "5 mL"),
            ("T3", "Reagent", "water"),
            ("T4", "Location", "tube"),
            ("T5", "Action", "mix"),
            ("T6", "Time", "30 s"),
        ],
        [
            ("T1", "Acts-on", "T3"),
            ("T3", "Measure", "T2"),
            ("T1", "Site", "T4"),
            ("T5", "Setting", "T6"),
        ],
    ),
    doc(
        "train/protocol_2",
        "Title\nAdd 10 mL of water to the tube; incubate for 5-10 min.\n"
        "Add 1 mM EDTA. Cut 2 mm of tubing. Adjust to pH 8.0.\n",
        [
            ("T1", "Action", "Add"),
            ("T2", "Amount", "10 mL"),
            ("T3", "Reagent", "water"),
            ("T4", "Location", "tube"),
            ("T5", "Action", "incubate"),
            ("T6", "Time", "5-10 min"),
            ("T7", "Action", "Add"),
            ("T8", "Concentration", "1 mM"),
            ("T9", "Reagent", "EDTA"),
            ("T10", "Action", "Cut"),
            ("T11", "Size", "2 mm"),
            ("T12", "Reagent", "tubing"),
            ("T13", "Action", "Adjust"),
            ("T14", "pH", "pH 8.0"),
        ],
        [
            ("T1", "Acts-on", "T3"),
            ("T3", "Measure", "T2"),
            ("T1", "Site", "T4"),
            ("T5", "Setting", "T6"),
            ("T7", "Acts-on", "T9"),
            ("T9", "Measure", "T8"),
        ],
    ),
]

CONFIG = RulesConfig(unit_min_count=1, lexicon_min_count=1)


def labelled(pred: dict[str, Any], text: str) -> list[tuple[str, str]]:
    return [(text[e["start"] : e["end"]], e["label"]) for e in pred["entities"]]


def test_units_are_case_sensitive_and_ranges_and_prefixes_match() -> None:
    model = RulesModel.fit(TRAIN, CONFIG)
    assert model.units["|mM"]["label"] == "Concentration"
    assert model.units["|mm"]["label"] == "Size"
    text = "Title\nAdd 3 mM salt, cut 4 mm, wait 2-3 min at pH 7.5.\n"
    found = labelled({"entities": model.predict_entities(text)}, text)
    assert ("3 mM", "Concentration") in found
    assert ("4 mm", "Size") in found
    assert ("2-3 min", "Time") in found
    assert ("pH 7.5", "pH") in found


def test_lexicon_is_case_insensitive_and_longest_match() -> None:
    model = RulesModel.fit(TRAIN, CONFIG)
    text = "Title\nADD water to the TUBE.\n"
    found = labelled({"entities": model.predict_entities(text)}, text)
    assert found == [("ADD", "Action"), ("water", "Reagent"), ("TUBE", "Location")]


def test_low_precision_phrases_are_dropped() -> None:
    # "tube" is annotated once but appears unannotated three more times.
    noisy = doc(
        "train/protocol_3",
        "Title\nLabel the tube. Rinse the tube. Store the tube.\n",
        [],
    )
    model = RulesModel.fit([*TRAIN, noisy], RulesConfig(unit_min_count=1, lexicon_min_count=1))
    assert "tube" not in model.lexicon


def test_clauses_split_on_punctuation_and_then() -> None:
    text = "Title\nAdd water, then mix; spin.\n"
    clauses = [text[s:e] for s, e in clause_spans(text)]
    assert clauses == ["Title", "Add water, ", "then mix;", " spin."]


def test_relations_attach_to_nearest_compatible_span() -> None:
    model = RulesModel.fit(TRAIN, CONFIG)
    gold = TRAIN[0]
    pred = model.predict(gold, gold_entities=True)
    triples = {(r["head"], r["label"], r["tail"]) for r in pred["relations"]}
    assert ("T3", "Measure", "T2") in triples  # 5 mL measures the water, not the action
    assert ("T1", "Acts-on", "T3") in triples
    assert ("T5", "Setting", "T6") in triples  # 30 s belongs to mix, across "then" boundary


def test_end_to_end_prediction_on_unseen_text() -> None:
    model = RulesModel.fit(TRAIN, CONFIG)
    text = "Title\nAdd 2 mL of water to the tube.\n"
    pred = model.predict({"doc_id": "x", "text": text, "entities": []})
    spans = {e["id"]: text[e["start"] : e["end"]] for e in pred["entities"]}
    triples = {(spans[r["head"]], r["label"], spans[r["tail"]]) for r in pred["relations"]}
    assert ("water", "Measure", "2 mL") in triples
    assert ("Add", "Acts-on", "water") in triples


def test_model_round_trips_through_json() -> None:
    model = RulesModel.fit(TRAIN, CONFIG)
    clone = RulesModel.from_json(model.to_json())
    text = "Title\nAdd 2 mL of water to the tube, then mix for 30 s.\n"
    probe = {"doc_id": "x", "text": text, "entities": []}
    assert clone.predict(probe) == model.predict(probe)
