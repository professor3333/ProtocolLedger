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
