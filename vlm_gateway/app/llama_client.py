"""llama-server backed classifier used by the VLM gateway worker."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

import httpx

from vlm_gateway.app.parser import ContractViolationError, parse_llama_chat_response
from vlm_gateway.app.prompts import (
    DSPyLevel1PromptSource,
    build_primary_classification_request,
    load_dspy_level1_prompt_source,
)


Classifier = Callable[[dict[str, Any]], dict[str, Any]]
DEFAULT_DSPY_LEVEL1_PROGRAM_PATH = (
    Path(__file__).resolve().parents[2] / "artifacts" / "models" / "intake_dspy" / "level1" / "gepa" / "program"
)


def create_llama_classifier(
    endpoint: str,
    *,
    model_id: str = "LiquidAI/LFM2.5-VL-1.6B-GGUF",
    model_quantization: str = "Q8_0",
    timeout_seconds: int = 180,
    prompt_program_path: Path | str = DEFAULT_DSPY_LEVEL1_PROGRAM_PATH,
) -> Classifier:
    client = httpx.Client(timeout=timeout_seconds)
    prompt_source = load_dspy_level1_prompt_source(prompt_program_path)

    def classify(job: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        image_data_url = f"data:{job['mime_type']};base64,{job['image_base64']}"
        primary_request = build_primary_classification_request(
            image_data_url=image_data_url,
            reporter_notes=job.get("reporter_notes"),
            active_categories=job["active_categories"],
            prompt_source=prompt_source,
        )
        primary_request["model"] = model_id
        primary_request["max_tokens"] = 160

        primary_response = _post_json(client, endpoint, primary_request)
        primary_result = parse_llama_chat_response(
            payload=primary_response,
            allowed_categories=set(job["active_categories"]),
            prompt_version=job["prompt_version"],
        )

        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            "decision": primary_result.decision,
            "category_name": None,
            "confidence": primary_result.confidence,
            "model_id": _normalize_model_id(
                primary_result.model_id,
                configured_model_id=model_id,
                model_quantization=model_quantization,
            ),
            "model_quantization": model_quantization,
            "prompt_version": primary_result.prompt_version,
            "raw_primary_result": _build_raw_primary_result(
                prompt_source=prompt_source,
                response_payload=primary_response,
                primary_result=primary_result,
            ),
            "raw_evaluator_result": {
                "status": "not_run",
                "reason": "level1_only_classifier",
            },
            "latency_ms": latency_ms,
        }

    return classify


def _build_raw_primary_result(
    *,
    prompt_source: DSPyLevel1PromptSource,
    response_payload: dict[str, Any],
    primary_result,
) -> dict[str, Any]:
    return {
        "prompt_backend": "llama_dspy_level1",
        "output_field_names": list(prompt_source.output_field_names),
        "decision": primary_result.decision,
        "best_matching_category_hint": primary_result.best_matching_category_hint,
        "rationale": primary_result.rationale,
        "response_payload": response_payload,
    }


def _post_json(
    client: httpx.Client,
    endpoint: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = client.post(endpoint, json=payload)
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict):
        raise ContractViolationError("llama-server response body must be a JSON object")
    return body


def _normalize_model_id(
    raw_model_id: str,
    *,
    configured_model_id: str,
    model_quantization: str,
) -> str:
    if not raw_model_id:
        return configured_model_id

    suffix = f":{model_quantization}"
    if raw_model_id.endswith(suffix):
        return raw_model_id[: -len(suffix)]
    return raw_model_id
