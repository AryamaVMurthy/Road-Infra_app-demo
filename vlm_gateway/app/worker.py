"""Background worker loop for the VLM gateway queue."""

from __future__ import annotations

import threading
from typing import Any, Callable

from vlm_gateway.app.queue import RedisJobQueue


Classifier = Callable[[dict[str, Any]], dict[str, Any]]


def run_worker(
    *,
    queue: RedisJobQueue,
    classifier: Classifier,
    stop_event: threading.Event,
) -> None:
    while not stop_event.is_set():
        job = queue.pop_job(timeout_seconds=1)
        if job is None:
            continue

        try:
            result = classifier(job)
        except Exception as exc:  # noqa: BLE001
            result = {
                "decision": "SYSTEM_ERROR",
                "category_name": None,
                "confidence": None,
                "model_id": "unknown",
                "model_quantization": "unknown",
                "prompt_version": job.get("prompt_version", ""),
                "raw_primary_result": {
                    "error": str(exc),
                },
                "raw_evaluator_result": {
                    "status": "fail",
                    "failure_reason": "classifier_exception",
                },
                "latency_ms": 0,
            }

        queue.publish_result(job["submission_id"], result)
