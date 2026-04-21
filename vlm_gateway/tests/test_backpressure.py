import threading
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from vlm_gateway.app.main import create_app


def _payload(submission_id: str) -> dict:
    return {
        "submission_id": submission_id,
        "image_base64": "ZmFrZQ==",
        "mime_type": "image/jpeg",
        "reporter_notes": "road issue near divider",
        "active_categories": {
            "Pothole": "Road-surface collapse or cavity in drivable area",
        },
        "prompt_version": "v1",
    }


def test_gateway_returns_overload_when_queue_is_full(redis_url):
    release = threading.Event()

    def slow_classifier(job):
        release.wait(timeout=5)
        return {
            "decision": "IN_SCOPE",
            "category_name": None,
            "confidence": 0.9,
            "model_id": "fake-model",
            "model_quantization": "Q8_0",
            "prompt_version": job["prompt_version"],
            "raw_primary_result": {"decision": "IN_SCOPE"},
            "raw_evaluator_result": {"status": "pass"},
            "latency_ms": 200,
        }

    app = create_app(
        redis_url=redis_url,
        classifier=slow_classifier,
        max_queue_size=1,
        result_timeout_seconds=3,
    )

    with TestClient(app) as client:
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(
                client.post, "/internal/v1/intake/classify", json=_payload("sub-1")
            )
            time.sleep(0.1)
            second = executor.submit(
                client.post, "/internal/v1/intake/classify", json=_payload("sub-2")
            )
            time.sleep(0.1)
            third = client.post("/internal/v1/intake/classify", json=_payload("sub-3"))
            release.set()

            assert first.result().status_code == 200
            assert second.result().status_code == 200

    assert third.status_code == 503
    assert third.json()["detail"] == "VLM queue is full"
