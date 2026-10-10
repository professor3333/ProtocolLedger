import json
from pathlib import Path
from typing import Any

import pytest

torch = pytest.importorskip("torch")
transformers = pytest.importorskip("transformers")

from protocolledger.neural.predict import predict_documents  # noqa: E402
from protocolledger.neural.train import load_best, train, training_type_pairs  # noqa: E402
from protocolledger.serve.bundle import BundleError, load_bundle  # noqa: E402
from protocolledger.serve.neural_bundle import write_neural_bundle  # noqa: E402
from tests.test_neural import DOCS, _config, make_encoder, make_tokenizer  # noqa: E402


@pytest.fixture(scope="module")
def trained(tmp_path_factory: pytest.TempPathFactory) -> tuple[Any, Any, set[Any], Path]:
    tmp = tmp_path_factory.mktemp("neural")
    tok = make_tokenizer(tmp)
    cpu = torch.device("cpu")
    train(
        _config(epochs=15),
        make_encoder(tok),
        32,
        tok,
        DOCS,
        DOCS[:4],
        tmp / "run",
        device=cpu,
        log=lambda _: None,
    )
    model, pairs, _ = load_best(tmp / "run" / "best.pt", make_encoder(tok), cpu)
    bundle = write_neural_bundle(
        tmp / "bundle", model, tok, pairs, "tiny-neural", {"evaluation": {}}
    )
    return model, tok, pairs, bundle


def test_bundle_reproduces_direct_predictions(trained: Any) -> None:
    model, tok, pairs, bundle = trained
    loaded = load_bundle(bundle)
    assert loaded.model_version == "tiny-neural"
    assert loaded.version_info()["quantization"] == "none"
    text = DOCS[5]["text"]
    direct = predict_documents(
        model, tok, [{"doc_id": "input", "text": text}], pairs, torch.device("cpu")
    )[0]
    entities, relations = loaded.extractor.extract(text)
    assert entities == direct["entities"] and relations == direct["relations"]
    assert all("score" in e for e in entities)


def test_bundle_is_self_contained_and_tensor_only(trained: Any) -> None:
    *_, bundle = trained
    manifest = json.loads((bundle / "bundle.json").read_text())
    names = set(manifest["files"])
    assert "model.safetensors" in names and "encoder/config.json" in names
    assert any(n.startswith("tokenizer/") for n in names)
    assert not any(n.endswith((".pt", ".pkl", ".bin")) for n in names)


def test_tampered_weights_are_refused(trained: Any, tmp_path: Path) -> None:
    *_, bundle = trained
    copy = tmp_path / "copy"
    for f in bundle.rglob("*"):
        if f.is_file():
            target = copy / f.relative_to(bundle)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(f.read_bytes())
    data = bytearray((copy / "model.safetensors").read_bytes())
    data[-1] ^= 0xFF
    (copy / "model.safetensors").write_bytes(bytes(data))
    with pytest.raises(BundleError, match="hash mismatch"):
        load_bundle(copy)


def test_type_pairs_round_trip(trained: Any) -> None:
    *_, bundle = trained
    manifest = json.loads((bundle / "bundle.json").read_text())
    assert {tuple(p) for p in manifest["type_pairs"]} == training_type_pairs(DOCS)
