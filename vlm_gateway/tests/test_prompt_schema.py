from vlm_gateway.app.prompts import (
    DSPyLevel1PromptSource,
    build_primary_classification_request,
)


def _prompt_source() -> DSPyLevel1PromptSource:
    return DSPyLevel1PromptSource(
        instructions="EXACT DSPY LEVEL1 INSTRUCTIONS",
        output_field_names=("decision", "best_matching_category_hint", "rationale"),
    )


def test_build_primary_classification_request_uses_openai_multimodal_shape():
    request = build_primary_classification_request(
        image_data_url="data:image/jpeg;base64,ZmFrZQ==",
        reporter_notes="Large cavity near the divider",
        active_categories={
            "pothole": "Road-surface collapse or cavity in drivable area",
            "damaged_road": "Cracked, eroded, or broken road surface without a discrete cavity",
        },
        prompt_source=_prompt_source(),
    )

    assert request["response_format"]["type"] == "json_object"
    assert request["messages"][0]["role"] == "system"
    assert request["messages"][0]["content"].startswith("EXACT DSPY LEVEL1 INSTRUCTIONS")
    assert "Append this exact final answer format" in request["messages"][0]["content"]
    assert request["messages"][1]["role"] == "user"
    assert request["messages"][1]["content"][0]["type"] == "text"
    assert request["messages"][1]["content"][1]["type"] == "image_url"
    assert request["temperature"] == 0
    assert request["seed"] == 7
    assert request["reasoning_format"] == "none"
    assert request["chat_template_kwargs"] == {"enable_thinking": False}
    assert (
        request["messages"][1]["content"][1]["image_url"]["url"]
        == "data:image/jpeg;base64,ZmFrZQ=="
    )


def test_build_primary_classification_request_only_appends_output_suffix_to_dspy_prompt():
    request = build_primary_classification_request(
        image_data_url="data:image/jpeg;base64,ZmFrZQ==",
        reporter_notes=None,
        active_categories={"pothole": "Road-surface collapse or cavity in drivable area"},
        prompt_source=_prompt_source(),
    )

    system_prompt = request["messages"][0]["content"]

    assert system_prompt.startswith("EXACT DSPY LEVEL1 INSTRUCTIONS")
    assert system_prompt.count("EXACT DSPY LEVEL1 INSTRUCTIONS") == 1
    assert system_prompt.endswith("rationale: <short rationale>")


def test_build_primary_classification_request_embeds_category_catalog_only():
    request = build_primary_classification_request(
        image_data_url="data:image/jpeg;base64,ZmFrZQ==",
        reporter_notes="cat photo pretending to be a pothole",
        active_categories={
            "pothole": "Road-surface collapse or cavity in drivable area",
            "garbage_litter": "Visible dumped waste or litter accumulation in public roadside space",
        },
        prompt_source=_prompt_source(),
    )

    user_prompt = request["messages"][1]["content"][0]["text"]

    assert "Category Catalog:" in user_prompt
    assert "pothole: Road-surface collapse or cavity in drivable area" in user_prompt
    assert (
        "garbage_litter: Visible dumped waste or litter accumulation in public roadside space"
        in user_prompt
    )
    assert "cat photo pretending to be a pothole" not in user_prompt


def test_build_primary_classification_request_uses_dspy_output_schema():
    request = build_primary_classification_request(
        image_data_url="data:image/jpeg;base64,ZmFrZQ==",
        reporter_notes=None,
        active_categories={"pothole": "Road-surface collapse or cavity in drivable area"},
        prompt_source=_prompt_source(),
    )

    schema = request["response_format"]["schema"]

    assert schema["required"] == [
        "decision",
        "best_matching_category_hint",
        "rationale",
    ]
    assert schema["properties"]["decision"] == {"type": "string"}
    assert schema["properties"]["best_matching_category_hint"] == {"type": "string"}
    assert schema["properties"]["rationale"] == {"type": "string"}
    assert schema["additionalProperties"] is False
