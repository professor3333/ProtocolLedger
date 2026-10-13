import csv
import io
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from protocolledger.serve.app import create_app
from protocolledger.serve.reviews import ReviewError, ReviewStore

TEXT = "Example\nAdd 5 mL of water to the tube, then mix for 30 s at -80 \u00b0C.\n"


def span(surface: str) -> tuple[int, int]:
    start = TEXT.index(surface)
    return start, start + len(surface)


def ent(eid: str, label: str, surface: str, **extra: Any) -> dict[str, Any]:
    start, end = span(surface)
    return {
        "id": eid,
        "label": label,
        "start": start,
        "end": end,
        "origin": "model",
        "decision": "accepted",
        **extra,
    }


def content() -> dict[str, Any]:
    return {
        "entities": [
            ent("P1", "Action", "Add"),
            ent("P2", "Amount", "5 mL"),
            ent("P3", "Reagent", "water"),
            ent("P4", "Location", "tube", decision="rejected"),
            ent("P5", "Action", "mix"),
            ent("P6", "Time", "30 s"),
            ent("H1", "Temperature", "-80 \u00b0C", origin="human", decision="added"),
        ],
        "relations": [
            {
                "id": "R1",
                "head": "P1",
                "label": "Acts-on",
                "tail": "P3",
                "origin": "model",
                "decision": "accepted",
            },
            {
                "id": "R2",
                "head": "P3",
                "label": "Measure",
                "tail": "P2",
                "origin": "model",
                "decision": "accepted",
            },
            {
                "id": "R3",
                "head": "P1",
                "label": "Site",
                "tail": "P4",
                "origin": "model",
                "decision": "rejected",
            },
            {
                "id": "R4",
                "head": "P5",
                "label": "Setting",
                "tail": "P6",
                "origin": "model",
                "decision": "accepted",
            },
            {
                "id": "H2",
                "head": "P5",
                "label": "Setting",
                "tail": "H1",
                "origin": "human",
                "decision": "added",
            },
        ],
    }


# ------------------------------------------------------------------- store


def test_store_is_append_only_and_survives_restart(tmp_path: Path) -> None:
    db = tmp_path / "reviews.db"
    store = ReviewStore(db)
    created = store.create({"v": 1}, "h", None, "m1", None)
    assert created.token
    store.add_revision(created.review_id, created.token, {"v": 2})
    reopened = ReviewStore(db)  # a fresh process opening the same file
    record = reopened.get(created.review_id, created.token)
    assert record["revision"] == 2 and record["content"] == {"v": 2}
    assert [h["revision"] for h in record["history"]] == [1, 2]
    with sqlite3.connect(db) as raw, pytest.raises(sqlite3.DatabaseError, match="append-only"):
        raw.execute("UPDATE revisions SET payload = '{}'")
    with sqlite3.connect(db) as raw, pytest.raises(sqlite3.DatabaseError, match="append-only"):
        raw.execute("DELETE FROM revisions")
    assert sqlite3.connect(db).execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_wrong_token_and_missing_review_are_indistinguishable(tmp_path: Path) -> None:
    store = ReviewStore(tmp_path / "r.db")
    created = store.create({}, "h", None, "m", None)
    for review_id, token in [
        (created.review_id, "wrong"),
        (created.review_id, None),
        ("missing", created.token),
    ]:
        with pytest.raises(ReviewError) as info:
            store.get(review_id, token)
        assert (info.value.status, info.value.detail) == (404, "review not found")


def test_reissued_token_replaces_the_old_one_and_keeps_revisions(tmp_path: Path) -> None:
    store = ReviewStore(tmp_path / "r.db")
    older = store.create({"v": 0}, "h", "text", "manual-annotation", None)
    created = store.create({"v": 1}, "h", "text", "manual-annotation", None)
    store.create({"v": 9}, "h", "text", "some-model", None)
    store.create({"v": 9}, "other", "text", "manual-annotation", None)
    store.add_revision(created.review_id, created.token, {"v": 2})
    found = store.find("h", "manual-annotation")
    assert [r["id"] for r in found] == [older.review_id, created.review_id]
    assert all(r["stored"] for r in found) and len(store.find("h")) == 3
    token = store.reissue_token(created.review_id)
    record = store.get(created.review_id, token)
    assert record["revision"] == 2 and record["content"] == {"v": 2}
    with pytest.raises(ReviewError):
        store.get(created.review_id, created.token)
    with pytest.raises(ReviewError):
        store.reissue_token("missing")


