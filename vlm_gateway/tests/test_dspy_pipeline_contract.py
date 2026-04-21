import os
from pathlib import Path
import sys

import dspy
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def clear_gateway_redis():
    yield


def _load_pipeline_module():
    import importlib.util

    spec = importlib.util.find_spec("vlm_gateway.app.dspy_pipeline")
    assert spec is not None, "Expected vlm_gateway.app.dspy_pipeline to exist for the DSPy gateway slice."
    return __import__("vlm_gateway.app.dspy_pipeline", fromlist=["placeholder"])


def _load_server_module():
    import importlib.util

    spec = importlib.util.find_spec("vlm_gateway.app.server")
    assert spec is not None, "Expected vlm_gateway.app.server to exist for the DSPy gateway slice."
    return __import__("vlm_gateway.app.server", fromlist=["placeholder"])


class StubLevel1Program:
    def __init__(self, decision: str, hint: str, rationale: str):
        self.decision = decision
        self.hint = hint
        self.rationale = rationale

    def __call__(self, *, image, category_catalog):
        return dspy.Prediction(
            decision=self.decision,
            best_matching_category_hint=self.hint,
            rationale=self.rationale,
        )


def _job(active_categories: dict[str, str] | None = None) -> dict[str, object]:
    return {
        "submission_id": "sub-1",
        "image_base64": "ZmFrZQ==",
        "mime_type": "image/jpeg",
        "reporter_notes": "road issue near divider",
        "active_categories": active_categories
        or {
            "pothole": "Broken or missing road surface forming a visible hole or cavity.",
            "damaged_road": "Cracked, eroded, or broken road surface without a discrete pothole cavity.",
            "damaged_road_sign": "Missing, broken, bent, or unreadable roadside sign infrastructure.",
            "garbage_litter": "Visible dumped waste or litter accumulation in public roadside space.",
        },
        "prompt_version": "dspy-v1",
    }


def test_dspy_pipeline_returns_existing_gateway_contract_for_accepted_and_rejected():
    pipeline = _load_pipeline_module()
    accepted_classifier = pipeline.create_dspy_classifier(
        level1_program=StubLevel1Program(
            decision="IN_SCOPE",
            hint="pothole",
            rationale="Visible road cavity.",
        ),
        variant_name="gepa",
    )
    rejected_classifier = pipeline.create_dspy_classifier(
        level1_program=StubLevel1Program(
            decision="REJECT",
            hint="",
            rationale="No supported civic issue visible.",
        ),
        variant_name="gepa",
    )

    accepted = accepted_classifier(_job())
    rejected = rejected_classifier(_job())

    assert accepted["decision"] == "IN_SCOPE"
    assert accepted["category_name"] is None
    assert accepted["confidence"] is None
    assert accepted["model_id"] == "gpt-5.4-mini"
    assert accepted["model_quantization"] == "dspy-gepa"
    assert rejected["decision"] == "REJECTED"
    assert rejected["category_name"] is None


def test_dspy_pipeline_preserves_level1_hint_in_raw_result():
    pipeline = _load_pipeline_module()
    classifier = pipeline.create_dspy_classifier(
        level1_program=StubLevel1Program(
            decision="IN_SCOPE",
            hint="pothole",
            rationale="Visible road cavity.",
        ),
        variant_name="gepa",
    )

    result = classifier(_job())

    assert result["decision"] == "IN_SCOPE"
    assert result["raw_primary_result"]["level1"]["best_matching_category_hint"] == "pothole"


def test_dspy_pipeline_fails_fast_when_artifacts_are_missing(tmp_path: Path):
    pipeline = _load_pipeline_module()

    with pytest.raises(ValueError, match="does not exist"):
        pipeline.load_dspy_classifier(
            level1_program_path=tmp_path / "missing-level1",
            variant_name="gepa",
        )


def test_dspy_pipeline_rejects_active_category_sets_outside_supported_catalog():
    pipeline = _load_pipeline_module()
    classifier = pipeline.create_dspy_classifier(
        level1_program=StubLevel1Program(
            decision="REJECT",
            hint="",
            rationale="No supported civic issue visible.",
        ),
        variant_name="gepa",
    )

    with pytest.raises(ValueError, match="must exactly match the DSPy category catalog"):
        classifier(
            _job(
                {
                    "Pothole": "Road-surface collapse or cavity in drivable area",
                    "Drainage": "Blocked drain, standing water, or overflow",
                }
            )
        )


def test_server_mode_selection_uses_dspy_pipeline_and_fails_fast_when_paths_are_missing(
    monkeypatch: pytest.MonkeyPatch,
):
    server = _load_server_module()
    seen = {}

    def fake_load_dspy_classifier(**kwargs):
        seen.update(kwargs)
        return lambda job: {"decision": "REJECTED"}

    monkeypatch.setattr(
        server,
        "_load_dspy_classifier",
        lambda: fake_load_dspy_classifier,
    )
    monkeypatch.setenv("VLM_CLASSIFIER_MODE", "dspy")
    monkeypatch.setenv("DSPY_LEVEL1_PROGRAM_PATH", "/tmp/level1-program")
    monkeypatch.setenv("DSPY_VARIANT_NAME", "mipro")

    classifier = server.build_classifier_from_env()

    assert callable(classifier)
    assert seen["level1_program_path"] == Path("/tmp/level1-program")
    assert seen["variant_name"] == "mipro"

    monkeypatch.delenv("DSPY_LEVEL1_PROGRAM_PATH")
    with pytest.raises(ValueError, match="DSPY_LEVEL1_PROGRAM_PATH"):
        server.build_classifier_from_env()


def test_server_mode_selection_defaults_to_llama(monkeypatch: pytest.MonkeyPatch):
    server = _load_server_module()
    seen = {}

    def fake_create_llama_classifier(endpoint, **kwargs):
        seen["endpoint"] = endpoint
        seen["kwargs"] = kwargs
        return lambda job: {"decision": "REJECTED"}

    monkeypatch.setattr(server, "create_llama_classifier", fake_create_llama_classifier)
    monkeypatch.delenv("VLM_CLASSIFIER_MODE", raising=False)

    classifier = server.build_classifier_from_env()

    assert callable(classifier)
    assert seen["endpoint"] == "http://llama-server:8081/v1/chat/completions"
