import io

from PIL import Image
from sqlmodel import select

from app.models.domain import AuditLog, Category, Evidence, Issue, ReportIntakeSubmission, User
from app.services.issue_service import IssueService
from conftest import login_via_otp, seed_default_authority


def _jpeg_bytes() -> bytes:
    image = Image.new("RGB", (32, 32), color="blue")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def _seed_rejected_submission(session):
    _, organization = seed_default_authority(session)
    sysadmin = User(email="sysadmin-archive@example.com", role="SYSADMIN")
    admin = User(email="admin-archive@example.com", role="ADMIN", org_id=organization.id)
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
        org_id=organization.id,
        status="REJECTED_SPAM",
        reason_code="SPAM_REJECTED",
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
            new_value="REJECTED_SPAM",
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
    assert body[0]["reason_code"] == "SPAM_REJECTED"


def test_admin_cannot_list_intake_archive(client, session):
    _, admin, _, submission = _seed_rejected_submission(session)

    login_via_otp(client, session, admin.email)
    response = client.get("/api/v1/admin/intake-archive")

    assert response.status_code == 403


def test_citizen_cannot_list_intake_archive(client, session):
    _, _, citizen, _ = _seed_rejected_submission(session)

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
    assert body["reason_code"] == "SPAM_REJECTED"
    assert body["model_quantization"] == "Q8_0"
    assert body["raw_primary_result"]["decision"] == "REJECTED"


def test_sysadmin_can_override_spam_decision_into_uncategorized_issue(client, session):
    sysadmin, _, _, submission = _seed_rejected_submission(session)
    login_via_otp(client, session, sysadmin.email)

    response = client.post(
        f"/api/v1/admin/intake-archive/{submission.id}/mark-not-spam",
        json={"reason": "Manual review confirmed valid civic issue"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Submission converted into an uncategorized issue"

    session.expire_all()
    created_issue = session.exec(select(Issue)).one()
    created_evidence = session.exec(select(Evidence)).one()
    updated_submission = session.get(ReportIntakeSubmission, submission.id)
    override_audit = session.exec(
        select(AuditLog).where(AuditLog.action == "INTAKE_OVERRIDE_TO_ACCEPTED")
    ).one()

    assert created_issue.category_id is None
    assert created_issue.intake_submission_id == updated_submission.id
    assert created_evidence.issue_id == created_issue.id
    assert updated_submission.issue_id == created_issue.id
    assert updated_submission.status == "ACCEPTED_UNCATEGORIZED"
    assert updated_submission.reason_code == "OVERRIDDEN_NOT_SPAM"
    assert override_audit.entity_id == submission.id


def test_admin_cannot_override_spam_decision(client, session):
    _, admin, _, submission = _seed_rejected_submission(session)
    login_via_otp(client, session, admin.email)

    response = client.post(
        f"/api/v1/admin/intake-archive/{submission.id}/mark-not-spam",
        json={"reason": "Manual review confirmed valid civic issue"},
    )

    assert response.status_code == 403
