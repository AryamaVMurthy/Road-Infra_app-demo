import io

from PIL import Image
from sqlmodel import select

from app.api.deps import get_vlm_gateway_client
from app.main import app as fastapi_app
from app.models.domain import Category, Evidence, Issue, ReportIntakeSubmission, User
from conftest import login_via_otp, seed_default_authority


class FakeVLMClient:
    def __init__(self, result):
        self._result = result

    def classify_intake(self, **kwargs):
        return self._result


def _jpeg_bytes() -> bytes:
    image = Image.new("RGB", (64, 64), color="red")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def _accepted_result(category_name: str = "Pothole"):
    from app.services.vlm_client import VLMClassificationResult

    return VLMClassificationResult(
        decision="ACCEPTED_CATEGORY_MATCH",
        category_name=category_name,
        confidence=0.94,
        model_id="LiquidAI/LFM2.5-VL-1.6B-GGUF",
        model_quantization="Q8_0",
        prompt_version="v1",
        raw_primary_result={"decision": "ACCEPTED_CATEGORY_MATCH"},
        raw_evaluator_result={"status": "pass"},
        latency_ms=900,
    )


def _rejected_result():
    from app.services.vlm_client import VLMClassificationResult

    return VLMClassificationResult(
        decision="REJECTED",
        category_name=None,
        confidence=0.89,
        model_id="LiquidAI/LFM2.5-VL-1.6B-GGUF",
        model_quantization="Q8_0",
        prompt_version="v1",
        raw_primary_result={"decision": "REJECTED"},
        raw_evaluator_result={
            "status": "skipped",
            "reason": "primary_rejection_does_not_require_category_confirmation",
        },
        latency_ms=870,
    )


def test_report_issue_auto_classifies_without_category_id(client, session):
    seed_default_authority(session)
    session.add(
        Category(
            name="Pothole",
            default_priority="P2",
            classification_guidance="Road-surface cavity or collapse",
        )
    )
    session.add(
        Category(
            name="Drainage",
            classification_guidance="Blocked drain or standing water",
        )
    )
    reporter = User(email="vlm-reporter@example.com", role="CITIZEN")
    session.add(reporter)
    session.commit()
    login_via_otp(client, session, reporter.email)

    fastapi_app.dependency_overrides[get_vlm_gateway_client] = lambda: FakeVLMClient(
        _accepted_result()
    )

    response = client.post(
        "/api/v1/issues/report",
        data={
            "lat": 17.4447,
            "lng": 78.3483,
            "address": "Main Road",
            "description": "road issue near divider",
        },
        files={"photo": ("test.jpg", _jpeg_bytes(), "image/jpeg")},
    )

    fastapi_app.dependency_overrides.pop(get_vlm_gateway_client, None)

    assert response.status_code == 200
    body = response.json()
    assert body["category_name"] == "Pothole"
    assert body["duplicate_merged"] is False
    assert body["submission_id"]

    issue = session.exec(select(Issue)).one()
    evidence = session.exec(select(Evidence)).all()
    submission = session.exec(select(ReportIntakeSubmission)).one()

    assert issue.category_name == "Pothole"
    assert issue.classification_model_id == "LiquidAI/LFM2.5-VL-1.6B-GGUF"
    assert len(evidence) == 1
    assert submission.status == "ACCEPTED"
    assert submission.issue_id == issue.id


def test_report_issue_rejection_is_archived_without_creating_issue(client, session):
    seed_default_authority(session)
    session.add(
        Category(
            name="Pothole",
            classification_guidance="Road-surface cavity or collapse",
        )
    )
    reporter = User(email="reject-reporter@example.com", role="CITIZEN")
    session.add(reporter)
    session.commit()
    login_via_otp(client, session, reporter.email)

    fastapi_app.dependency_overrides[get_vlm_gateway_client] = lambda: FakeVLMClient(
        _rejected_result()
    )

    response = client.post(
        "/api/v1/issues/report",
        data={
            "lat": 17.4447,
            "lng": 78.3483,
            "description": "spam upload",
        },
        files={"photo": ("test.jpg", _jpeg_bytes(), "image/jpeg")},
    )

    fastapi_app.dependency_overrides.pop(get_vlm_gateway_client, None)

    assert response.status_code == 422
    body = response.json()
    assert body["submission_id"]

    assert session.exec(select(Issue)).all() == []
    submission = session.exec(select(ReportIntakeSubmission)).one()
    assert submission.status == "REJECTED"
    assert submission.reason_code == "REJECTED"
    assert submission.issue_id is None


def test_duplicate_auto_classified_report_merges_into_existing_issue(client, session):
    seed_default_authority(session)
    session.add(
        Category(
            name="Pothole",
            classification_guidance="Road-surface cavity or collapse",
        )
    )
    reporter = User(email="dup-reporter@example.com", role="CITIZEN")
    session.add(reporter)
    session.commit()
    login_via_otp(client, session, reporter.email)

    fastapi_app.dependency_overrides[get_vlm_gateway_client] = lambda: FakeVLMClient(
        _accepted_result()
    )

    first = client.post(
        "/api/v1/issues/report",
        data={
            "lat": 17.4447,
            "lng": 78.3483,
            "description": "first report",
        },
        files={"photo": ("first.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    second = client.post(
        "/api/v1/issues/report",
        data={
            "lat": 17.444701,
            "lng": 78.348301,
            "description": "duplicate report",
        },
        files={"photo": ("second.jpg", _jpeg_bytes(), "image/jpeg")},
    )

    fastapi_app.dependency_overrides.pop(get_vlm_gateway_client, None)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["duplicate_merged"] is True

    issues = session.exec(select(Issue)).all()
    submissions = session.exec(select(ReportIntakeSubmission)).all()
    assert len(issues) == 1
    assert issues[0].report_count == 2
    assert len(submissions) == 2
    assert all(sub.issue_id == issues[0].id for sub in submissions)
