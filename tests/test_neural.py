import random
from pathlib import Path
from typing import Any

import pytest

torch = pytest.importorskip("torch")
transformers = pytest.importorskip("transformers")

from protocolledger.eval.scorer import evaluate  # noqa: E402
from protocolledger.neural.batching import encode_batch, sample_targets, subword_counter  # noqa: E402
from protocolledger.neural.config import ENCODERS, NeuralConfig, preserves_case  # noqa: E402
from protocolledger.neural.encoding import Coverage, build_examples  # noqa: E402
from protocolledger.neural.model import range_max, sparse_table  # noqa: E402
from protocolledger.neural.predict import predict_documents  # noqa: E402
from protocolledger.neural.train import load_best, train, training_type_pairs  # noqa: E402
from protocolledger.text.normalize import encoder_view  # noqa: E402


def test_sparse_table_range_max_matches_brute_force() -> None:
    gen = torch.Generator().manual_seed(0)
    words = torch.randn(3, 13, 5, generator=gen)
    table = sparse_table(words)
    queries = [(b, s, e) for b in range(3) for s in range(13) for e in range(s + 1, 14)]
    batch, start, end = (torch.tensor(x) for x in zip(*queries, strict=True))
    got = range_max(table, batch, start, end)
    want = torch.stack([words[b, s:e].max(dim=0).values for b, s, e in queries])
    assert torch.allclose(got, want)


def test_encoder_view_only_substitutes_unrepresentable_characters() -> None:
    assert encoder_view("5 \xb5L") == "5 \u03bcL"
    assert encoder_view("4 \xbaC") == "4 \xb0C"
    assert encoder_view("37\u2103") == "37\xb0C"
    assert encoder_view("Tris-HCl mM") == "Tris-HCl mM"


def test_encoder_specs_are_pinned_and_cased() -> None:
    for spec in ENCODERS.values():
        assert len(spec.revision) == 40
        assert dict(spec.tokenizer_kwargs)["do_lower_case"] is False


# ----------------------------------------------------------- tiny fixtures

VOCAB_WORDS = [
    "Protocol",
    "Add",
    "mix",
    "Spin",
    "of",
    "water",
    "to",
    "the",
    "tube",
    "then",
    "for",
    "s",
    "mL",
    "min",
    ".",
    ",",
    "buffer",
    "at",
    "x",
    "g",
    "Incubate",
    "in",
    "ice",
]


def make_tokenizer(tmp: Path) -> Any:
    chars = sorted(set("".join(VOCAB_WORDS)) | set("0123456789"))
    vocab = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]", *VOCAB_WORDS, *chars]
    vocab += [f"##{c}" for c in chars]
    (tmp / "vocab.txt").write_text("\n".join(dict.fromkeys(vocab)), "utf-8")
    return transformers.BertTokenizerFast.from_pretrained(str(tmp), do_lower_case=False)


def make_encoder(tokenizer: Any) -> Any:
    torch.manual_seed(0)
    config = transformers.BertConfig(
        vocab_size=len(tokenizer),
        hidden_size=32,
        num_hidden_layers=1,
        num_attention_heads=2,
        intermediate_size=64,
        max_position_embeddings=128,
    )
    return transformers.BertModel(config)


def ent(eid: str, label: str, text: str, surface: str, after: int = 0) -> dict[str, Any]:
    start = text.index(surface, after)
    return {"id": eid, "label": label, "start": start, "end": start + len(surface)}


def make_doc(i: int) -> dict[str, Any]:
    text = f"Protocol {i}\nAdd {i + 1} mL of water to the tube, then mix for {i + 3} s.\n"
    entities = [
        ent("T1", "Action", text, "Add"),
        ent("T2", "Amount", text, f"{i + 1} mL"),
        ent("T3", "Reagent", text, "water"),
        ent("T4", "Location", text, "tube"),
        ent("T5", "Action", text, "mix"),
        ent("T6", "Time", text, f"{i + 3} s"),
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
        "steps": [],
        "entities": entities,
        "relations": relations,
    }


DOCS = [make_doc(i) for i in range(12)]
for _d in DOCS:
    from protocolledger.data.convert import step_spans

    _d["steps"] = [list(s) for s in step_spans(_d["text"])]


def test_examples_map_gold_to_word_spans_and_count_coverage(tmp_path: Path) -> None:
    tok = make_tokenizer(tmp_path)
    cov = Coverage()
    doc = dict(DOCS[0])
    doc["entities"] = [*doc["entities"], {"id": "T9", "label": "Reagent", "start": 12, "end": 14}]
    (title, step) = build_examples(doc, 3, subword_counter(tok), 510, cov)
    assert title.entities == []
    words = step.word_texts
    spans = {" ".join(words[s:e]): lab for s, e, lab in step.entities}
    assert spans == {
        "Add": "Action",
        "1 mL": "Amount",
        "water": "Reagent",
        "tube": "Location",
        "mix": "Action",
        "3 s": "Time",
    }
    assert len(step.relations) == 4
    assert cov.entities == 7 and cov.entities_misaligned == 1  # "dd" is inside "Add"
    narrow = Coverage()
    build_examples(DOCS[0], 1, subword_counter(tok), 510, narrow)
    assert narrow.entities_too_wide == 2  # "1 mL" and "3 s"
    assert narrow.relations_unreachable == 2


def test_long_steps_are_windowed_and_cross_window_relations_counted(tmp_path: Path) -> None:
    tok = make_tokenizer(tmp_path)
    cov = Coverage()
    examples = build_examples(DOCS[0], 10, subword_counter(tok), 4, cov)
    assert len(examples) > 2
    assert all(
        sum(len(tok.tokenize(encoder_view(w))) for w in ex.word_texts) <= 4 for ex in examples
    )
    assert cov.relations_unreachable > 0


