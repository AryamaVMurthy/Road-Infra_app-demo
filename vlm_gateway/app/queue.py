"""Redis-backed queue primitives for the VLM gateway."""

from __future__ import annotations

import json
import threading
from typing import Any

import redis


class QueueFullError(RuntimeError):
    """Raised when the configured queue capacity is exhausted."""


class RedisJobQueue:
    def __init__(
        self,
        *,
        redis_url: str,
        max_queue_size: int,
        queue_key: str = "vlm_gateway:pending",
    ) -> None:
        self._client = redis.from_url(redis_url, decode_responses=True)
        self._queue_key = queue_key
        self._max_queue_size = max_queue_size
        self._enqueue_lock = threading.Lock()

    @property
    def client(self) -> redis.Redis:
        return self._client

    def enqueue(self, job: dict[str, Any]) -> None:
        with self._enqueue_lock:
            queue_depth = self._client.zcard(self._queue_key)
            if queue_depth >= self._max_queue_size:
                raise QueueFullError("VLM queue is full")
            encoded = self._encode_job(job)
            # Equal scores keep ordering deterministic by member value, which
            # lets the synchronous queue stay stable under concurrent tests.
            self._client.zadd(self._queue_key, {encoded: 0})

    def pop_job(self, *, timeout_seconds: int = 1) -> dict[str, Any] | None:
        item = self._client.bzpopmin(self._queue_key, timeout=timeout_seconds)
        if item is None:
            return None
        _, payload, _ = item
        return self._decode_job(payload)

    def publish_result(self, submission_id: str, result: dict[str, Any]) -> None:
        self._client.rpush(self._result_key(submission_id), json.dumps(result))

    def await_result(
        self, submission_id: str, *, timeout_seconds: int
    ) -> dict[str, Any] | None:
        item = self._client.blpop(
            self._result_key(submission_id), timeout=timeout_seconds
        )
        if item is None:
            return None
        _, payload = item
        return json.loads(payload)

    def _result_key(self, submission_id: str) -> str:
        return f"vlm_gateway:result:{submission_id}"

    def _encode_job(self, job: dict[str, Any]) -> str:
        submission_id = str(job["submission_id"])
        return f"{submission_id}|{json.dumps(job, sort_keys=True)}"

    def _decode_job(self, payload: str) -> dict[str, Any]:
        _, encoded_job = payload.split("|", 1)
        return json.loads(encoded_job)
