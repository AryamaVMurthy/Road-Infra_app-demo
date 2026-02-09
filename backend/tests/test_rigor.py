import pytest
from app.models.domain import Category, User, Issue, AuditLog
from sqlmodel import Session, select, col, desc
from uuid import uuid4
from datetime import datetime, timedelta
from app.models.domain import Otp


def _login(client, session: Session, email: str):
    client.post("/api/v1/auth/otp-request", json={"email": email})
    otp = (
        session.exec(
            select(Otp).where(Otp.email == email).order_by(desc(Otp.created_at))
        )
        .first()
    )
    assert otp is not None
    response = client.post("/api/v1/auth/login", json={"email": email, "otp": otp.code})
    assert response.status_code == 200


def test_sla_breach_detection_logic(session):
    # Setup
    cat = Category(name="Pothole", expected_sla_days=3)
    session.add(cat)
    reporter = User(email="rep@test.com", role="CITIZEN")
    session.add(reporter)
    session.commit()

    # Create an issue from 5 days ago (should be breached)
    five_days_ago = datetime.utcnow() - timedelta(days=5)
    issue = Issue(
        category_id=cat.id,
        status="REPORTED",
        location="SRID=4326;POINT(78.3 17.4)",
        reporter_id=reporter.id,
        created_at=five_days_ago,
    )
    session.add(issue)
    session.commit()
    session.refresh(issue)

    # Logic check: (Current - Created) > SLA
    age = datetime.utcnow() - issue.created_at
    is_breached = age.days > cat.expected_sla_days
    assert is_breached is True


def test_bulk_assignment_rigor(client, session):
    # Setup
    cat = Category(name="Pothole")
    session.add(cat)
    admin = User(email="admin@authority.gov.in", role="ADMIN")
    session.add(admin)
    worker = User(email="worker1@authority.gov.in", role="WORKER")
    session.add(worker)

    issues = []
    for i in range(5):
        issue = Issue(
            category_id=cat.id,
            status="REPORTED",
            location="SRID=4326;POINT(78.3 17.4)",
            reporter_id=admin.id,
        )
        session.add(issue)
        issues.append(issue)
    session.commit()
    for i in issues:
        session.refresh(i)

    _login(client, session, "admin@authority.gov.in")

    issue_ids = [str(i.id) for i in issues]
    response = client.post(
        "/api/v1/admin/bulk-assign",
        json={"issue_ids": issue_ids, "worker_id": str(worker.id)},
    )
    assert response.status_code == 200

    # Verify all updated
    for i_id in issue_ids:
        issue = session.get(Issue, i_id)
        assert issue.status == "ASSIGNED"
        assert issue.worker_id == worker.id

    # Verify AuditLogs
    audit_logs = session.exec(
        select(AuditLog).where(AuditLog.action == "ASSIGNMENT")
    ).all()
    assert len(audit_logs) == 5


def test_worker_deactivation_lifecycle(client, session):
    # Setup
    admin = User(email="sysadmin@test.com", role="SYSADMIN")
    session.add(admin)
    worker = User(email="leaver@test.com", role="WORKER", status="ACTIVE")
    session.add(worker)
    cat = Category(name="Pothole")
    session.add(cat)
    session.commit()

    # Assign a task to the worker
    issue = Issue(
        category_id=cat.id,
        status="ASSIGNED",
        worker_id=worker.id,
        location="SRID=4326;POINT(78.3 17.4)",
        reporter_id=admin.id,
    )
    session.add(issue)
    session.commit()

    _login(client, session, "sysadmin@test.com")

    response = client.post(f"/api/v1/admin/deactivate-worker?worker_id={worker.id}")
    assert response.status_code == 200

    # Verify status changed
    session.refresh(worker)
    assert worker.status == "INACTIVE"

    # Verify task reset
    session.refresh(issue)
    assert issue.status == "REPORTED"
    assert issue.worker_id is None

    # Verify AuditLog for unassignment
    unassign_log = session.exec(
        select(AuditLog).where(AuditLog.action == "AUTO_UNASSIGN")
    ).first()
    assert unassign_log is not None
    assert unassign_log.entity_id == issue.id