def test_idempotent_creation(tmp_path: Path) -> None:
    store = ReviewStore(tmp_path / "r.db")
    first = store.create({"a": 1}, "h", None, "m", "key-1")
    retry = store.create({"a": 1}, "h", None, "m", "key-1")
    assert retry.review_id == first.review_id and retry.token is None
    with pytest.raises(ReviewError) as info:
        store.create({"a": 2}, "h", None, "m", "key-1")
    assert info.value.status == 409


def test_backup_restores(tmp_path: Path) -> None:
    store = ReviewStore(tmp_path / "live.db")
    created = store.create({"a": 1}, "h", "text", "m", None)
    store.backup(tmp_path / "backup.db")
    restored = ReviewStore(tmp_path / "backup.db")
    assert restored.get(created.review_id, created.token)["text"] == "text"


# --------------------------------------------------------------------- API


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(None, tmp_path / "reviews.db")) as c:
        yield c


def create(client: TestClient, **overrides: Any) -> Any:
    body = {"text": TEXT, "save_text": False, "model_version": "test-model", "content": content()}
    body.update(overrides)
    return client.post("/v1/reviews", json=body)


def test_create_read_revise_without_storing_text(client: TestClient) -> None:
    res = create(client)
    assert res.status_code == 201
    review = res.json()
    headers = {"X-Review-Token": review["token"]}
    record = client.get(f"/v1/reviews/{review['id']}", headers=headers).json()
    assert record["text"] is None and len(record["text_sha256"]) == 64
    assert client.get(f"/v1/reviews/{review['id']}").status_code == 404
    revised = content()
    revised["relations"][2]["decision"] = "accepted"
    revised["entities"][3]["decision"] = "accepted"
    res = client.post(
        f"/v1/reviews/{review['id']}/revisions",
        headers=headers,
        json={"text": TEXT, "content": revised},
    )
    assert res.status_code == 201 and res.json() == {"revision": 2}
    wrong = client.post(
        f"/v1/reviews/{review['id']}/revisions",
        headers=headers,
        json={"text": TEXT + "x", "content": revised},
    )
    assert wrong.status_code == 409


def test_idempotency_key_header(client: TestClient) -> None:
    a = create(client, model_version="m").json()
    b = client.post(
        "/v1/reviews",
        headers={"Idempotency-Key": "k"},
        json={"text": TEXT, "model_version": "m", "content": content()},
    ).json()
    c = client.post(
        "/v1/reviews",
        headers={"Idempotency-Key": "k"},
        json={"text": TEXT, "model_version": "m", "content": content()},
    ).json()
    assert b["id"] == c["id"] != a["id"] and c["token"] is None


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda c: c["entities"][6].update(origin="model"), "human entities"),
        (lambda c: c["entities"][0].update(decision="edited"), "must record its original"),
        (lambda c: c["entities"][0].update(end=10_000), "outside the text"),
        (lambda c: c["entities"][0].update(label="Banana"), "unknown entity label"),
        (lambda c: c["relations"][2].update(decision="accepted"), "rejected entity"),
        (lambda c: c["relations"][0].update(tail="Z9"), "unknown endpoint"),
    ],
)
def test_invalid_reviews_are_rejected(client: TestClient, mutate: Any, message: str) -> None:
    body = content()
    mutate(body)
    res = create(client, content=body)
    assert res.status_code == 422 and message in res.json()["detail"]


