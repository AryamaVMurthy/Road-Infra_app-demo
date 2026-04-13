"""llama-server backed classifier used by the VLM gateway worker."""

from __future__ import annotations

import time
from typing import Any, Callable

import httpx

from vlm_gateway.app.parser import (
    ContractViolationError,
    parse_evaluator_response,
    parse_llama_chat_response,
)
from vlm_gateway.app.prompts import (
    build_description_request,
    build_evaluator_request,
    build_primary_classification_request,
)


Classifier = Callable[[dict[str, Any]], dict[str, Any]]


def create_llama_classifier(
    endpoint: str,
    *,
    model_id: str = "LiquidAI/LFM2.5-VL-1.6B-GGUF",
    model_quantization: str = "Q8_0",
    timeout_seconds: int = 20,
) -> Classifier:
    client = httpx.Client(timeout=timeout_seconds)

    def classify(job: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        image_data_url = f"data:{job['mime_type']};base64,{job['image_base64']}"
        description_request = build_description_request(
            image_data_url=image_data_url,
            reporter_notes=job.get("reporter_notes"),
            prompt_version=job["prompt_version"],
        )
        description_request["model"] = model_id
        description_request["max_tokens"] = 128
        description_response = _post_json(client, endpoint, description_request)
        image_description = _extract_text_content(description_response)

        primary_request = build_primary_classification_request(
            image_data_url=image_data_url,
            image_description=image_description,
            reporter_notes=job.get("reporter_notes"),
            active_categories=job["active_categories"],
            prompt_version=job["prompt_version"],
        )
        primary_request["model"] = model_id
        primary_request["max_tokens"] = 256

        primary_response = _post_json(client, endpoint, primary_request)
        primary_result = parse_llama_chat_response(
            payload=primary_response,
            allowed_categories=set(job["active_categories"]),
            prompt_version=job["prompt_version"],
        )

        if primary_result.decision == "ACCEPTED_CATEGORY_MATCH":
            evaluator_request = build_evaluator_request(
                image_data_url=image_data_url,
                image_description=image_description,
                active_categories=job["active_categories"],
                prompt_version=job["prompt_version"],
                primary_result={
                    "decision": primary_result.decision,
                    "category_name": primary_result.category_name,
                    "confidence": primary_result.confidence,
                },
            )
            evaluator_request["model"] = model_id
            evaluator_request["max_tokens"] = 128

            evaluator_response = _post_json(client, endpoint, evaluator_request)
            evaluator_result = parse_evaluator_response(payload=evaluator_response)
            if evaluator_result.status != "pass":
                raise ContractViolationError(
                    "Evaluator rejected the primary model result: "
                    f"{evaluator_result.failure_reason or 'unspecified'}"
                )
        else:
            evaluator_response = {
                "status": "skipped",
                "reason": "primary_rejection_does_not_require_category_confirmation",
            }

        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            "decision": primary_result.decision,
            "category_name": primary_result.category_name,
            "confidence": primary_result.confidence,
            "model_id": primary_result.model_id or model_id,
            "model_quantization": model_quantization,
            "prompt_version": primary_result.prompt_version,
            "raw_primary_result": {
                "description": image_description,
                "description_response": description_response,
                "classification_response": primary_response,
            },
            "raw_evaluator_result": evaluator_response,
            "latency_ms": latency_ms,
        }

    return classify


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


def _extract_text_content(payload: dict[str, Any]) -> str:
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ContractViolationError(
            "llama-server payload must include choices[0].message.content"
        ) from exc

    if not isinstance(content, str):
        raise ContractViolationError("Description response content must be plain text")

    cleaned = content.strip()
    if not cleaned:
        raise ContractViolationError("Description response content must not be empty")
    return cleaned
