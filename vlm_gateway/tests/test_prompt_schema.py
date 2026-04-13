from vlm_gateway.app.prompts import (
    build_description_request,
    build_primary_classification_request,
)


def test_build_description_request_uses_openai_multimodal_shape():
    request = build_description_request(
        image_data_url="data:image/jpeg;base64,ZmFrZQ==",
        reporter_notes="Large cavity near the divider",
        prompt_version="v1",
    )

    assert "response_format" not in request
    assert request["messages"][0]["role"] == "system"
    assert request["messages"][1]["role"] == "user"
    assert request["messages"][1]["content"][0]["type"] == "text"
    assert request["messages"][1]["content"][1]["type"] == "image_url"
    assert request["temperature"] == 0
    assert request["seed"] == 7


def test_build_primary_classification_request_uses_openai_multimodal_shape():
    request = build_primary_classification_request(
        image_data_url="data:image/jpeg;base64,ZmFrZQ==",
        image_description="A damaged road surface with a visible cavity in the lane.",
        reporter_notes="Large cavity near the divider",
        active_categories={
            "Pothole": "Road-surface collapse or cavity in drivable area",
            "Drainage": "Blocked drain, standing water, or overflow",
        },
        prompt_version="v1",
    )

    assert request["response_format"]["type"] == "json_schema"
    assert request["messages"][0]["role"] == "system"
    assert request["messages"][1]["role"] == "user"
    assert request["messages"][1]["content"][0]["type"] == "text"
    assert request["messages"][1]["content"][1]["type"] == "image_url"
    assert request["temperature"] == 0
    assert request["seed"] == 7
    assert (
        request["messages"][1]["content"][1]["image_url"]["url"]
        == "data:image/jpeg;base64,ZmFrZQ=="
    )


def test_build_primary_classification_request_embeds_categories_and_prompt_version():
    request = build_primary_classification_request(
        image_data_url="data:image/jpeg;base64,ZmFrZQ==",
        image_description="Standing water near a blocked roadside drain.",
        reporter_notes="water accumulation beside drain",
        active_categories={
            "Pothole": "Road-surface collapse or cavity in drivable area",
            "Drainage": "Blocked drain, standing water, or overflow",
        },
        prompt_version="v7",
    )

    system_prompt = request["messages"][0]["content"]
    user_prompt = request["messages"][1]["content"][0]["text"]

    assert "v7" in system_prompt
    assert "Pothole" in system_prompt
    assert "Drainage" in system_prompt
    assert "Road-surface collapse or cavity in drivable area" in system_prompt
    assert "Blocked drain, standing water, or overflow" in system_prompt
    assert "water accumulation beside drain" in user_prompt
    assert "Standing water near a blocked roadside drain." in user_prompt
    assert "Return JSON only" in system_prompt


def test_build_primary_classification_request_embeds_binary_decision_contract():
    request = build_primary_classification_request(
        image_data_url="data:image/jpeg;base64,ZmFrZQ==",
        image_description="A broken road surface.",
        reporter_notes="None",
        active_categories={
            "Pothole": "Road-surface collapse or cavity in drivable area",
        },
        prompt_version="v1",
    )

    system_prompt = request["messages"][0]["content"]

    assert "ACCEPTED_CATEGORY_MATCH, REJECTED" in system_prompt
    assert "If decision is ACCEPTED_CATEGORY_MATCH" in system_prompt
    assert "If decision is REJECTED" in system_prompt
    assert "Strongly prefer classifying into one of the active categories" in system_prompt
    assert "Only reject when no active category fits at all." in request["messages"][1]["content"][0]["text"]
