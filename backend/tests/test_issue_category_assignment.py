from sqlmodel import select

from app.models.domain import AuditLog, Category, Issue, User
from conftest import login_via_otp, seed_default_authority


def _seed_uncategorized_issue(session):
    _, organization = seed_default_authority(session)
    admin = User(email="assign-admin@example.com", role="ADMIN", org_id=organization.id)
    sysadmin = User(email="assign-sys@example.com", role="SYSADMIN")
    worker = User(email="assign-worker@example.com", role="WORKER", org_id=organization.id)
    citizen = User(email="assign-citizen@example.com", role="CITIZEN")
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
        category_id=None,
        status="REPORTED",
        location="SRID=4326;POINT(78.3483 17.4447)",
        reporter_id=citizen.id,
        org_id=organization.id,
        report_count=1,
        classification_source="vlm_gateway",
        classification_confidence=0.9,
        classification_model_id="gpt-5.4-mini",
        classification_prompt_version="level1-gepa",
    )
    session.add(issue)
    session.commit()
    session.refresh(issue)
    return admin, sysadmin, worker, citizen, pothole, drainage, issue


def test_admin_can_assign_category_to_uncategorized_issue(client, session):
    admin, _, _, _, _, drainage, issue = _seed_uncategorized_issue(session)
    login_via_otp(client, session, admin.email)

    response = client.post(
        f"/api/v1/admin/issues/{issue.id}/assign-category",
        json={"category_id": str(drainage.id)},
    )

    assert response.status_code == 200
    session.expire_all()
    updated_issue = session.get(Issue, issue.id)
    assert updated_issue.category_id == drainage.id

    audit = session.exec(
        select(AuditLog).where(AuditLog.action == "CATEGORY_ASSIGNED")
    ).one()
    assert audit.entity_id == issue.id
    assert audit.old_value is None
    assert audit.new_value == str(drainage.id)


def test_sysadmin_can_reassign_existing_category_and_audit_it(client, session):
    _, sysadmin, _, _, pothole, drainage, issue = _seed_uncategorized_issue(session)
    issue.category_id = pothole.id
    session.add(issue)
    session.commit()

    login_via_otp(client, session, sysadmin.email)
    response = client.post(
        f"/api/v1/admin/issues/{issue.id}/assign-category",
        json={"category_id": str(drainage.id)},
    )

    assert response.status_code == 200
    session.expire_all()
    updated_issue = session.get(Issue, issue.id)
    assert updated_issue.category_id == drainage.id

    audit = session.exec(
        select(AuditLog).where(AuditLog.action == "CATEGORY_REASSIGNED")
    ).one()
    assert audit.entity_id == issue.id
    assert audit.old_value == str(pothole.id)
    assert audit.new_value == str(drainage.id)


def test_citizen_and_worker_cannot_assign_issue_category(client, session):
    _, _, worker, citizen, _, drainage, issue = _seed_uncategorized_issue(session)

    login_via_otp(client, session, citizen.email)
    citizen_response = client.post(
        f"/api/v1/admin/issues/{issue.id}/assign-category",
        json={"category_id": str(drainage.id)},
    )
    assert citizen_response.status_code == 403

    client.cookies.clear()
    login_via_otp(client, session, worker.email)
    worker_response = client.post(
        f"/api/v1/admin/issues/{issue.id}/assign-category",
        json={"category_id": str(drainage.id)},
    )
    assert worker_response.status_code == 403
