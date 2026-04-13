from uuid import UUID

from sqlmodel import select

from app.models.domain import AuditLog, Category, Issue, User
from conftest import login_via_otp, seed_default_authority


def _seed_issue_with_categories(session):
    _, organization = seed_default_authority(session)
    admin = User(email="reclass-admin@example.com", role="ADMIN", org_id=organization.id)
    sysadmin = User(email="reclass-sys@example.com", role="SYSADMIN")
    worker = User(email="reclass-worker@example.com", role="WORKER", org_id=organization.id)
    citizen = User(email="reclass-citizen@example.com", role="CITIZEN")
    pothole = Category(name="Pothole", classification_guidance="Road cavity")
    drainage = Category(name="Drainage", classification_guidance="Blocked drain")
    session.add(admin)
    session.add(sysadmin)
    session.add(worker)
    session.add(citizen)
    session.add(pothole)
    session.add(drainage)
    session.commit()
    session.refresh(citizen)
    session.refresh(pothole)
    session.refresh(drainage)

    issue = Issue(
        category_id=pothole.id,
        status="REPORTED",
        location="SRID=4326;POINT(78.3483 17.4447)",
        reporter_id=citizen.id,
        org_id=organization.id,
        report_count=1,
        classification_source="vlm_gateway",
        classification_confidence=0.9,
        classification_model_id="LiquidAI/LFM2.5-VL-1.6B-GGUF",
        classification_model_quantization="Q8_0",
        classification_prompt_version="v1",
    )
    session.add(issue)
    session.commit()
    session.refresh(issue)
    return admin, sysadmin, worker, citizen, pothole, drainage, issue


def test_admin_can_reclassify_issue_and_audit_it(client, session):
    admin, _, _, _, pothole, drainage, issue = _seed_issue_with_categories(session)
    login_via_otp(client, session, admin.email)

    response = client.post(
        f"/api/v1/admin/issues/{issue.id}/reclassify",
        json={"category_id": str(drainage.id), "reason": "Manual review found drainage issue"},
    )

    assert response.status_code == 200
    session.expire_all()
    updated_issue = session.get(Issue, issue.id)
    assert updated_issue.category_id == drainage.id

    audit = session.exec(
        select(AuditLog).where(AuditLog.action == "CATEGORY_OVERRIDE")
    ).one()
    assert audit.entity_id == issue.id
    assert audit.old_value == str(pothole.id)
    assert audit.new_value == str(drainage.id)


def test_sysadmin_can_reclassify_issue(client, session):
    _, sysadmin, _, _, _, drainage, issue = _seed_issue_with_categories(session)
    login_via_otp(client, session, sysadmin.email)

    response = client.post(
        f"/api/v1/admin/issues/{issue.id}/reclassify",
        json={"category_id": str(drainage.id), "reason": "Override"},
    )

    assert response.status_code == 200


def test_citizen_and_worker_cannot_reclassify_issue(client, session):
    _, _, worker, citizen, _, drainage, issue = _seed_issue_with_categories(session)

    login_via_otp(client, session, citizen.email)
    citizen_response = client.post(
        f"/api/v1/admin/issues/{issue.id}/reclassify",
        json={"category_id": str(drainage.id), "reason": "Override"},
    )
    assert citizen_response.status_code == 403

    client.cookies.clear()
    login_via_otp(client, session, worker.email)
    worker_response = client.post(
        f"/api/v1/admin/issues/{issue.id}/reclassify",
        json={"category_id": str(drainage.id), "reason": "Override"},
    )
    assert worker_response.status_code == 403
