"""Contract parsing for llama-server chat completions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


VALID_DECISIONS = {
    "ACCEPTED_CATEGORY_MATCH",
    "REJECTED",
}

LEGACY_REJECTION_DECISIONS = {
    "REJECTED_SPOOF_SYNTHETIC",
    "REJECTED_SPAM_IRRELEVANT",
    "REJECTED_NO_CATEGORY_MATCH",
}


class ContractViolationError(ValueError):
    """Raised when llama output breaks the expected inference contract."""


@dataclass(slots=True)
class ParsedClassification:
    decision: str
    category_name: str | None
    confidence: float | None
    prompt_version: str
    model_id: str


@dataclass(slots=True)
class ParsedEvaluatorResult:
    status: str
    failure_reason: str | None


def parse_llama_chat_response(
    *,
    payload: dict[str, Any],
    allowed_categories: set[str],
    prompt_version: str,
) -> ParsedClassification:
    model_id = str(payload.get("model") or "")
    content = _extract_message_content(payload)
    parsed = _load_model_output(content)

    raw_decision = parsed.get("decision")
    if raw_decision in LEGACY_REJECTION_DECISIONS:
        decision = "REJECTED"
    else:
        decision = raw_decision

    if decision not in VALID_DECISIONS:
        raise ContractViolationError(
            "Model output decision must be a supported contract enum"
        )

    category_name = parsed.get("category_name")
    if decision == "ACCEPTED_CATEGORY_MATCH":
        if category_name not in allowed_categories:
            raise ContractViolationError(
                "Model output category_name must be an allowed category"
            )
    elif decision == "REJECTED" and category_name is not None:
        raise ContractViolationError(
            "Rejected model decisions must not include a category_name"
        )

    confidence = parsed.get("confidence")
    if confidence is None:
        confidence_value = None
    else:
        if not isinstance(confidence, (int, float, str)):
            raise ContractViolationError("Model output confidence must be a numeric value")

        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError) as exc:
            raise ContractViolationError(
                "Model output confidence must be a numeric value"
            ) from exc

        if confidence_value < 0.0 or confidence_value > 1.0:
            raise ContractViolationError(
                "Model output confidence must be between 0.0 and 1.0"
            )

    if decision == "ACCEPTED_CATEGORY_MATCH" and confidence_value is None:
        raise ContractViolationError(
            "Accepted model outputs must include a numeric confidence"
        )

    return ParsedClassification(
        decision=decision,
        category_name=category_name,
        confidence=confidence_value,
        prompt_version=prompt_version,
        model_id=model_id,
    )


def _extract_message_content(payload: dict[str, Any]) -> str:
    try:
        return str(payload["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        raise ContractViolationError(
            "llama-server payload must include choices[0].message.content"
        ) from exc


def _load_json_object(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ContractViolationError(
            "Model output must be a valid JSON object"
        ) from exc

    if not isinstance(parsed, dict):
        raise ContractViolationError("Model output must be a valid JSON object")
    return parsed


def _load_model_output(content: str) -> dict[str, Any]:
    stripped = content.strip()
    if stripped == "REJECTED":
        return {"decision": "REJECTED", "category_name": None, "confidence": None}
    return _load_json_object(stripped)


def parse_evaluator_response(*, payload: dict[str, Any]) -> ParsedEvaluatorResult:
    content = _extract_message_content(payload)
    parsed = _load_json_object(content)

    status = parsed.get("status")
    if status not in {"pass", "fail"}:
        raise ContractViolationError("Evaluator status must be 'pass' or 'fail'")

    failure_reason = parsed.get("failure_reason")
    if failure_reason is not None and not isinstance(failure_reason, str):
        raise ContractViolationError(
            "Evaluator failure_reason must be a string or null"
        )

    return ParsedEvaluatorResult(status=status, failure_reason=failure_reason)
