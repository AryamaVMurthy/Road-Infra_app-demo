import io

from PIL import Image
from sqlmodel import select

from app.models.domain import AuditLog, Category, ReportIntakeSubmission, User
from app.services.issue_service import IssueService
from conftest import login_via_otp, seed_default_authority


def _jpeg_bytes() -> bytes:
    image = Image.new("RGB", (32, 32), color="blue")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def _seed_rejected_submission(session):
    seed_default_authority(session)
    sysadmin = User(email="sysadmin-archive@example.com", role="SYSADMIN")
    admin = User(email="admin-archive@example.com", role="ADMIN")
    citizen = User(email="citizen-archive@example.com", role="CITIZEN")
    category = Category(name="Pothole", classification_guidance="Road cavity")
    session.add(sysadmin)
    session.add(admin)
    session.add(citizen)
    session.add(category)
    session.commit()
    session.refresh(sysadmin)
    session.refresh(admin)
    session.refresh(citizen)

    file_path = IssueService.store_issue_photo(_jpeg_bytes(), prefix="issues")
    submission = ReportIntakeSubmission(
        reporter_id=citizen.id,
        status="REJECTED",
        reason_code="REJECTED",
        classification_source="vlm_gateway",
        model_id="LiquidAI/LFM2.5-VL-1.6B-GGUF",
        model_quantization="Q8_0",
        prompt_version="v1",
        lat=17.4447,
        lng=78.3483,
        file_path=file_path,
        mime_type="image/jpeg",
        image_sha256="archive123",
        raw_primary_result={"decision": "REJECTED"},
        raw_evaluator_result={"status": "skipped"},
        latency_ms=810,
    )
    session.add(submission)
    session.add(
        AuditLog(
            action="INTAKE_REJECTED",
            entity_type="INTAKE_SUBMISSION",
            entity_id=submission.id,
            actor_id=citizen.id,
            new_value="REJECTED",
        )
    )
    session.commit()
    session.refresh(submission)
    return sysadmin, admin, citizen, submission


def test_sysadmin_can_list_intake_archive(client, session):
    sysadmin, _, _, submission = _seed_rejected_submission(session)
    login_via_otp(client, session, sysadmin.email)

    response = client.get("/api/v1/admin/intake-archive")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == str(submission.id)
    assert body[0]["reason_code"] == "REJECTED"


def test_non_sysadmin_cannot_list_intake_archive(client, session):
    _, admin, citizen, _ = _seed_rejected_submission(session)

    login_via_otp(client, session, admin.email)
    assert client.get("/api/v1/admin/intake-archive").status_code == 403

    client.cookies.clear()
    login_via_otp(client, session, citizen.email)
    assert client.get("/api/v1/admin/intake-archive").status_code == 403


def test_sysadmin_can_fetch_archived_image(client, session):
    sysadmin, _, _, submission = _seed_rejected_submission(session)
    login_via_otp(client, session, sysadmin.email)

    response = client.get(f"/api/v1/admin/intake-archive/{submission.id}/image")

    assert response.status_code == 200
    assert "image/jpeg" in response.headers["content-type"]


def test_sysadmin_can_fetch_archived_submission_details(client, session):
    sysadmin, _, _, submission = _seed_rejected_submission(session)
    login_via_otp(client, session, sysadmin.email)

    response = client.get(f"/api/v1/admin/intake-archive/{submission.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(submission.id)
    assert body["reason_code"] == "REJECTED"
    assert body["model_quantization"] == "Q8_0"
    assert body["raw_primary_result"]["decision"] == "REJECTED"
