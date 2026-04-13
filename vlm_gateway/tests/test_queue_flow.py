import threading
import time

from fastapi.testclient import TestClient

from vlm_gateway.app.main import create_app
from vlm_gateway.app.queue import RedisJobQueue
from vlm_gateway.app.worker import run_worker


def _payload(submission_id: str) -> dict:
    return {
        "submission_id": submission_id,
        "image_base64": "ZmFrZQ==",
        "mime_type": "image/jpeg",
        "reporter_notes": "road issue near divider",
        "active_categories": {
            "Pothole": "Road-surface collapse or cavity in drivable area",
            "Drainage": "Blocked drain, standing water, or overflow",
        },
        "prompt_version": "v1",
    }


def test_enqueue_request_roundtrip_returns_completed_result(redis_url):
    def fake_classifier(job):
        return {
            "decision": "ACCEPTED_CATEGORY_MATCH",
            "category_name": "Pothole",
            "confidence": 0.91,
            "model_id": "fake-model",
            "model_quantization": "Q8_0",
            "prompt_version": job["prompt_version"],
            "raw_primary_result": {"decision": "ACCEPTED_CATEGORY_MATCH"},
            "raw_evaluator_result": {"status": "pass"},
            "latency_ms": 12,
        }

    app = create_app(redis_url=redis_url, classifier=fake_classifier)

    with TestClient(app) as client:
        response = client.post("/internal/v1/intake/classify", json=_payload("sub-1"))

    assert response.status_code == 200
    assert response.json()["decision"] == "ACCEPTED_CATEGORY_MATCH"
    assert response.json()["category_name"] == "Pothole"


def test_gateway_processes_requests_in_fifo_order(redis_url):
    processed = []

    def fake_classifier(job):
        processed.append(job["submission_id"])
        time.sleep(0.1)
        return {
            "decision": "ACCEPTED_CATEGORY_MATCH",
            "category_name": "Pothole",
            "confidence": 0.95,
            "model_id": "fake-model",
            "model_quantization": "Q8_0",
            "prompt_version": job["prompt_version"],
            "raw_primary_result": {"decision": "ACCEPTED_CATEGORY_MATCH"},
            "raw_evaluator_result": {"status": "pass"},
            "latency_ms": 20,
        }

    queue = RedisJobQueue(redis_url=redis_url, max_queue_size=8)
    stop_event = threading.Event()
    worker = threading.Thread(
        target=run_worker,
        kwargs={
            "queue": queue,
            "classifier": fake_classifier,
            "stop_event": stop_event,
        },
        daemon=True,
    )

    queue.enqueue(_payload("sub-1"))
    queue.enqueue(_payload("sub-2"))

    worker.start()
    first = queue.await_result("sub-1", timeout_seconds=3)
    second = queue.await_result("sub-2", timeout_seconds=3)
    stop_event.set()
    worker.join(timeout=2)

    assert first is not None
    assert second is not None
    assert processed == ["sub-1", "sub-2"]
