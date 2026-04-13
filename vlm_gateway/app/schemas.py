"""Pydantic schemas for the VLM gateway HTTP contract."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class IntakeClassificationRequest(BaseModel):
    submission_id: str = Field(min_length=1)
    image_base64: str = Field(min_length=1)
    mime_type: str = Field(min_length=1)
    reporter_notes: str | None = None
    active_categories: dict[str, str]
    prompt_version: str = Field(min_length=1)


class IntakeClassificationResponse(BaseModel):
    decision: str
    category_name: str | None
    confidence: float | None
    model_id: str
    model_quantization: str
    prompt_version: str
    raw_primary_result: dict[str, Any]
    raw_evaluator_result: dict[str, Any]
    latency_ms: int
