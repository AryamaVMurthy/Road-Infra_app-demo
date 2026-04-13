"""Env-driven FastAPI server for the separate VLM gateway service."""

from __future__ import annotations

import os

from vlm_gateway.app.llama_client import create_llama_classifier
from vlm_gateway.app.main import create_app


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value is not None else default


app = create_app(
    redis_url=os.getenv("VLM_REDIS_URL", "redis://redis:6379/0"),
    classifier=create_llama_classifier(
        os.getenv("LLAMA_SERVER_URL", "http://llama-server:8081/v1/chat/completions"),
        model_id=os.getenv("VLM_MODEL_ID", "LiquidAI/LFM2.5-VL-1.6B-GGUF"),
        model_quantization=os.getenv("VLM_MODEL_QUANTIZATION", "Q8_0"),
        timeout_seconds=_int_env("LLAMA_TIMEOUT_SECONDS", 20),
    ),
    max_queue_size=_int_env("VLM_MAX_QUEUE_SIZE", 8),
    result_timeout_seconds=_int_env("VLM_RESULT_TIMEOUT_SECONDS", 25),
)
