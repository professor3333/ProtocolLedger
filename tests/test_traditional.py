from typing import Any

from protocolledger.baselines.crf_entities import (
    CRFConfig,
    CRFTagger,
    bio_decode,
    bio_encode,
    encode_stats,
)
from protocolledger.baselines.logreg_relations import LogRegConfig, LogRegRelations
from protocolledger.text.tokenize import tokenize


def ent(eid: str, label: str, text: str, surface: str, after: int = 0) -> dict[str, Any]:
    start = text.index(surface, after)
    return {"id": eid, "label": label, "start": start, "end": start + len(surface)}


def test_bio_round_trip() -> None:
    text = "Add 5 mL of cold water."
    toks = tokenize(text)
    ents = [
        ent("T1", "Action", text, "Add"),
        ent("T2", "Amount", text, "5 mL"),
        ent("T3", "Reagent", text, "cold water"),
    ]
    tags, stats = bio_encode(toks, ents)
    assert tags == ["B-Action", "B-Amount", "I-Amount", "O", "B-Reagent", "I-Reagent", "O"]
    assert stats.misaligned == stats.overlapping == 0
    assert bio_decode(toks, tags) == [(e["start"], e["end"], e["label"]) for e in ents]


def test_bio_counts_unrepresentable_entities() -> None:
    text = "Add 100 \u00b5lof buffer."
    toks = tokenize(text)
    # "100 \u00b5l" ends inside the glued token "\u00b5lof".
    glued = {"id": "T1", "label": "Amount", "start": 4, "end": 10}
    outer = ent("T2", "Reagent", text, "buffer")
    inner = {"id": "T3", "label": "Modifier", "start": outer["start"], "end": outer["end"]}
    _, stats = bio_encode(toks, [glued, outer, inner])
    assert (stats.misaligned, stats.overlapping) == (1, 1)


def test_bio_decode_treats_stray_inside_tag_as_new_entity() -> None:
    toks = tokenize("mix well now")
    assert bio_decode(toks, ["I-Action", "B-Modifier", "I-Action"]) == [
        (0, 3, "Action"),
        (4, 8, "Modifier"),
        (9, 12, "Action"),
    ]


def make_doc(i: int) -> dict[str, Any]:
    text = f"Protocol {i}\nAdd {i + 1} mL of water to the tube.\nMix for {i + 2} min.\n"
    entities = [
        ent("T1", "Action", text, "Add"),
        ent("T2", "Amount", text, f"{i + 1} mL"),
        ent("T3", "Reagent", text, "water"),
        ent("T4", "Location", text, "tube"),
        ent("T5", "Action", text, "Mix"),
        ent("T6", "Time", text, f"{i + 2} min"),
    ]
    relations = [
        {"head": "T1", "label": "Acts-on", "tail": "T3"},
        {"head": "T3", "label": "Measure", "tail": "T2"},
        {"head": "T1", "label": "Site", "tail": "T4"},
        {"head": "T5", "label": "Setting", "tail": "T6"},
    ]
    return {
        "doc_id": f"train/protocol_{i}",
        "text": text,
        "entities": entities,
        "relations": relations,
    }


TRAIN = [make_doc(i) for i in range(12)]


def test_crf_learns_a_simple_pattern() -> None:
    tagger = CRFTagger.fit(TRAIN, CRFConfig(max_iterations=50))
    text = "Protocol x\nAdd 7 mL of water to the tube.\n"
    found = {(text[e["start"] : e["end"]], e["label"]) for e in tagger.predict_entities(text)}
    assert {("Add", "Action"), ("7 mL", "Amount"), ("water", "Reagent")} <= found
    assert encode_stats(TRAIN).misaligned == 0


def test_logreg_learns_attachments_and_reports_reachability() -> None:
    model = LogRegRelations.fit(TRAIN, LogRegConfig(C=10.0))
    doc = make_doc(40)
    rels = {
        (r["head"], r["label"], r["tail"])
        for r in model.predict_relations(doc["text"], doc["entities"])
    }
    assert ("T3", "Measure", "T2") in rels
    assert ("T5", "Setting", "T6") in rels
    # A relation across steps cannot be generated as a candidate and is counted.
    crossing = {**doc, "relations": [{"head": "T1", "label": "Setting", "tail": "T6"}]}
    stats = model.reachability([crossing])
    assert (stats.gold, stats.cross_step) == (1, 1)


def test_candidates_stay_within_steps_and_known_type_pairs() -> None:
    model = LogRegRelations.fit(TRAIN, LogRegConfig())
    assert ("Action", "Time") in model.type_pairs
    assert ("Time", "Action") not in model.type_pairs
