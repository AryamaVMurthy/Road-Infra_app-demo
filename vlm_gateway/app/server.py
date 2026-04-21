"""Env-driven FastAPI server for the separate VLM gateway service."""

from __future__ import annotations

import os
from pathlib import Path

from vlm_gateway.app.llama_client import (
    DEFAULT_DSPY_LEVEL1_PROGRAM_PATH,
    create_llama_classifier,
)
from vlm_gateway.app.main import create_app


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value is not None else default


def _load_dspy_classifier():
    from vlm_gateway.app.dspy_pipeline import load_dspy_classifier

    return load_dspy_classifier


def build_classifier_from_env():
    mode = os.getenv("VLM_CLASSIFIER_MODE", "llama").strip().lower()
    if mode == "llama":
        return create_llama_classifier(
            os.getenv("LLAMA_SERVER_URL", "http://llama-server:8081/v1/chat/completions"),
            model_id=os.getenv("VLM_MODEL_ID", "LiquidAI/LFM2.5-VL-1.6B-GGUF"),
            model_quantization=os.getenv("VLM_MODEL_QUANTIZATION", "Q8_0"),
            timeout_seconds=_int_env("LLAMA_TIMEOUT_SECONDS", 180),
            prompt_program_path=Path(
                os.getenv(
                    "DSPY_LEVEL1_PROGRAM_PATH",
                    str(DEFAULT_DSPY_LEVEL1_PROGRAM_PATH),
                )
            ),
        )

    if mode == "dspy":
        level1_program_path = os.getenv("DSPY_LEVEL1_PROGRAM_PATH")
        if not level1_program_path:
            raise ValueError(
                "DSPY_LEVEL1_PROGRAM_PATH must be set when VLM_CLASSIFIER_MODE=dspy."
            )
        return _load_dspy_classifier()(
            level1_program_path=Path(level1_program_path),
            variant_name=os.getenv("DSPY_VARIANT_NAME", "gepa"),
        )

    raise ValueError(
        f"Unsupported VLM_CLASSIFIER_MODE `{mode}`. Expected `llama` or `dspy`."
    )


app = create_app(
    redis_url=os.getenv("VLM_REDIS_URL", "redis://redis:6379/0"),
    classifier=build_classifier_from_env(),
    max_queue_size=_int_env("VLM_MAX_QUEUE_SIZE", 8),
    result_timeout_seconds=_int_env("VLM_RESULT_TIMEOUT_SECONDS", 240),
)
