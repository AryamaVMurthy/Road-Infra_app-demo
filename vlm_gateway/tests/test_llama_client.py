from __future__ import annotations

from pathlib import Path

from vlm_gateway.app import llama_client
from vlm_gateway.app.prompts import FINAL_ANSWER_SUFFIX


def test_create_llama_classifier_runs_level1_only_for_rejected_result(
    monkeypatch,
):
    calls: list[dict[str, object]] = []
    responses = [
        {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"decision":"REJECT",'
                            '"best_matching_category_hint":"",'
                            '"rationale":"No supported civic issue is visible."}'
                        )
                    }
                }
            ],
            "model": "LiquidAI/LFM2.5-VL-1.6B-GGUF:Q8_0",
        },
    ]

    def fake_post_json(client, endpoint, payload):
        calls.append(payload)
        return responses.pop(0)

    monkeypatch.setattr(llama_client, "_post_json", fake_post_json)
    monkeypatch.setattr(
        llama_client,
        "load_dspy_level1_prompt_source",
        lambda path: llama_client.DSPyLevel1PromptSource(
            instructions="EXACT DSPY INSTRUCTIONS",
            output_field_names=("decision", "best_matching_category_hint", "rationale"),
        ),
    )

    classifier = llama_client.create_llama_classifier(
        "http://llama.test/v1/chat/completions",
        prompt_program_path=Path("/tmp/dspy-program"),
    )
    result = classifier(
        {
            "submission_id": "sub-1",
            "image_base64": "ZmFrZQ==",
            "mime_type": "image/jpeg",
            "reporter_notes": "possible issue",
            "active_categories": {
                "Pothole": "Road-surface collapse or cavity in drivable area",
                "Drainage": "Blocked drain, standing water, or overflow",
            },
            "prompt_version": "v1",
        }
    )

    assert len(calls) == 1
    system_prompt = calls[0]["messages"][0]["content"]
    assert system_prompt.startswith("EXACT DSPY INSTRUCTIONS")
    assert system_prompt.endswith(FINAL_ANSWER_SUFFIX)
    assert result["decision"] == "REJECTED"
    assert result["category_name"] is None
    assert result["raw_evaluator_result"] == {
        "status": "not_run",
        "reason": "level1_only_classifier",
    }


def test_create_llama_classifier_runs_level1_only_for_in_scope_result(
    monkeypatch,
):
    calls: list[dict[str, object]] = []
    responses = [
        {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"decision":"IN_SCOPE","best_matching_category_hint":"pothole","rationale":"Visible road cavity."}'
                        )
                    }
                }
            ],
            "model": "LiquidAI/LFM2.5-VL-1.6B-GGUF:Q8_0",
        },
    ]

    def fake_post_json(client, endpoint, payload):
        calls.append(payload)
        return responses.pop(0)

    monkeypatch.setattr(llama_client, "_post_json", fake_post_json)
    monkeypatch.setattr(
        llama_client,
        "load_dspy_level1_prompt_source",
        lambda path: llama_client.DSPyLevel1PromptSource(
            instructions="EXACT DSPY INSTRUCTIONS",
            output_field_names=("decision", "best_matching_category_hint", "rationale"),
        ),
    )

    classifier = llama_client.create_llama_classifier(
        "http://llama.test/v1/chat/completions",
        prompt_program_path=Path("/tmp/dspy-program"),
    )
    result = classifier(
        {
            "submission_id": "sub-2",
            "image_base64": "ZmFrZQ==",
            "mime_type": "image/jpeg",
            "reporter_notes": "possible issue",
            "active_categories": {
                "Pothole": "Road-surface collapse or cavity in drivable area",
            },
            "prompt_version": "v1",
        }
    )

    assert len(calls) == 1
    system_prompt = calls[0]["messages"][0]["content"]
    assert system_prompt.startswith("EXACT DSPY INSTRUCTIONS")
    assert system_prompt.endswith(FINAL_ANSWER_SUFFIX)
    assert result["decision"] == "IN_SCOPE"
    assert result["confidence"] is None
    assert result["raw_evaluator_result"] == {
        "status": "not_run",
        "reason": "level1_only_classifier",
    }
