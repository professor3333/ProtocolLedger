"""FastAPI service: extraction API plus the static review interface.

Run locally with a model bundle::

    PROTOCOLLEDGER_BUNDLE=artifacts/bundles/<version> \\
        uv run uvicorn --factory protocolledger.serve.app:create_app_from_env

Submitted text is processed in memory and not stored.
"""

from __future__ import annotations

import hashlib
import logging
import os
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any, TypeVar

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from protocolledger.eval.scorer import QUANTITY_LABELS
from protocolledger.serve.bundle import BundleError, LoadedBundle, load_bundle
from protocolledger.serve.export import export_csv, export_json, validate_content
from protocolledger.serve.reviews import ReviewError, ReviewStore
from protocolledger.serve.schemas import (
    MAX_LINES,
    Entity,
    ExportRequest,
    ExtractRequest,
    ExtractResponse,
    ModelInfo,
    NormalizedValue,
    PreviewRequest,
    PreviewResponse,
    Problem,
    Relation,
    ReviewContent,
    ReviewCreate,
    ReviewCreated,
    ReviewItem,
    ReviewRecord,
    ReviewRevision,
    SheetRow,
)
from protocolledger.serve.sheet import build_sheet
from protocolledger.values import VALUES_VERSION, normalize_value

STATIC_DIR = Path(__file__).parent / "static"
MAX_BODY_BYTES = 256 * 1024
DOCS_PATHS = ("/docs", "/redoc")
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}

log = logging.getLogger("protocolledger.serve")
T = TypeVar("T")


