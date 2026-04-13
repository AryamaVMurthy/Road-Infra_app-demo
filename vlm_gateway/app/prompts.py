"""Prompt builders for llama-server intake classification."""

from __future__ import annotations

from typing import Any


def build_description_request(
    *,
    image_data_url: str,
    reporter_notes: str | None,
    prompt_version: str,
) -> dict[str, Any]:
    notes = reporter_notes.strip() if reporter_notes else "None provided"

    system_prompt = (
        f"You are the MARG intake image describer. Prompt version: {prompt_version}.\n"
        "Look at the image carefully and describe only what is visibly present.\n"
        "Prefer concrete visual details over guesses.\n"
        "Mention visible road defects, drains, standing water, garbage, street lights, "
        "or signs that the image is synthetic, irrelevant, or non-civic when applicable.\n"
        "Return plain text only in one or two short sentences."
    )

    user_prompt = (
        "Describe this citizen-submitted image for a downstream classifier.\n"
        f"Reporter notes: {notes}"
    )

    return {
        "temperature": 0,
        "seed": 7,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            },
        ],
    }


def build_primary_classification_request(
    *,
    image_data_url: str,
    image_description: str,
    reporter_notes: str | None,
    active_categories: dict[str, str],
    prompt_version: str,
) -> dict[str, Any]:
    category_lines = "\n".join(
        f"- {name}: {guidance}" for name, guidance in sorted(active_categories.items())
    )
    notes = reporter_notes.strip() if reporter_notes else "None provided"

    system_prompt = (
        f"You are the MARG intake classifier. Prompt version: {prompt_version}.\n"
        "Return JSON only.\n"
        "Decide whether the image is a valid civic road-infrastructure issue image.\n"
        "Strongly prefer classifying into one of the active categories when the image "
        "plausibly fits any active category.\n"
        "Use REJECTED only when the image clearly does not fit any active category at all.\n"
        "Use exactly one of these decisions: ACCEPTED_CATEGORY_MATCH, REJECTED.\n"
        "If decision is ACCEPTED_CATEGORY_MATCH, category_name must be one of the active categories.\n"
        "If decision is REJECTED, category_name must be null.\n"
        "Active categories:\n"
        f"{category_lines}"
    )

    user_prompt = (
        "Classify this citizen-submitted image.\n"
        f"Reporter notes: {notes}\n"
        f"Visual description: {image_description}\n"
        "If the image plausibly matches an active category, choose that category.\n"
        "Only reject when no active category fits at all.\n"
        "Return a JSON object with decision, category_name, confidence."
    )

    return {
        "temperature": 0,
        "seed": 7,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            },
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "marg_intake_primary_result",
                "schema": {
                    "type": "object",
                    "required": [
                        "decision",
                        "category_name",
                        "confidence",
                    ],
                    "properties": {
                        "decision": {"type": "string"},
                        "category_name": {"type": ["string", "null"]},
                        "confidence": {"type": "number"},
                    },
                    "additionalProperties": False,
                },
            },
        },
    }


def build_evaluator_request(
    *,
    image_data_url: str,
    image_description: str,
    active_categories: dict[str, str],
    prompt_version: str,
    primary_result: dict[str, Any],
) -> dict[str, Any]:
    category_lines = "\n".join(
        f"- {name}: {guidance}" for name, guidance in sorted(active_categories.items())
    )

    system_prompt = (
        f"You are the MARG intake evaluator. Prompt version: {prompt_version}.\n"
        "Return JSON only.\n"
        "Review the image, the active categories, and the primary classifier result.\n"
        "Fail only if the primary result breaks the contract or is not justified by the image.\n"
        "Valid primary outcomes include accepted category matches and valid rejections.\n"
        "Rubric:\n"
        "- If decision is ACCEPTED_CATEGORY_MATCH, PASS only if the image clearly fits "
        "the chosen active category.\n"
        "- If decision is REJECTED and category_name is null, "
        "you MUST return PASS when the image is real but does not plausibly fit any "
        "of the active categories.\n"
        "- A real image of an animal, person, indoor object, or unrelated outdoor scene "
        "that does not match any active category is a valid rejection and should PASS.\n"
        "- Do not mark a valid non-category real image as FAIL merely because it is not "
        "a civic issue. That is exactly when REJECTED should PASS.\n"
        "- Do not fail a result merely because it is a rejection. Rejections are valid outcomes.\n"
        "If the primary result is coherent and justified by the image, return "
        '{"status":"pass","failure_reason":null}.\n'
        "If it is not coherent or not justified, return "
        '{"status":"fail","failure_reason":"<short explanation>"}.\n'
        "Active categories:\n"
        f"{category_lines}"
    )

    user_prompt = (
        "Evaluate this primary intake classification result.\n"
        f"Visual description: {image_description}\n"
        f"Primary result: {primary_result}\n"
        "Return a JSON object with status and failure_reason only."
    )

    return {
        "temperature": 0,
        "seed": 7,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            },
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "marg_intake_evaluator_result",
                "schema": {
                    "type": "object",
                    "required": ["status", "failure_reason"],
                    "properties": {
                        "status": {"type": "string"},
                        "failure_reason": {"type": ["string", "null"]},
                    },
                    "additionalProperties": False,
                },
            },
        },
    }
