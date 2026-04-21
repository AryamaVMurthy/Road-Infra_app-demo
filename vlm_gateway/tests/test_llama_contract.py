import pytest

from vlm_gateway.app.parser import ContractViolationError, parse_llama_chat_response


def test_parse_llama_chat_response_accepts_valid_in_scope_result():
    payload = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"decision":"IN_SCOPE",'
                        '"category_name":null,'
                        '"confidence":0.93}'
                    )
                }
            }
        ],
        "model": "LiquidAI/LFM2.5-VL-1.6B-GGUF:Q8_0",
    }

    result = parse_llama_chat_response(
        payload=payload,
        allowed_categories={"Pothole", "Drainage"},
        prompt_version="v1",
    )

    assert result.decision == "IN_SCOPE"
    assert result.category_name is None
    assert result.confidence == 0.93
    assert result.prompt_version == "v1"


def test_parse_llama_chat_response_rejects_non_json_model_output():
    payload = {
        "choices": [
            {
                "message": {
                    "content": "This looks like a pothole near a curb, confidence high."
                }
            }
        ],
        "model": "LiquidAI/LFM2.5-VL-1.6B-GGUF:Q8_0",
    }

    with pytest.raises(ContractViolationError, match="valid JSON object"):
        parse_llama_chat_response(
            payload=payload,
            allowed_categories={"Pothole", "Drainage"},
            prompt_version="v1",
        )


def test_parse_llama_chat_response_accepts_llama_structured_text_output():
    payload = {
        "choices": [
            {
                "message": {
                    "content": (
                        "decision: IN_SCOPE\n"
                        "best_matching_category_hint: Pothole\n"
                        "rationale: Visible road cavity in the drivable lane."
                    )
                }
            }
        ],
        "model": "LiquidAI/LFM2.5-VL-1.6B-GGUF:Q8_0",
    }

    result = parse_llama_chat_response(
        payload=payload,
        allowed_categories={"Pothole", "Drainage"},
        prompt_version="v1",
    )

    assert result.decision == "IN_SCOPE"
    assert result.best_matching_category_hint == "Pothole"
    assert result.rationale == "Visible road cavity in the drivable lane."


def test_parse_llama_chat_response_accepts_plain_rejected_output():
    payload = {
        "choices": [
            {
                "message": {
                    "content": "REJECTED"
                }
            }
        ],
        "model": "LiquidAI/LFM2.5-VL-1.6B-GGUF:Q8_0",
    }

    result = parse_llama_chat_response(
        payload=payload,
        allowed_categories={"Pothole", "Drainage"},
        prompt_version="v1",
    )

    assert result.decision == "REJECTED"
    assert result.category_name is None
    assert result.confidence is None


def test_parse_llama_chat_response_rejects_any_category_name_on_in_scope_output():
    payload = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"decision":"IN_SCOPE",'
                        '"category_name":"Street Sign",'
                        '"confidence":0.81}'
                    )
                }
            }
        ],
        "model": "LiquidAI/LFM2.5-VL-1.6B-GGUF:Q8_0",
    }

    with pytest.raises(ContractViolationError, match="must not include a category_name"):
        parse_llama_chat_response(
            payload=payload,
            allowed_categories={"Pothole", "Drainage"},
            prompt_version="v1",
        )


def test_parse_llama_chat_response_rejects_category_name_on_rejected_output():
    payload = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"decision":"REJECTED",'
                        '"category_name":"Garbage",'
                        '"confidence":0.88}'
                    )
                }
            }
        ],
        "model": "LiquidAI/LFM2.5-VL-1.6B-GGUF:Q8_0",
    }

    with pytest.raises(ContractViolationError, match="must not include a category_name"):
        parse_llama_chat_response(
            payload=payload,
            allowed_categories={"Pothole", "Drainage"},
            prompt_version="v1",
        )


def test_parse_llama_chat_response_normalizes_legacy_rejection_decision():
    payload = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"decision":"REJECTED_NO_CATEGORY_MATCH",'
                        '"category_name":null,'
                        '"confidence":0.88}'
                    )
                }
            }
        ],
        "model": "LiquidAI/LFM2.5-VL-1.6B-GGUF:Q8_0",
    }

    result = parse_llama_chat_response(
        payload=payload,
        allowed_categories={"Pothole", "Drainage"},
        prompt_version="v1",
    )

    assert result.decision == "REJECTED"
    assert result.category_name is None


def test_parse_llama_chat_response_rejects_missing_confidence():
    payload = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"decision":"IN_SCOPE",'
                        '"category_name":null,'
                        '"confidence":null}'
                    )
                }
            }
        ],
        "model": "LiquidAI/LFM2.5-VL-1.6B-GGUF:Q8_0",
    }

    result = parse_llama_chat_response(
        payload=payload,
        allowed_categories={"Pothole", "Drainage"},
        prompt_version="v1",
    )
    assert result.decision == "IN_SCOPE"
    assert result.confidence is None


def test_parse_llama_chat_response_accepts_dspy_in_scope_result():
    payload = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"decision":"IN_SCOPE",'
                        '"best_matching_category_hint":"pothole",'
                        '"rationale":"Visible road cavity."}'
                    )
                }
            }
        ],
        "model": "LiquidAI/LFM2.5-VL-1.6B-GGUF:Q8_0",
    }

    result = parse_llama_chat_response(
        payload=payload,
        allowed_categories={"pothole", "damaged_road"},
        prompt_version="v1",
    )

    assert result.decision == "IN_SCOPE"
    assert result.category_name is None
    assert result.confidence is None


def test_parse_llama_chat_response_accepts_dspy_reject_result():
    payload = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"decision":"REJECT",'
                        '"best_matching_category_hint":"",'
                        '"rationale":"No listed issue is visible."}'
                    )
                }
            }
        ],
        "model": "LiquidAI/LFM2.5-VL-1.6B-GGUF:Q8_0",
    }

    result = parse_llama_chat_response(
        payload=payload,
        allowed_categories={"pothole", "damaged_road"},
        prompt_version="v1",
    )

    assert result.decision == "REJECTED"
    assert result.category_name is None
    assert result.confidence is None


def test_parse_llama_chat_response_rejects_dspy_reject_with_nonempty_hint():
    payload = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"decision":"REJECT",'
                        '"best_matching_category_hint":"pothole",'
                        '"rationale":"No listed issue is visible."}'
                    )
                }
            }
        ],
        "model": "LiquidAI/LFM2.5-VL-1.6B-GGUF:Q8_0",
    }

    with pytest.raises(ContractViolationError, match="best_matching_category_hint"):
        parse_llama_chat_response(
            payload=payload,
            allowed_categories={"pothole", "damaged_road"},
            prompt_version="v1",
        )


def test_parse_llama_chat_response_accepts_reject_with_string_none_hint():
    payload = {
        "choices": [
            {
                "message": {
                    "content": (
                        "decision: REJECT\n"
                        "best_matching_category_hint: None\n"
                        "rationale: The image does not match any supported issue."
                    )
                }
            }
        ],
        "model": "LiquidAI/LFM2.5-VL-1.6B-GGUF:Q8_0",
    }

    result = parse_llama_chat_response(
        payload=payload,
        allowed_categories={"pothole", "damaged_road"},
        prompt_version="v1",
    )

    assert result.decision == "REJECTED"
    assert result.best_matching_category_hint is None