def test_export_json_and_csv_mark_humans_and_keep_provenance(client: TestClient) -> None:
    review = create(client, save_text=True).json()
    headers = {"X-Review-Token": review["token"]}
    url = f"/v1/reviews/{review['id']}/export"
    data = client.post(url, headers=headers, json={"format": "json"}).json()
    assert data["rejected"] == {"entities": ["P4"], "relations": ["R3"]}
    human = next(e for e in data["entities"] if e["id"] == "H1")
    assert human["origin"] == "human" and human["normalized"]["value"] == -80
    assert data["model_version"] == "test-model" and data["revision"] == 1
    res = client.post(url, headers=headers, json={"format": "csv"})
    assert res.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(res.text)))
    mix = next(r for r in rows if r["action"].startswith("mix"))
    assert "-80 \u00b0C [human]" in mix["conditions"]
    assert rows[0]["materials"].startswith("water")
    assert rows[0]["quantities"].startswith("5 mL (of water)")


def test_export_requires_text_when_it_was_not_stored(client: TestClient) -> None:
    review = create(client).json()
    headers = {"X-Review-Token": review["token"]}
    url = f"/v1/reviews/{review['id']}/export"
    assert client.post(url, headers=headers, json={"format": "json"}).status_code == 409
    assert client.post(url, headers=headers, json={"text": "other"}).status_code == 409
    assert client.post(url, headers=headers, json={"text": TEXT}).status_code == 200


def test_csv_neutralizes_formulas_but_keeps_negative_numbers(client: TestClient) -> None:
    text = "Title\n=HYPERLINK(1) -80 \u00b0C\n"
    start = text.index("=")
    body = {
        "text": text,
        "save_text": True,
        "model_version": "m",
        "content": {
            "entities": [
                {
                    "id": "P1",
                    "label": "Action",
                    "start": start,
                    "end": start + 13,
                    "origin": "model",
                    "decision": "accepted",
                },
                {
                    "id": "P2",
                    "label": "Temperature",
                    "start": text.index("-80"),
                    "end": text.index("-80") + 6,
                    "origin": "model",
                    "decision": "accepted",
                },
            ],
            "relations": [
                {
                    "id": "R1",
                    "head": "P1",
                    "label": "Setting",
                    "tail": "P2",
                    "origin": "model",
                    "decision": "accepted",
                }
            ],
        },
    }
    review = client.post("/v1/reviews", json=body).json()
    res = client.post(
        f"/v1/reviews/{review['id']}/export",
        headers={"X-Review-Token": review["token"]},
        json={"format": "csv"},
    )
    row = next(csv.DictReader(io.StringIO(res.text)))
    assert row["action"].startswith("'=HYPERLINK")
    assert row["conditions"].startswith("-80")


def test_reviews_unavailable_without_storage(tmp_path: Path) -> None:
    with TestClient(create_app(None)) as c:
        res = c.post("/v1/reviews", json={"text": TEXT, "model_version": "m", "content": content()})
        assert res.status_code == 503


def test_preview_recomputes_the_sheet_from_an_edited_graph(client: TestClient) -> None:
    edited = content()
    # Supply the missing object of "mix" and move "5 mL" from the water to the action.
    edited["relations"].append(
        {
            "id": "H3",
            "head": "P5",
            "label": "Acts-on",
            "tail": "P3",
            "origin": "human",
            "decision": "added",
        }
    )
    edited["relations"][1]["decision"] = "rejected"
    edited["relations"].append(
        {
            "id": "H4",
            "head": "P1",
            "label": "Measure",
            "tail": "P2",
            "origin": "human",
            "decision": "added",
        }
    )
    res = client.post("/v1/preview", json={"text": TEXT, "content": edited})
    assert res.status_code == 200
    body = res.json()
    add, mix = body["sheet"]
    assert add["materials"] == ["P3"] and add["quantities"] == [{"entity": "P2", "of": "P1"}]
    assert add["locations"] == []  # the tube was rejected
    assert mix["materials"] == ["P3"] and mix["status"] == "proposed"
    assert body["normalized_values"]["H1"]["value"] == -80
    assert body["review_items"] == []


def test_preview_rejects_invalid_graphs(client: TestClient) -> None:
    edited = content()
    edited["relations"][2]["decision"] = "accepted"  # points at the rejected tube
    res = client.post("/v1/preview", json={"text": TEXT, "content": edited})
    assert res.status_code == 422 and "rejected entity" in res.json()["detail"]
