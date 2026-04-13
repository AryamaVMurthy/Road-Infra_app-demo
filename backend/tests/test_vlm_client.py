import httpx
import pytest

from app.services.vlm_client import (
    VLMClassificationResult,
    VLMGatewayClient,
    VLMGatewayContractError,
    VLMGatewayUnavailableError,
)


def test_vlm_client_maps_accepted_gateway_response():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "decision": "ACCEPTED_CATEGORY_MATCH",
                "category_name": "Pothole",
                "confidence": 0.92,
                "model_id": "LiquidAI/LFM2.5-VL-1.6B-GGUF",
                "model_quantization": "Q8_0",
                "prompt_version": "v1",
                "raw_primary_result": {"decision": "ACCEPTED_CATEGORY_MATCH"},
                "raw_evaluator_result": {"status": "pass"},
                "latency_ms": 1100,
            },
        )
    )

    client = VLMGatewayClient(
        "http://vlm-gateway:8090",
        timeout_seconds=5,
        transport=transport,
    )

    result = client.classify_intake(
        submission_id="sub-1",
        image_base64="ZmFrZQ==",
        mime_type="image/jpeg",
        reporter_notes="possible pothole",
        active_categories={"Pothole": "road cavity"},
        prompt_version="v1",
    )

    assert isinstance(result, VLMClassificationResult)
    assert result.decision == "ACCEPTED_CATEGORY_MATCH"
    assert result.category_name == "Pothole"
    assert result.model_quantization == "Q8_0"


def test_vlm_client_maps_rejected_gateway_response():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "decision": "REJECTED",
                "category_name": None,
                "confidence": None,
                "model_id": "LiquidAI/LFM2.5-VL-1.6B-GGUF",
                "model_quantization": "Q8_0",
                "prompt_version": "v1",
                "raw_primary_result": {"decision": "REJECTED"},
                "raw_evaluator_result": {
                    "status": "skipped",
                    "reason": "primary_rejection_does_not_require_category_confirmation",
                },
                "latency_ms": 980,
            },
        )
    )

    client = VLMGatewayClient(
        "http://vlm-gateway:8090",
        timeout_seconds=5,
        transport=transport,
    )

    result = client.classify_intake(
        submission_id="sub-2",
        image_base64="ZmFrZQ==",
        mime_type="image/jpeg",
        reporter_notes=None,
        active_categories={"Pothole": "road cavity"},
        prompt_version="v1",
    )

    assert result.decision == "REJECTED"
    assert result.category_name is None
    assert result.confidence is None


def test_vlm_client_raises_explicit_error_on_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    client = VLMGatewayClient(
        "http://vlm-gateway:8090",
        timeout_seconds=1,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(VLMGatewayUnavailableError):
        client.classify_intake(
            submission_id="sub-3",
            image_base64="ZmFrZQ==",
            mime_type="image/jpeg",
            reporter_notes=None,
            active_categories={"Pothole": "road cavity"},
            prompt_version="v1",
        )


def test_vlm_client_rejects_malformed_gateway_response():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "decision": "ACCEPTED_CATEGORY_MATCH",
            },
        )
    )

    client = VLMGatewayClient(
        "http://vlm-gateway:8090",
        timeout_seconds=5,
        transport=transport,
    )

    with pytest.raises(VLMGatewayContractError):
        client.classify_intake(
            submission_id="sub-4",
            image_base64="ZmFrZQ==",
            mime_type="image/jpeg",
            reporter_notes=None,
            active_categories={"Pothole": "road cavity"},
            prompt_version="v1",
        )
