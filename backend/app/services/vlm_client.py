"""Client for the separate VLM gateway service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


class VLMGatewayError(RuntimeError):
    """Base class for gateway client failures."""


class VLMGatewayUnavailableError(VLMGatewayError):
    """Raised when the gateway cannot be reached or times out."""


class VLMGatewayContractError(VLMGatewayError):
    """Raised when the gateway returns an invalid payload."""


@dataclass(slots=True)
class VLMClassificationResult:
    decision: str
    category_name: str | None
    confidence: float | None
    model_id: str
    model_quantization: str
    prompt_version: str
    raw_primary_result: dict[str, Any]
    raw_evaluator_result: dict[str, Any]
    latency_ms: int


class VLMGatewayClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: int,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout_seconds,
            transport=transport,
        )

    def classify_intake(
        self,
        *,
        submission_id: str,
        image_base64: str,
        mime_type: str,
        reporter_notes: str | None,
        active_categories: dict[str, str],
        prompt_version: str,
    ) -> VLMClassificationResult:
        payload = {
            "submission_id": submission_id,
            "image_base64": image_base64,
            "mime_type": mime_type,
            "reporter_notes": reporter_notes,
            "active_categories": active_categories,
            "prompt_version": prompt_version,
        }

        try:
            response = self._client.post("/internal/v1/intake/classify", json=payload)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise VLMGatewayUnavailableError(
                "Timed out waiting for VLM gateway classification"
            ) from exc
        except httpx.HTTPError as exc:
            raise VLMGatewayUnavailableError(
                "Failed to reach VLM gateway classification endpoint"
            ) from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise VLMGatewayContractError(
                "VLM gateway returned a non-JSON response"
            ) from exc

        try:
            return VLMClassificationResult(
                decision=str(body["decision"]),
                category_name=body["category_name"],
                confidence=float(body["confidence"]) if body["confidence"] is not None else None,
                model_id=str(body["model_id"]),
                model_quantization=str(body["model_quantization"]),
                prompt_version=str(body["prompt_version"]),
                raw_primary_result=dict(body["raw_primary_result"]),
                raw_evaluator_result=dict(body["raw_evaluator_result"]),
                latency_ms=int(body["latency_ms"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise VLMGatewayContractError(
                "VLM gateway returned an invalid classification payload"
            ) from exc
