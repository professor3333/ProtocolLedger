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

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from protocolledger.serve.bundle import BundleError, LoadedBundle, load_bundle
from protocolledger.serve.schemas import (
    MAX_LINES,
    Entity,
    ExtractRequest,
    ExtractResponse,
    ModelInfo,
    Problem,
    Relation,
    ReviewItem,
    SheetRow,
)
from protocolledger.serve.sheet import build_sheet

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


def create_app(bundle_dir: Path | None) -> FastAPI:
    state: dict[str, LoadedBundle | str | None] = {"bundle": None, "error": None}

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
            review_items=[ReviewItem(**item) for item in review],
            warnings=warnings,
        )

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html", media_type="text/html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


def create_app_from_env() -> FastAPI:
    configured = os.environ.get("PROTOCOLLEDGER_BUNDLE")
    return create_app(Path(configured) if configured else None)