def create_app(bundle_dir: Path | None, review_db: Path | None = None) -> FastAPI:
    state: dict[str, LoadedBundle | str | None] = {"bundle": None, "error": None}
    stores: dict[str, ReviewStore] = {}

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if bundle_dir is None:
            state["error"] = "no model bundle configured (set PROTOCOLLEDGER_BUNDLE)"
        else:
            try:
                state["bundle"] = load_bundle(bundle_dir)
            except (BundleError, OSError, ValueError) as exc:
                state["error"] = f"model bundle failed to load: {exc}"
        if state["error"]:
            log.error("%s", state["error"])
        if review_db is not None:
            stores["reviews"] = ReviewStore(review_db)
        yield

    app = FastAPI(
        title="ProtocolLedger",
        version="1",
        summary="Evidence-linked extraction from lab protocols.",
        lifespan=lifespan,
    )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Never echo submitted input back: it may be private, and it may not be encodable
        # (e.g. lone surrogates), which would turn a 422 into a 500.
        errors = [
            {"loc": list(e.get("loc", ())), "msg": str(e.get("msg", "")), "type": e.get("type")}
            for e in exc.errors()
        ]
        return JSONResponse({"detail": errors}, status_code=422)

    @app.middleware("http")
    async def limits_and_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        length = request.headers.get("content-length")
        if length is not None and (not length.isdigit() or int(length) > MAX_BODY_BYTES):
            response: Response = JSONResponse(
                {"detail": f"request body exceeds {MAX_BODY_BYTES} bytes"}, status_code=413
            )
        else:
            response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            # Swagger UI (/docs) loads its own CDN script; every other page is strict.
            if name == "Content-Security-Policy" and request.url.path.startswith(DOCS_PATHS):
                continue
            response.headers[name] = value
        return response

    def bundle() -> LoadedBundle:
        loaded = state["bundle"]
        if not isinstance(loaded, LoadedBundle):
            raise HTTPException(status_code=503, detail=str(state["error"] or "model not loaded"))
        return loaded

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", responses={503: {"model": Problem}})
    def readyz() -> dict[str, object]:
        loaded = bundle()
        return {"status": "ready", **loaded.version_info()}

    @app.post(
        "/v1/extract",
        response_model=ExtractResponse,
        responses={422: {"model": Problem}, 413: {"model": Problem}, 503: {"model": Problem}},
    )
    def extract(request: ExtractRequest) -> ExtractResponse:
        loaded = bundle()
        text = request.text
        try:
            encoded = text.encode("utf-8")
        except UnicodeEncodeError:
            raise HTTPException(status_code=422, detail="text is not valid Unicode") from None
        if "\x00" in text:
            raise HTTPException(status_code=422, detail="text contains NUL characters")
        if text.count("\n") + 1 > MAX_LINES:
            raise HTTPException(status_code=422, detail=f"text exceeds {MAX_LINES} lines")

        extractor = loaded.extractor
        raw_entities = extractor.predict_entities(text)
        raw_relations = extractor.predict_relations(text, raw_entities)
        entities = [Entity(**e, text=text[e["start"] : e["end"]]) for e in raw_entities]
        relations = [
            Relation(id=f"R{i}", head=r["head"], label=r["label"], tail=r["tail"])
            for i, r in enumerate(raw_relations, start=1)
        ]
        rows, review = build_sheet(raw_entities, raw_relations)
        normalized: dict[str, NormalizedValue] = {}
        for e in entities:
            if e.label in QUANTITY_LABELS:
                value, _ = normalize_value(e.text, e.label)
                if value is not None:
                    normalized[e.id] = NormalizedValue(**value)
        warnings = []
        if not any(e.label == "Action" for e in entities):
            warnings.append("No actions were recognized; the preparation sheet is empty.")
        if "\r" in text:
            warnings.append("Carriage returns were kept; offsets count them as characters.")
        info = loaded.version_info()
        return ExtractResponse(
            model=ModelInfo(**{k: info[k] for k in ModelInfo.model_fields}),
            text_sha256=hashlib.sha256(encoded).hexdigest(),
            entities=entities,
            relations=relations,
            sheet=[SheetRow(**row) for row in rows],
            normalized_values=normalized,
            normalization_version=VALUES_VERSION,
            review_items=[ReviewItem(**item) for item in review],
            warnings=warnings,
        )

    def review_store() -> ReviewStore:
        if "reviews" not in stores:
            raise HTTPException(status_code=503, detail="review storage is not configured")
        return stores["reviews"]

    def text_hash(text: str) -> str:
        try:
            return hashlib.sha256(text.encode("utf-8")).hexdigest()
        except UnicodeEncodeError:
            raise HTTPException(status_code=422, detail="text is not valid Unicode") from None

    def check_content(content: ReviewContent, text: str) -> None:
        problems = validate_content(content, text)
        if problems:
            raise HTTPException(status_code=422, detail="; ".join(problems[:20]))

    def call(fn: Callable[[], T]) -> T:
        try:
            return fn()
        except ReviewError as exc:
            raise HTTPException(status_code=exc.status, detail=exc.detail) from None

    review_errors: dict[int | str, dict[str, Any]] = {
        404: {"model": Problem},
        409: {"model": Problem},
        422: {"model": Problem},
        503: {"model": Problem},
    }

    @app.post("/v1/reviews", status_code=201, response_model=ReviewCreated, responses=review_errors)
    def create_review(
        request: ReviewCreate,
        idempotency_key: Annotated[str | None, Header(max_length=200)] = None,
    ) -> ReviewCreated:
        store = review_store()
        digest = text_hash(request.text)
        check_content(request.content, request.text)
        created = call(
            lambda: store.create(
                request.content.model_dump(),
                digest,
                request.text if request.save_text else None,
                request.model_version,
                idempotency_key,
            )
        )
        return ReviewCreated(id=created.review_id, token=created.token, revision=created.revision)

    @app.post("/v1/reviews/{review_id}/revisions", status_code=201, responses=review_errors)
    def revise_review(
        review_id: str,
        request: ReviewRevision,
        x_review_token: Annotated[str | None, Header()] = None,
    ) -> dict[str, int]:
        store = review_store()
        record = call(lambda: store.get(review_id, x_review_token))
        if text_hash(request.text) != record["text_sha256"]:
            raise HTTPException(status_code=409, detail="text does not match this review")
        check_content(request.content, request.text)
        number = call(
            lambda: store.add_revision(review_id, x_review_token, request.content.model_dump())
        )
        return {"revision": number}

    @app.post("/v1/preview", response_model=PreviewResponse, responses={422: {"model": Problem}})
    def preview(request: PreviewRequest) -> PreviewResponse:
        """Recompute the sheet for an edited graph; stateless and never stored."""
        text_hash(request.text)
        check_content(request.content, request.text)
        kept = [e for e in request.content.entities if e.decision != "rejected"]
        relations = [r.model_dump() for r in request.content.relations if r.decision != "rejected"]
        rows, review = build_sheet([e.model_dump() for e in kept], relations)
        normalized = {}
        for e in kept:
            if e.label in QUANTITY_LABELS:
                value, _ = normalize_value(request.text[e.start : e.end], e.label)
                if value is not None:
                    normalized[e.id] = NormalizedValue(**value)
        return PreviewResponse(
            sheet=[SheetRow(**row) for row in rows],
            review_items=[ReviewItem(**item) for item in review],
            normalized_values=normalized,
        )

    @app.get("/v1/reviews/{review_id}", response_model=ReviewRecord, responses=review_errors)
    def get_review(
        review_id: str, x_review_token: Annotated[str | None, Header()] = None
    ) -> ReviewRecord:
        record = call(lambda: review_store().get(review_id, x_review_token))
        return ReviewRecord(**record)

    @app.post("/v1/reviews/{review_id}/export", responses=review_errors)
    def export_review(
        review_id: str,
        request: ExportRequest,
        x_review_token: Annotated[str | None, Header()] = None,
    ) -> Response:
        record = call(lambda: review_store().get(review_id, x_review_token))
        text = record["text"] if record["text"] is not None else request.text
        if text is None:
            raise HTTPException(
                status_code=409, detail="this review did not store its text; include it to export"
            )
        if text_hash(text) != record["text_sha256"]:
            raise HTTPException(status_code=409, detail="text does not match this review")
        content = ReviewContent(**record["content"])
        stem = f"protocolledger-review-{review_id}-r{record['revision']}"
        if request.format == "csv":
            return Response(
                export_csv(record, content, text),
                media_type="text/csv; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{stem}.csv"'},
            )
        return JSONResponse(
            export_json(record, content, text),
            headers={"Content-Disposition": f'attachment; filename="{stem}.json"'},
        )

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html", media_type="text/html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


def create_app_from_env() -> FastAPI:
    configured = os.environ.get("PROTOCOLLEDGER_BUNDLE")
    database = os.environ.get("PROTOCOLLEDGER_DB")
    return create_app(
        Path(configured) if configured else None, Path(database) if database else None
    )
