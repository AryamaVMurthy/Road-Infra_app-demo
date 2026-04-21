from vlm_gateway.app.prompts import DSPyLevel1PromptSource, build_primary_classification_request


def test_build_primary_classification_request_uses_exact_dspy_instructions_and_output_shape():
    prompt_source = DSPyLevel1PromptSource(
        instructions="EXACT DSPY GEPA INSTRUCTIONS",
        output_field_names=("decision", "best_matching_category_hint", "rationale"),
    )

    request = build_primary_classification_request(
        image_data_url="data:image/jpeg;base64,ZmFrZQ==",
        reporter_notes="ignore me",
        active_categories={
            "pothole": "Road-surface collapse or cavity in drivable area",
            "damaged_road": "Cracked or eroded road surface without one discrete hole",
        },
        prompt_source=prompt_source,
    )

    system_prompt = request["messages"][0]["content"]
    assert system_prompt.startswith("EXACT DSPY GEPA INSTRUCTIONS")
    assert "Append this exact final answer format" in system_prompt
    assert "decision: <IN_SCOPE or REJECT>" in system_prompt
    assert "best_matching_category_hint: <category name or None>" in system_prompt
    assert "rationale: <short rationale>" in system_prompt
    assert "Reporter notes" not in request["messages"][1]["content"][0]["text"]
    assert "Category Catalog:" in request["messages"][1]["content"][0]["text"]
    assert "pothole: Road-surface collapse or cavity in drivable area" in request["messages"][1]["content"][0]["text"]
    assert request["response_format"]["type"] == "json_object"
    assert request["response_format"]["schema"]["required"] == [
        "decision",
        "best_matching_category_hint",
        "rationale",
    ]
