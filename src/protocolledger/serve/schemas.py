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


class ExtractResponse(BaseModel):
    schema_version: str = SCHEMA_VERSION
    model: ModelInfo
    text_sha256: str
    offsets: Literal["unicode_code_points"] = "unicode_code_points"
    entities: list[Entity]
    relations: list[Relation]
    sheet: list[SheetRow]
    review_items: list[ReviewItem]
    warnings: list[str]


class Problem(BaseModel):
    detail: str
