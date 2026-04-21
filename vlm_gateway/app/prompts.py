"""Prompt builders for the Level 1 llama-server intake classification path."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import dspy


FINAL_ANSWER_SUFFIX = (
    "\n\nAppend this exact final answer format after completing the DSPy task. "
    "Output only these three lines and nothing else:\n"
    "decision: <IN_SCOPE or REJECT>\n"
    "best_matching_category_hint: <category name or None>\n"
    "rationale: <short rationale>"
)


@dataclass(frozen=True, slots=True)
class DSPyLevel1PromptSource:
    instructions: str
    output_field_names: tuple[str, ...]


@lru_cache(maxsize=8)
def load_dspy_level1_prompt_source(program_path: Path | str) -> DSPyLevel1PromptSource:
    resolved_program_path = Path(program_path)
    if not resolved_program_path.exists():
        raise ValueError(
            f"DSPy Level 1 program path `{resolved_program_path}` does not exist."
        )

    program = dspy.load(str(resolved_program_path), allow_pickle=True)
    predictor = getattr(program, "predictor", None)
    if predictor is None:
        raise ValueError(
            f"DSPy Level 1 program `{resolved_program_path}` is missing predictor state."
        )

    signature = getattr(predictor, "signature", None)
    if signature is None:
        raise ValueError(
            f"DSPy Level 1 program `{resolved_program_path}` is missing predictor signature state."
        )

    instructions = getattr(signature, "instructions", None)
    if not isinstance(instructions, str) or not instructions.strip():
        raise ValueError(
            f"DSPy Level 1 program `{resolved_program_path}` is missing optimized instructions."
        )

    output_fields = tuple(
        field_name
        for field_name, field_info in signature.fields.items()
        if field_info.json_schema_extra.get("__dspy_field_type") == "output"
    )
    if output_fields != ("decision", "best_matching_category_hint", "rationale"):
        raise ValueError(
            "DSPy Level 1 prompt source must expose decision, best_matching_category_hint, "
            f"and rationale outputs; got {output_fields!r}."
        )

    return DSPyLevel1PromptSource(
        instructions=instructions,
        output_field_names=output_fields,
    )


def build_primary_classification_request(
    *,
    image_data_url: str,
    reporter_notes: str | None,
    active_categories: dict[str, str],
    prompt_source: DSPyLevel1PromptSource,
) -> dict[str, Any]:
    del reporter_notes

    category_catalog = "\n".join(
        f"{name}: {guidance}" for name, guidance in sorted(active_categories.items())
    )

    user_prompt = (
        "Use the provided category catalog and image to complete the DSPy Level 1 task.\n"
        f"Category Catalog:\n{category_catalog}"
    )
    json_schema = {
        "type": "object",
        "required": list(prompt_source.output_field_names),
        "properties": {
            "decision": {"type": "string"},
            "best_matching_category_hint": {"type": "string"},
            "rationale": {"type": "string"},
        },
        "additionalProperties": False,
    }

    return {
        "temperature": 0,
        "seed": 7,
        "reasoning_format": "none",
        "chat_template_kwargs": {"enable_thinking": False},
        "messages": [
            {
                "role": "system",
                "content": f"{prompt_source.instructions}{FINAL_ANSWER_SUFFIX}",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            },
        ],
        "response_format": {
            "type": "json_object",
            "schema": json_schema,
        },
    }
