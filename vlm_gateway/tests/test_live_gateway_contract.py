import base64
from pathlib import Path

from fastapi.testclient import TestClient

from vlm_gateway.app.llama_client import create_llama_classifier
from vlm_gateway.app.main import create_app


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_live_gateway_returns_contract_valid_response(redis_url):
    image_bytes = (PROJECT_ROOT / "test_e2e.jpg").read_bytes()
    app = create_app(
        redis_url=redis_url,
        classifier=create_llama_classifier("http://localhost:8081/v1/chat/completions"),
        result_timeout_seconds=45,
    )

    payload = {
        "submission_id": "live-sub-1",
        "image_base64": base64.b64encode(image_bytes).decode("ascii"),
        "mime_type": "image/jpeg",
        "reporter_notes": "Possible civic road issue near a divider.",
        "active_categories": {
            "Pothole": "Road-surface collapse or cavity in drivable area",
            "Drainage": "Blocked drain, standing water, or overflow",
        },
        "prompt_version": "live-v1",
    }

    with TestClient(app) as client:
        response = client.post("/internal/v1/intake/classify", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] in {"IN_SCOPE", "REJECTED"}
    assert body["model_id"] == "LiquidAI/LFM2.5-VL-1.6B-GGUF"
    assert body["prompt_version"] == "live-v1"
    assert isinstance(body["latency_ms"], int)
    assert body["raw_evaluator_result"] == {
        "status": "not_run",
        "reason": "level1_only_classifier",
    }
