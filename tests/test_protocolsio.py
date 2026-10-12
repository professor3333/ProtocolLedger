from typing import Any

from protocolledger.data.convert import step_spans
from protocolledger.data.protocolsio import (
    CleanStep,
    Lexicons,
    ProtocolIndex,
    build_text,
    challenge_tags,
    clean_steps,
    html_to_lines,
    looks_english,
    quantity_share,
    select_challenge,
    usable,
)

ACTIONS = frozenset({"add", "mix", "incubate", "centrifuge", "remove"})


def step(step_id: int, text: str, section: str = "Procedure") -> CleanStep:
    return CleanStep(step_id=step_id, number=str(step_id), section=section, lines=(text,))


def test_components_render_as_visible_text() -> None:
    html = (
        '<p>Dilute OP50 (10<sup>12</sup> cfu/mL) 1:100 in <span class="component-amount">'
        '100 µL</span>  M9 buffer.</p><p>Shake at <span class="component-centrifuge">'
        '200 rpm, 22 °C, </span> for<span class="component-duration">03:00:00</span> .</p>'
    )
    lines, dropped, seen = html_to_lines(html)
    assert lines == [
        "Dilute OP50 (10¹² cfu/mL) 1:100 in 100 µL M9 buffer.",
        "Shake at 200 rpm, 22 °C, for03:00:00 .",
    ]
    assert not dropped
    assert seen == {"component-amount": 1, "component-centrifuge": 1, "component-duration": 1}


def test_notes_tables_and_figures_are_dropped_and_counted() -> None:
    html = (
        '<p>Add buffer.</p><figure><div class="component-note"><p>Light-sensitive.</p>'
        '</div></figure><table class="component-table"><tr><td>dH2O</td><td>780 µL</td>'
        '</tr></table><p>Mix&nbsp;gently.</p><img src="x.png">'
    )
    lines, dropped, _ = html_to_lines(html)
    assert lines == ["Add buffer.", "Mix\u00a0gently."]  # the NBSP survives
    assert dropped == {"figure": 1, "component-table": 1, "img": 1}


def test_unmappable_superscripts_stay_plain_and_bad_markup_is_tolerated() -> None:
    lines, _, _ = html_to_lines("<p>Use CaCl<sub>2</sub> at 10<sup>th</sup> step<b>.</p>")
    assert lines == ["Use CaCl₂ at 10th step."]


def test_each_step_is_one_line_after_the_title() -> None:
    steps, _ = clean_steps(
        [
            {
                "id": 1,
                "number": "1",
                "section": "<p>Day 1</p>",
                "step": "<p>Add 5 mL<br>water.</p>",
            },
            {"id": 2, "number": "2", "section": None, "step": "<p>Mix.</p><p>Spin down.</p>"},
        ]
    )
    text, index = build_text("My  protocol", steps)
    assert text == "My protocol\nAdd 5 mL water.\nMix. Spin down.\n"
    assert [e["line"] for e in index] == [1, 2]
    assert index[0]["section"] == "Day 1"
    spans = step_spans(text)
    assert [text[s:e] for s, e in spans] == ["My protocol", "Add 5 mL water.", "Mix. Spin down."]


def test_usable_step_rules() -> None:
    assert usable(step(1, "Add 5 mL water to the tube."), ACTIONS) is None
    assert usable(step(1, "Add water.", "Introduction"), ACTIONS) == "section"
    assert usable(step(1, "Add it"), ACTIONS) == "too-short"
    assert usable(step(1, " ".join(["add"] * 121)), ACTIONS) == "too-long"
    assert usable(step(1, "This protocol describes our method."), ACTIONS) == "no-action-word"
    assert usable(CleanStep(1, "1", "Procedure", ()), ACTIONS) == "empty"


def test_language_and_quantity_checks() -> None:
    assert looks_english(["Add 5 mL of water to the tube and mix with a pipette."])
    assert not looks_english(["Ajouter 5 mL d'eau dans le tube puis mélanger doucement."])
    steps = [step(1, "Add 5 mL water."), step(2, "Mix well."), step(3, "Spin at 4 °C.")]
    assert quantity_share(steps) == 2 / 3


def lexicons() -> Lexicons:
    text = "Add water. Mix PBS. Incubate."
    labels = {"Add": "Action", "water": "Reagent", "Mix": "Action", "PBS": "Reagent"}
    labels["Incubate"] = "Action"
    entities: list[dict[str, Any]] = []
    for surface, label in labels.items():
        start = text.index(surface)
        entities.append({"label": label, "start": start, "end": start + len(surface)})
    return Lexicons.from_train([{"text": text, "entities": entities}] * 3)


def test_challenge_categories() -> None:
    lex = lexicons()
    assert lex.actions == {"add", "mix", "incubate"}
    tags = challenge_tags("Add water, mix and incubate; add water again if needed.", lex)
    assert tags == ["multiple_actions", "repeated_materials", "conditional_wording"]
    assert challenge_tags("Incubate 5\u201310 min at 37 °C.", lex) == ["ranges", "unusual_symbols"]
    assert challenge_tags("Resuspend it in buffer.", lex) == ["implicit_references"]
    assert challenge_tags("Wait \u2013 then go\u2026", lex) == []  # ordinary typography


def test_challenge_selection_is_round_robin_and_capped_per_protocol() -> None:
    pool = [
        ("p1", step(1, "a"), ["ranges"]),
        ("p1", step(2, "b"), ["ranges", "conditional_wording"]),
        ("p1", step(3, "c"), ["ranges"]),
        ("p2", step(4, "d"), ["ranges"]),
        ("p2", step(5, "e"), ["conditional_wording"]),
    ]
    picked = select_challenge(pool, per_category=2, per_protocol=1)
    assert [(s, st.step_id) for s, st, _ in picked] == [("p1", 1), ("p2", 5)]
    picked = select_challenge(pool, per_category=2, per_protocol=3)
    # step 2 carries both categories, so it counts toward both
    assert [st.step_id for _, st, _ in picked] == [1, 2, 5]
    assert picked == select_challenge(pool, per_category=2, per_protocol=3)


def test_protocol_index_uses_the_dedup_rule() -> None:
    base = "Title A\n" + " ".join(f"word{i}" for i in range(200))
    index = ProtocolIndex()
    index.add("wnut2020/train/protocol_1", base)
    assert index.match(base) == "wnut2020/train/protocol_1"
    assert index.match(base.replace("word199", "other")) == "wnut2020/train/protocol_1"
    assert index.match("Title B\n" + " ".join(f"term{i}" for i in range(200))) is None
