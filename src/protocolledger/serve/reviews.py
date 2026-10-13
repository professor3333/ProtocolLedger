"""Durable review records in SQLite (WAL mode), append-only.

* A review is created by an explicit submission and identified by an unguessable id.
  The creator receives a secret token; only its SHA-256 is stored, and reading or
  revising the review requires it.
* Every submission is stored as a new revision; revisions are never updated or deleted,
  so the correction history is complete.
* Protocol text is stored only when the submitter opts in. Otherwise only its SHA-256
  is kept, and a client reopening the review must supply text with the same hash.
* ``Idempotency-Key`` makes creation safe to retry: the same key with the same payload
  returns the original review instead of creating a duplicate.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    token_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL,
    text_sha256 TEXT NOT NULL,
    text TEXT,
    model_version TEXT NOT NULL,
    idempotency_key TEXT UNIQUE,
    request_sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS revisions (
    review_id TEXT NOT NULL REFERENCES reviews(id),
    number INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    payload TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    PRIMARY KEY (review_id, number)
);
CREATE TRIGGER IF NOT EXISTS revisions_append_only_update
BEFORE UPDATE ON revisions BEGIN SELECT RAISE(ABORT, 'revisions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS revisions_append_only_delete
BEFORE DELETE ON revisions BEGIN SELECT RAISE(ABORT, 'revisions are append-only'); END;
"""


class ReviewError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


@dataclass(frozen=True)
class Created:
    review_id: str
    token: str | None  # None when an idempotent retry returned an existing review
    revision: int


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


class ReviewStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript(SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.execute("PRAGMA foreign_keys=ON")
        db.row_factory = sqlite3.Row
        try:
            yield db
        finally:
            db.close()

    def create(
        self,
        payload: dict[str, Any],
        text_sha256: str,
        text: str | None,
        model_version: str,
        idempotency_key: str | None,
    ) -> Created:
        body = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        request_sha = _sha256(body + text_sha256 + (text or "") + model_version)
        with self._lock, self._connect() as db:
            if idempotency_key:
                row = db.execute(
                    "SELECT id, request_sha256 FROM reviews WHERE idempotency_key = ?",
                    (idempotency_key,),
                ).fetchone()
                if row:
                    if row["request_sha256"] != request_sha:
                        raise ReviewError(409, "Idempotency-Key reused with a different request")
                    return Created(row["id"], None, 1)
            review_id = secrets.token_urlsafe(16)
            token = secrets.token_urlsafe(32)
            now = _now()
            db.execute("BEGIN IMMEDIATE")
            try:
                db.execute(
                    "INSERT INTO reviews VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        review_id,
                        _sha256(token),
                        now,
                        text_sha256,
                        text,
                        model_version,
                        idempotency_key,
                        request_sha,
                    ),
                )
                db.execute(
                    "INSERT INTO revisions VALUES (?, 1, ?, ?, ?)",
                    (review_id, now, body, _sha256(body)),
                )
                db.execute("COMMIT")
            except BaseException:
                db.execute("ROLLBACK")
                raise
            return Created(review_id, token, 1)

    def _authorize(self, db: sqlite3.Connection, review_id: str, token: str | None) -> sqlite3.Row:
        row: sqlite3.Row | None = db.execute(
            "SELECT * FROM reviews WHERE id = ?", (review_id,)
        ).fetchone()
        # Same response for "missing" and "wrong token" so ids cannot be probed.
        if (
            row is None
            or token is None
            or not hmac.compare_digest(row["token_sha256"], _sha256(token))
        ):
            raise ReviewError(404, "review not found")
        return row

    def add_revision(self, review_id: str, token: str | None, payload: dict[str, Any]) -> int:
        body = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        with self._lock, self._connect() as db:
            self._authorize(db, review_id, token)
            db.execute("BEGIN IMMEDIATE")
            try:
                number = db.execute(
                    "SELECT COALESCE(MAX(number), 0) + 1 FROM revisions WHERE review_id = ?",
                    (review_id,),
                ).fetchone()[0]
                db.execute(
                    "INSERT INTO revisions VALUES (?, ?, ?, ?, ?)",
                    (review_id, number, _now(), body, _sha256(body)),
                )
                db.execute("COMMIT")
            except BaseException:
                db.execute("ROLLBACK")
                raise
            return int(number)

    def get(self, review_id: str, token: str | None) -> dict[str, Any]:
        with self._connect() as db:
            row = self._authorize(db, review_id, token)
            revisions = db.execute(
                "SELECT number, created_at, payload, payload_sha256 FROM revisions "
                "WHERE review_id = ? ORDER BY number",
                (review_id,),
            ).fetchall()
        latest = revisions[-1]
        return {
            "id": row["id"],
            "created_at": row["created_at"],
            "text_sha256": row["text_sha256"],
            "text": row["text"],
            "model_version": row["model_version"],
            "revision": latest["number"],
            "updated_at": latest["created_at"],
            "content": json.loads(latest["payload"]),
            "history": [
                {
                    "revision": r["number"],
                    "created_at": r["created_at"],
                    "sha256": r["payload_sha256"],
                }
                for r in revisions
            ],
        }

    def find(self, text_sha256: str, model_version: str | None = None) -> list[dict[str, Any]]:
        """Reviews of one text, oldest first. Local administration only: it bypasses tokens."""
        query = "SELECT id, created_at, model_version, text IS NOT NULL AS stored FROM reviews "
        query += "WHERE text_sha256 = ?"
        args: tuple[str, ...] = (text_sha256,)
        if model_version is not None:
            query += " AND model_version = ?"
            args += (model_version,)
        with self._connect() as db:
            rows = db.execute(query + " ORDER BY created_at, rowid", args).fetchall()
        return [dict(r) | {"stored": bool(r["stored"])} for r in rows]

    def reissue_token(self, review_id: str) -> str:
        """Replace a review's access token and return the new one. Local administration
        only (it needs the database file): the old token stops working, and the review's
        revisions are not touched."""
        token = secrets.token_urlsafe(32)
        with self._lock, self._connect() as db:
            cursor = db.execute(
                "UPDATE reviews SET token_sha256 = ? WHERE id = ?", (_sha256(token), review_id)
            )
            if cursor.rowcount != 1:
                raise ReviewError(404, "review not found")
        return token

    def backup(self, destination: Path) -> None:
        """Consistent online copy (safe while the service is running)."""
        with self._connect() as source, sqlite3.connect(destination) as target:
            source.backup(target)
