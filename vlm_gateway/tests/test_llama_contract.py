import pytest

from vlm_gateway.app.parser import ContractViolationError, parse_llama_chat_response


def test_parse_llama_chat_response_accepts_valid_category_match():
    payload = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"decision":"ACCEPTED_CATEGORY_MATCH",'
                        '"category_name":"Pothole",'
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

    assert result.decision == "ACCEPTED_CATEGORY_MATCH"
    assert result.category_name == "Pothole"
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


def test_parse_llama_chat_response_rejects_unknown_category_name():
    payload = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"decision":"ACCEPTED_CATEGORY_MATCH",'
                        '"category_name":"Street Sign",'
                        '"confidence":0.81}'
                    )
                }
            }
        ],
        "model": "LiquidAI/LFM2.5-VL-1.6B-GGUF:Q8_0",
    }

    with pytest.raises(ContractViolationError, match="allowed category"):
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
                        '{"decision":"ACCEPTED_CATEGORY_MATCH",'
                        '"category_name":"Pothole",'
                        '"confidence":null}'
                    )
                }
            }
        ],
        "model": "LiquidAI/LFM2.5-VL-1.6B-GGUF:Q8_0",
    }

    with pytest.raises(ContractViolationError, match="must include a numeric confidence"):
        parse_llama_chat_response(
            payload=payload,
            allowed_categories={"Pothole", "Drainage"},
            prompt_version="v1",
        )