def test_sampling_keeps_all_gold_and_bounds_negatives(tmp_path: Path) -> None:
    tok = make_tokenizer(tmp_path)
    examples = [ex for d in DOCS[:3] for ex in build_examples(d, 4, subword_counter(tok), 510)]
    cfg = NeuralConfig(max_span_words=4, negative_spans=5, negative_pairs=3)
    ent_index = {
        lab: i + 1
        for i, lab in enumerate(sorted({"Action", "Amount", "Reagent", "Location", "Time"}))
    }
    rel_index = {lab: i for i, lab in enumerate(["Acts-on", "Measure", "Setting", "Site"])}
    t = sample_targets(
        examples, cfg, random.Random(0), ent_index, rel_index, training_type_pairs(DOCS)
    )
    gold_spans = sum(len(ex.entities) for ex in examples)
    assert int((t.span_label > 0).sum()) == gold_spans
    assert int((t.span_label == 0).sum()) <= 5 * len(examples)
    assert int(t.pair_labels.sum()) == sum(len(ex.relations) for ex in examples)
    batch = encode_batch(tok, examples)
    assert batch.word_index.max() == batch.num_words - 1


def _config(**overrides: Any) -> NeuralConfig:
    base = dict(
        max_span_words=4,
        batch_size=4,
        epochs=25,
        patience=25,
        learning_rate=3e-3,
        head_learning_rate=1e-2,
        warmup_fraction=0.0,
        negative_spans=20,
        negative_pairs=10,
        dropout=0.0,
        mixed_precision=False,
        seed=3,
    )
    base.update(overrides)
    return NeuralConfig(**base)


def test_tiny_model_overfits_training_documents(tmp_path: Path) -> None:
    tok = make_tokenizer(tmp_path)
    encoder = make_encoder(tok)
    cpu = torch.device("cpu")
    result = train(
        _config(),
        encoder,
        32,
        tok,
        DOCS,
        DOCS[:4],
        tmp_path / "run",
        device=cpu,
        log=lambda _: None,
    )
    assert result.best_dev_relation_f1 > 0.9
    model, pairs, _ = load_best(tmp_path / "run" / "best.pt", make_encoder(tok), cpu)
    preds = predict_documents(model, tok, DOCS[:4], pairs, cpu)
    report = evaluate(DOCS[:4], preds, resamples=1)
    assert report["relations"]["micro"]["f1"] == pytest.approx(result.best_dev_relation_f1)
    for p, d in zip(preds, DOCS[:4], strict=True):
        for e in p["entities"]:
            assert 0 <= e["start"] < e["end"] <= len(d["text"])


def test_interrupted_training_resumes_to_the_same_result(tmp_path: Path) -> None:
    tok = make_tokenizer(tmp_path)
    cpu = torch.device("cpu")
    cfg = _config(epochs=4, patience=10)
    full = train(
        cfg,
        make_encoder(tok),
        32,
        tok,
        DOCS,
        DOCS[:4],
        tmp_path / "full",
        device=cpu,
        log=lambda _: None,
    )

    class Interrupt(Exception):
        pass

    def stop_after_epoch_1(message: str) -> None:
        if message.startswith("epoch 1"):
            raise Interrupt

    with pytest.raises(Interrupt):
        train(
            cfg,
            make_encoder(tok),
            32,
            tok,
            DOCS,
            DOCS[:4],
            tmp_path / "cut",
            device=cpu,
            log=stop_after_epoch_1,
        )
    resumed = train(
        cfg,
        make_encoder(tok),
        32,
        tok,
        DOCS,
        DOCS[:4],
        tmp_path / "cut",
        device=cpu,
        log=lambda _: None,
    )
    assert len(resumed.history) == 4
    for a, b in zip(full.history, resumed.history, strict=True):
        assert a["train_loss"] == pytest.approx(b["train_loss"], rel=1e-5)
        assert a["dev_relation_f1"] == b["dev_relation_f1"]


def test_resume_refuses_a_different_config(tmp_path: Path) -> None:
    tok = make_tokenizer(tmp_path)
    cpu = torch.device("cpu")
    train(
        _config(epochs=1),
        make_encoder(tok),
        32,
        tok,
        DOCS[:2],
        DOCS[:1],
        tmp_path / "r",
        device=cpu,
        log=lambda _: None,
    )
    with pytest.raises(RuntimeError, match="different config"):
        train(
            _config(epochs=2),
            make_encoder(tok),
            32,
            tok,
            DOCS[:2],
            DOCS[:1],
            tmp_path / "r",
            device=cpu,
            log=lambda _: None,
        )


def test_case_check_accepts_any_split_but_rejects_lowercasing(tmp_path: Path) -> None:
    whole = tmp_path / "whole"
    split = tmp_path / "split"
    for folder, vocab in (
        (whole, ["mM", "DNA", "MgCl2"]),
        (split, ["m", "##M", "DNA", "Mg", "##Cl2"]),
    ):
        folder.mkdir()
        lines = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]", *vocab, "mm", "dna", "mgcl2"]
        (folder / "vocab.txt").write_text("\n".join(lines), "utf-8")
    for folder in (whole, split):
        cased = transformers.BertTokenizerFast.from_pretrained(str(folder), do_lower_case=False)
        lowered = transformers.BertTokenizerFast.from_pretrained(str(folder), do_lower_case=True)
        assert preserves_case(cased)
        assert not preserves_case(lowered)
