import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from protocolledger.baselines.crf_entities import CRFConfig, CRFTagger
from protocolledger.baselines.logreg_relations import LogRegConfig, LogRegRelations
from protocolledger.serve.app import MAX_BODY_BYTES, create_app
from protocolledger.serve.bundle import BundleError, load_bundle, write_traditional_bundle
from protocolledger.serve.schemas import MAX_TEXT_CHARS
from protocolledger.serve.sheet import IMPLICIT_OBJECT, UNATTACHED_QUANTITY, build_sheet

WORKED = "Example\nAdd 5 mL of water to the tube, then mix for 30 s.\n"


def _ent(eid: str, label: str, text: str, surface: str) -> dict[str, Any]:
    start = text.index(surface)
    return {"id": eid, "label": label, "start": start, "end": start + len(surface)}


def _doc(i: int) -> dict[str, Any]:
    text = f"Protocol {i}\nAdd {i + 2} mL of water to the tube, then mix for {i + 10} s.\n"
    ents = [
        _ent("T1", "Action", text, "Add"),
        _ent("T2", "Amount", text, f"{i + 2} mL"),
        _ent("T3", "Reagent", text, "water"),
        _ent("T4", "Location", text, "tube"),
        _ent("T5", "Action", text, "mix"),
        _ent("T6", "Time", text, f"{i + 10} s"),
    ]
    rels = [
        {"head": "T1", "label": "Acts-on", "tail": "T3"},
        {"head": "T3", "label": "Measure", "tail": "T2"},
        {"head": "T1", "label": "Site", "tail": "T4"},
        {"head": "T5", "label": "Setting", "tail": "T6"},
    ]
    return {"doc_id": f"train/protocol_{i}", "text": text, "entities": ents, "relations": rels}


@pytest.fixture(scope="module")
def bundle_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    docs = [_doc(i) for i in range(15)]
    tagger = CRFTagger.fit(docs, CRFConfig(max_iterations=60))
    relations = LogRegRelations.fit(docs, LogRegConfig(C=10.0))
    path = tmp_path_factory.mktemp("bundle") / "tiny"
    return write_traditional_bundle(path, tagger, relations, "tiny-test", {"evaluation": {}})


@pytest.fixture(scope="module")
def client(bundle_dir: Path) -> Iterator[TestClient]:
    with TestClient(create_app(bundle_dir)) as test_client:
        yield test_client


# ------------------------------------------------------------------ sheet


def test_sheet_matches_worked_example_and_never_fills_implicit_object() -> None:
    ents = [
        _ent("e1", "Action", WORKED, "Add"),
        _ent("e2", "Amount", WORKED, "5 mL"),
        _ent("e3", "Reagent", WORKED, "water"),
        _ent("e4", "Location", WORKED, "tube"),
        _ent("e5", "Action", WORKED, "mix"),
        _ent("e6", "Time", WORKED, "30 s"),
    ]
    rels = [
        {"head": "e1", "label": "Acts-on", "tail": "e3"},
        {"head": "e3", "label": "Measure", "tail": "e2"},
        {"head": "e1", "label": "Site", "tail": "e4"},
        {"head": "e5", "label": "Setting", "tail": "e6"},
    ]
    rows, review = build_sheet(ents, rels)
    add, mix = rows
    assert add["materials"] == ["e3"]
    assert add["quantities"] == [{"entity": "e2", "of": "e3"}]
    assert add["locations"] == ["e4"] and add["status"] == "proposed"
    assert mix["materials"] == [] and mix["conditions"] == ["e6"]
    assert mix["status"] == "review_required" and mix["issues"] == [IMPLICIT_OBJECT]
    assert review == [{"entity": "e5", "issue": IMPLICIT_OBJECT}]


def test_unattached_quantity_is_flagged() -> None:
    ents = [_ent("e1", "Action", WORKED, "Add"), _ent("e2", "Amount", WORKED, "5 mL")]
    _, review = build_sheet(ents, [])
    assert {"entity": "e2", "issue": UNATTACHED_QUANTITY} in review


# ----------------------------------------------------------------- bundle


def test_bundle_refuses_tampered_files(bundle_dir: Path, tmp_path: Path) -> None:
    copy = tmp_path / "copy"
    copy.mkdir()
    for f in bundle_dir.iterdir():
        (copy / f.name).write_bytes(f.read_bytes())
    (copy / "logreg.pkl").write_bytes(b"not the original model")
    with pytest.raises(BundleError, match="hash mismatch"):
        load_bundle(copy)


def test_bundle_refuses_paths_outside_itself(bundle_dir: Path, tmp_path: Path) -> None:
    copy = tmp_path / "copy"
    copy.mkdir()
    for f in bundle_dir.iterdir():
        (copy / f.name).write_bytes(f.read_bytes())
    manifest = json.loads((copy / "bundle.json").read_text())
    manifest["files"]["crf"]["path"] = "../crf.crfsuite"
    (copy / "bundle.json").write_text(json.dumps(manifest))
    with pytest.raises(BundleError, match="outside"):
        load_bundle(copy)


