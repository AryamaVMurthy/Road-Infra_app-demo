"""DSPy-backed classifier pipeline for the VLM gateway."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from tools.dspy_intake.programs import (
    _normalize_level1_prediction,
)
from tools.dspy_intake.training import (
    DEFAULT_CATEGORY_CATALOG,
    OPENAI_MODEL_ID,
    load_compiled_program,
)


Classifier = Callable[[dict[str, Any]], dict[str, Any]]


def create_dspy_classifier(
    *,
    level1_program,
    variant_name: str,
) -> Classifier:
    normalized_variant_name = variant_name.strip()
    if not normalized_variant_name:
        raise ValueError("DSPY variant_name must be a non-empty string.")

    def classify(job: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        category_catalog = _normalize_active_categories(job["active_categories"])
        image_input = f"data:{job['mime_type']};base64,{job['image_base64']}"

        level1_prediction = _normalize_level1_prediction(
            level1_program(
                image=image_input,
                category_catalog=category_catalog,
            ),
            tuple(category_catalog),
        )

        decision = "IN_SCOPE" if level1_prediction.decision == "IN_SCOPE" else "REJECTED"
        rationale = level1_prediction.rationale

        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            "decision": decision,
            "category_name": None,
            "confidence": None,
            "model_id": OPENAI_MODEL_ID,
            "model_quantization": f"dspy-{normalized_variant_name}",
            "prompt_version": job["prompt_version"],
            "raw_primary_result": {
                "level1": {
                    "decision": level1_prediction.decision,
                    "best_matching_category_hint": level1_prediction.best_matching_category_hint,
                    "rationale": level1_prediction.rationale,
                },
            },
            "raw_evaluator_result": {
                "classifier_backend": "dspy",
                "variant_name": normalized_variant_name,
            },
            "latency_ms": latency_ms,
        }

    return classify


def load_dspy_classifier(
    *,
    level1_program_path: Path,
    variant_name: str,
) -> Classifier:
    resolved_level1_program_path = Path(level1_program_path)
    if not resolved_level1_program_path.exists():
        raise ValueError(
            f"DSPy Level 1 program path `{resolved_level1_program_path}` does not exist."
        )

    return create_dspy_classifier(
        level1_program=load_compiled_program(resolved_level1_program_path),
        variant_name=variant_name,
    )


def _normalize_active_categories(active_categories: dict[str, str]) -> dict[str, str]:
    normalized_active_categories = {
        str(name).strip(): str(guidance)
        for name, guidance in active_categories.items()
        if str(name).strip()
    }
    if set(normalized_active_categories) != set(DEFAULT_CATEGORY_CATALOG):
        raise ValueError(
            "Gateway active_categories must exactly match the DSPy category catalog "
            f"{tuple(DEFAULT_CATEGORY_CATALOG)}; got {tuple(sorted(normalized_active_categories))}."
        )
    return {
        label: normalized_active_categories[label]
        for label in DEFAULT_CATEGORY_CATALOG
    }
