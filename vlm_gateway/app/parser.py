"""Contract parsing for llama-server chat completions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


VALID_DECISIONS = {"IN_SCOPE", "REJECTED"}
DSPY_DECISIONS = {"IN_SCOPE", "REJECT"}

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
    best_matching_category_hint: str | None
    rationale: str | None
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
    if raw_decision in LEGACY_REJECTION_DECISIONS or raw_decision == "REJECT":
        decision = "REJECTED"
    else:
        decision = raw_decision

    if decision not in VALID_DECISIONS:
        raise ContractViolationError(
            "Model output decision must be a supported contract enum"
        )

    category_name = parsed.get("category_name")
    if category_name is not None:
        raise ContractViolationError(
            "Spam-gating model decisions must not include a category_name"
        )

    best_matching_category_hint = _normalize_optional_string(
        parsed.get("best_matching_category_hint"),
        field_name="best_matching_category_hint",
        null_sentinels={"none", "null", "n/a", "na"},
    )
    rationale = _normalize_optional_string(
        parsed.get("rationale"),
        field_name="rationale",
    )

    uses_dspy_shape = (
        raw_decision == "REJECT"
        or "best_matching_category_hint" in parsed
        or "rationale" in parsed
    )

    if uses_dspy_shape:
        if rationale is None:
            raise ContractViolationError("DSPy model output rationale must be a string")

        if decision == "IN_SCOPE":
            if not best_matching_category_hint:
                raise ContractViolationError(
                    "DSPy IN_SCOPE output must include best_matching_category_hint"
                )
            normalized_allowed_categories = {
                str(category).strip().casefold() for category in allowed_categories
            }
            if best_matching_category_hint.casefold() not in normalized_allowed_categories:
                raise ContractViolationError(
                    "DSPy best_matching_category_hint must match one of the allowed categories"
                )
        else:
            if best_matching_category_hint:
                raise ContractViolationError(
                    "DSPy REJECT output must leave best_matching_category_hint empty"
                )
            best_matching_category_hint = None

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

    return ParsedClassification(
        decision=decision,
        category_name=None,
        confidence=confidence_value,
        best_matching_category_hint=best_matching_category_hint,
        rationale=rationale,
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
        return {
            "decision": "REJECTED",
            "category_name": None,
            "confidence": None,
        }
    if stripped == "IN_SCOPE":
        return {
            "decision": "IN_SCOPE",
            "category_name": None,
            "confidence": None,
        }
    try:
        return _load_json_object(stripped)
    except ContractViolationError:
        structured_text = _load_llama_structured_text_object(stripped)
        if structured_text is not None:
            return structured_text
        raise


def _normalize_optional_string(
    value: Any,
    *,
    field_name: str,
    null_sentinels: set[str] | None = None,
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ContractViolationError(f"Model output {field_name} must be a string or null")

    normalized = value.strip()
    if null_sentinels and normalized.casefold() in null_sentinels:
        return None
    return normalized or None


def _load_llama_structured_text_object(content: str) -> dict[str, Any] | None:
    fields: dict[str, str] = {}
    allowed_field_names = {"decision", "best_matching_category_hint", "rationale"}

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ":" not in line:
            return None

        name, value = line.split(":", 1)
        normalized_name = name.strip()
        if normalized_name not in allowed_field_names:
            return None
        fields[normalized_name] = value.strip()

    if set(fields) != allowed_field_names:
        return None

    return fields


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