def test_bundles_are_immutable(bundle_dir: Path) -> None:
    loaded = load_bundle(bundle_dir)
    assert loaded.model_version == "tiny-test"
    with pytest.raises(BundleError, match="immutable"):
        write_traditional_bundle(bundle_dir, None, None, "x", {})  # type: ignore[arg-type]


# -------------------------------------------------------------------- API


def test_health_and_readiness(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}
    ready = client.get("/readyz")
    assert ready.status_code == 200
    assert ready.json()["model_version"] == "tiny-test"


def test_not_ready_without_a_bundle(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "missing")) as c:
        assert c.get("/healthz").status_code == 200
        assert c.get("/readyz").status_code == 503
        assert c.post("/v1/extract", json={"text": "Add water."}).status_code == 503


def test_extract_returns_evidence_linked_graph(client: TestClient) -> None:
    text = "Protocol x\nAdd 7 mL of water to the tube, then mix for 40 s.\n"
    res = client.post("/v1/extract", json={"text": text})
    assert res.status_code == 200
    body = res.json()
    assert body["schema_version"] == "1"
    assert body["offsets"] == "unicode_code_points"
    assert body["model"]["model_version"] == "tiny-test"
    for e in body["entities"]:
        assert text[e["start"] : e["end"]] == e["text"]
    ids = {e["id"] for e in body["entities"]}
    assert all(r["head"] in ids and r["tail"] in ids for r in body["relations"])
    labels = {(e["text"], e["label"]) for e in body["entities"]}
    assert {("Add", "Action"), ("7 mL", "Amount"), ("water", "Reagent")} <= labels
    amount = next(e for e in body["entities"] if e["text"] == "7 mL")
    assert body["normalized_values"][amount["id"]]["kind"] == "number"
    assert body["normalized_values"][amount["id"]]["value"] == 7
    assert body["normalized_values"][amount["id"]]["unit"] == "mL"
    assert body["normalization_version"] == "1"
    mix_rows = [row for row in body["sheet"] if row["status"] == "review_required"]
    assert mix_rows, "an action without an object must be routed to review"


def test_offsets_are_code_points_beyond_the_bmp(client: TestClient) -> None:
    text = "\U0001f9ea Protocol\nAdd 7 mL of water to the tube.\n"
    body = client.post("/v1/extract", json={"text": text}).json()
    water = next(e for e in body["entities"] if e["text"] == "water")
    assert text[water["start"] : water["end"]] == "water"


@pytest.mark.parametrize(
    ("payload", "status"),
    [
        ({"text": ""}, 422),
        ({"text": "x" * (MAX_TEXT_CHARS + 1)}, 422),
        ({"text": "Add\x00water"}, 422),
        ({"text": "\n" * 500}, 422),
        ({"text": "Add water", "extra": 1}, 422),
        ({}, 422),
    ],
)
def test_invalid_requests_are_rejected(
    client: TestClient, payload: dict[str, Any], status: int
) -> None:
    res = client.post("/v1/extract", json=payload)
    assert res.status_code == status


def test_lone_surrogate_is_a_clean_422_without_echo(client: TestClient) -> None:
    res = client.post(
        "/v1/extract",
        content=b'{"text": "\\ud800 secret"}',
        headers={"content-type": "application/json"},
    )
    assert res.status_code == 422
    assert "secret" not in res.text


def test_oversized_body_is_413(client: TestClient) -> None:
    res = client.post(
        "/v1/extract",
        content=b'{"text": "' + b"a" * (MAX_BODY_BYTES + 10) + b'"}',
        headers={"content-type": "application/json"},
    )
    assert res.status_code == 413


def test_interface_is_served_with_strict_headers(client: TestClient) -> None:
    page = client.get("/")
    assert page.status_code == 200 and "ProtocolLedger" in page.text
    assert "script-src 'self'" in page.headers["content-security-policy"]
    assert page.headers["x-content-type-options"] == "nosniff"
    js = client.get("/static/app.js")
    assert js.status_code == 200 and "innerHTML" not in js.text
    assert "content-security-policy" not in client.get("/docs").headers


def test_metrics_expose_bounded_labels_and_no_text(client: TestClient) -> None:
    secret = "Protocol x\nAdd 7 mL of zz-secret-reagent to the tube.\n"
    client.post("/v1/extract", json={"text": secret})
    client.get("/v1/reviews/some-random-id-123")
    body = client.get("/metrics").text
    assert 'protocolledger_model_info{bundle_sha256="' in body
    assert 'route="/v1/extract"' in body
    assert 'route="/v1/reviews/{review_id}"' in body
    assert "some-random-id-123" not in body
    assert "zz-secret-reagent" not in body
    assert "protocolledger_extract_input_chars_bucket" in body
    assert 'protocolledger_predicted_entities_total{label="Action"}' in body
