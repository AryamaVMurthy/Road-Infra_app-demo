"""FastAPI entrypoint for the Redis-backed VLM gateway."""

from __future__ import annotations

import threading
from contextlib import asynccontextmanager
from typing import Any, Callable

from fastapi import FastAPI, HTTPException

from vlm_gateway.app.queue import QueueFullError, RedisJobQueue
from vlm_gateway.app.schemas import (
    IntakeClassificationRequest,
    IntakeClassificationResponse,
)
from vlm_gateway.app.worker import run_worker


Classifier = Callable[[dict[str, Any]], dict[str, Any]]


def create_app(
    *,
    redis_url: str,
    classifier: Classifier,
    max_queue_size: int = 8,
    result_timeout_seconds: int = 25,
) -> FastAPI:
    queue = RedisJobQueue(redis_url=redis_url, max_queue_size=max_queue_size)
    stop_event = threading.Event()
    worker_thread = threading.Thread(
        target=run_worker,
        kwargs={
            "queue": queue,
            "classifier": classifier,
            "stop_event": stop_event,
        },
        name="vlm-gateway-worker",
        daemon=True,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.queue = queue
        app.state.result_timeout_seconds = result_timeout_seconds
        app.state.stop_event = stop_event
        worker_thread.start()
        try:
            yield
        finally:
            stop_event.set()
            worker_thread.join(timeout=5)

    app = FastAPI(lifespan=lifespan)

    @app.post(
        "/internal/v1/intake/classify",
        response_model=IntakeClassificationResponse,
    )
    def classify_intake(payload: IntakeClassificationRequest) -> dict[str, Any]:
        job = payload.model_dump()
        try:
            queue.enqueue(job)
        except QueueFullError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        result = queue.await_result(
            payload.submission_id,
            timeout_seconds=result_timeout_seconds,
        )
        if result is None:
            raise HTTPException(
                status_code=503,
                detail="Timed out waiting for VLM classification result",
            )
        return result

    return app
