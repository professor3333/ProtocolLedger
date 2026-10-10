"""Versioned request and response schemas for the extraction API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1"
MAX_TEXT_CHARS = 20_000
MAX_LINES = 400


class ExtractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)


class Entity(BaseModel):
    id: str
    label: str
    start: int = Field(description="Start offset in Unicode code points, inclusive.")
    end: int = Field(description="End offset in Unicode code points, exclusive.")
    text: str


class Relation(BaseModel):
    id: str
    head: str
    label: str
    tail: str


class Quantity(BaseModel):
    entity: str
    of: str = Field(description="The material or action this value measures.")


class SheetRow(BaseModel):
    action: str
    materials: list[str]
    quantities: list[Quantity]
    locations: list[str]
    conditions: list[str]
    status: Literal["proposed", "review_required"]
    issues: list[str]


class ReviewItem(BaseModel):
    entity: str
    issue: str


class ModelInfo(BaseModel):
    model_version: str
    system: str
    bundle_sha256: str
    preprocessing_version: str


class NormalizedValue(BaseModel):
    kind: Literal["number", "range", "ratio", "symbolic"]
    value: float | str | None = None
    low: float | None = None
    high: float | None = None
    numerator: float | None = None
    denominator: float | None = None
    unit: str | None = None
    qualifier: str | None = None


class ExtractResponse(BaseModel):
    schema_version: str = SCHEMA_VERSION
    model: ModelInfo
    text_sha256: str
    offsets: Literal["unicode_code_points"] = "unicode_code_points"
    entities: list[Entity]
    relations: list[Relation]
    sheet: list[SheetRow]
    normalized_values: dict[str, NormalizedValue] = Field(
        description="Deterministic normalization of quantity entities, keyed by entity id. "
        "Quantities in unsupported formats are absent and shown as written."
    )
    normalization_version: str
    review_items: list[ReviewItem]
    warnings: list[str]


class Problem(BaseModel):
    detail: str


# ------------------------------------------------------------------- reviews

Origin = Literal["model", "human"]


class OriginalSpan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    start: int
    end: int


class ReviewEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=40)
    label: str
    start: int = Field(ge=0)
    end: int = Field(ge=1)
    origin: Origin
    decision: Literal["accepted", "rejected", "edited", "added"]
    original: OriginalSpan | None = None


class ReviewRelation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=40)
    head: str
    label: str
    tail: str
    origin: Origin
    decision: Literal["accepted", "rejected", "added"]


class ReviewContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entities: list[ReviewEntity] = Field(max_length=5000)
    relations: list[ReviewRelation] = Field(max_length=10000)


class ReviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    save_text: bool = False
    model_version: str = Field(min_length=1, max_length=100)
    content: ReviewContent


class ReviewRevision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    content: ReviewContent


class ReviewCreated(BaseModel):
    id: str
    token: str | None = Field(description="Shown once; required to read or revise. Null on retry.")
    revision: int


class ReviewHistoryItem(BaseModel):
    revision: int
    created_at: str
    sha256: str


class ReviewRecord(BaseModel):
    id: str
    created_at: str
    updated_at: str
    revision: int
    text_sha256: str
    text: str | None
    model_version: str
    content: ReviewContent
    history: list[ReviewHistoryItem]


class ExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["json", "csv"] = "json"
    text: str | None = Field(default=None, max_length=MAX_TEXT_CHARS)
