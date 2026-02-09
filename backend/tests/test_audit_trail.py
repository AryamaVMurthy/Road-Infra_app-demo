"""
Audit Trail Tests

Verifies that every workflow action creates correct AuditLog entries with
exact action, entity_type, entity_id, actor_id, old_value, and new_value.

Covers:
  1. Assignment audits (assign, reassign, unassign)
  2. Status change audits (manual, approve, reject)
  3. Worker audits (accept, start, resolve)
  4. Priority change audits
  5. Audit endpoint (ordering, completeness)
  6. Golden path full audit trail
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlmodel import Session, select, desc

from app.models.domain import Category, User, Issue, AuditLog, Otp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed(session: Session):
    cat = Category(name="Pothole", default_priority="P2", expected_sla_days=7)
    session.add(cat)
    citizen = User(email="citizen@test.com", role="CITIZEN")
    admin = User(email="admin@authority.gov.in", role="ADMIN")
    worker_a = User(email="worker_a@authority.gov.in", role="WORKER")
    worker_b = User(email="worker_b@authority.gov.in", role="WORKER")
    for u in (citizen, admin, worker_a, worker_b):
        session.add(u)
    session.commit()
    for obj in (cat, citizen, admin, worker_a, worker_b):
        session.refresh(obj)
    return cat, citizen, admin, worker_a, worker_b


def _create_issue(session: Session, cat, reporter, status="REPORTED", worker=None):
    issue = Issue(
        category_id=cat.id,
        status=status,
        location="SRID=4326;POINT(78.35 17.44)",
        reporter_id=reporter.id,
        worker_id=worker.id if worker else None,
    )
    session.add(issue)
    session.commit()
    session.refresh(issue)
    return issue


def _login(client, session: Session, email: str):
    client.post("/api/v1/auth/otp-request", json={"email": email})
    otp = (
        session.exec(
            select(Otp).where(Otp.email == email).order_by(desc(Otp.created_at))
        )
        .first()
    )
    assert otp is not None
    resp = client.post("/api/v1/auth/login", json={"email": email, "otp": otp.code})
    assert resp.status_code == 200


def _get_audits(session: Session, entity_id=None, action=None):
    stmt = select(AuditLog)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    stmt = stmt.order_by(AuditLog.created_at.asc())
    return session.exec(stmt).all()


# ===========================================================================
# 1. ASSIGNMENT AUDITS
# ===========================================================================


class TestAssignmentAudits:
    """Audit entries for assign, reassign, unassign operations."""

    def test_assign_creates_assignment_audit(self, client, session):
        cat, citizen, admin, worker_a, _ = _seed(session)
        issue = _create_issue(session, cat, citizen)

        _login(client, session, admin.email)
        resp = client.post(
            f"/api/v1/admin/assign?issue_id={issue.id}&worker_id={worker_a.id}"
        )
        assert resp.status_code == 200

        session.expire_all()
        assignments = _get_audits(session, entity_id=issue.id, action="ASSIGNMENT")
        status_changes = _get_audits(
            session, entity_id=issue.id, action="STATUS_CHANGE"
        )

        # AdminService.assign_issue logs 1× ASSIGNMENT only, no STATUS_CHANGE
        assert len(assignments) == 1
        assert len(status_changes) == 0

        assert assignments[0].old_value == "NONE"
        assert assignments[0].new_value == str(worker_a.id)

    def test_assign_records_correct_actor(self, client, session):
        cat, citizen, admin, worker_a, _ = _seed(session)
        issue = _create_issue(session, cat, citizen)

        _login(client, session, admin.email)
        client.post(f"/api/v1/admin/assign?issue_id={issue.id}&worker_id={worker_a.id}")

        session.expire_all()
        audits = _get_audits(session, entity_id=issue.id)
        assert len(audits) >= 1
        for audit in audits:
            assert audit.actor_id == admin.id

    def test_reassign_logs_old_and_new_worker(self, client, session):
        cat, citizen, admin, worker_a, worker_b = _seed(session)
        issue = _create_issue(session, cat, citizen, status="ASSIGNED", worker=worker_a)

        _login(client, session, admin.email)
        resp = client.post(
            f"/api/v1/admin/reassign?issue_id={issue.id}&worker_id={worker_b.id}"
        )
        assert resp.status_code == 200

        session.expire_all()
        reassignments = _get_audits(session, entity_id=issue.id, action="REASSIGNMENT")
        assert len(reassignments) == 1
        assert reassignments[0].old_value == f"worker:{worker_a.id},status:ASSIGNED"
        assert reassignments[0].new_value == f"worker:{worker_b.id},status:ASSIGNED"

    def test_unassign_logs_combined_old_state(self, client, session):
        cat, citizen, admin, worker_a, _ = _seed(session)
        issue = _create_issue(session, cat, citizen, status="ASSIGNED", worker=worker_a)

        _login(client, session, admin.email)
        resp = client.post(f"/api/v1/admin/unassign?issue_id={issue.id}")
        assert resp.status_code == 200

        session.expire_all()
        unassignments = _get_audits(session, entity_id=issue.id, action="UNASSIGNMENT")
        assert len(unassignments) == 1
        old_val = unassignments[0].old_value or ""
        assert f"worker:{worker_a.id}" in old_val
        assert "status:ASSIGNED" in old_val
        assert unassignments[0].new_value == "unassigned,REPORTED"


# ===========================================================================
# 2. STATUS CHANGE AUDITS
# ===========================================================================


class TestStatusChangeAudits:
    """Audit entries for manual status change, approve, reject."""

    def test_manual_status_change_logged(self, client, session):
        cat, citizen, admin, *_ = _seed(session)
        issue = _create_issue(session, cat, citizen, status="REPORTED")

        _login(client, session, admin.email)
        resp = client.post(
            f"/api/v1/admin/update-status?issue_id={issue.id}&status=CLOSED"
        )
        assert resp.status_code == 200

        session.expire_all()
        audits = _get_audits(session, entity_id=issue.id, action="STATUS_CHANGE")
        assert len(audits) == 1
        assert audits[0].old_value == "REPORTED"
        assert audits[0].new_value == "CLOSED"

    def test_approve_logs_closed(self, client, session):
        cat, citizen, admin, worker_a, _ = _seed(session)
        issue = _create_issue(session, cat, citizen, status="RESOLVED", worker=worker_a)

        _login(client, session, admin.email)
        resp = client.post(f"/api/v1/admin/approve?issue_id={issue.id}")
        assert resp.status_code == 200

        session.expire_all()
        audits = _get_audits(session, entity_id=issue.id, action="STATUS_CHANGE")
        assert len(audits) == 1
        assert audits[0].old_value == "RESOLVED"
        assert audits[0].new_value == "CLOSED"

    def test_reject_logs_in_progress(self, client, session):
        cat, citizen, admin, worker_a, _ = _seed(session)
        issue = _create_issue(session, cat, citizen, status="RESOLVED", worker=worker_a)
        issue.resolved_at = datetime.utcnow()
        session.add(issue)
        session.commit()

        _login(client, session, admin.email)
        resp = client.post(f"/api/v1/admin/reject?issue_id={issue.id}&reason=Bad photo")
        assert resp.status_code == 200

        session.expire_all()
        audits = _get_audits(session, entity_id=issue.id, action="STATUS_CHANGE")
        assert len(audits) == 1
        assert audits[0].old_value == "RESOLVED"
        assert audits[0].new_value == "IN_PROGRESS"


# ===========================================================================
# 3. WORKER AUDITS
# ===========================================================================


class TestWorkerAudits:
    """Audit entries for worker accept, start, resolve."""

    def test_accept_logs_assigned_to_accepted(self, client, session):
        cat, citizen, _, worker_a, _ = _seed(session)
        issue = _create_issue(session, cat, citizen, status="ASSIGNED", worker=worker_a)

        _login(client, session, worker_a.email)
        eta = (datetime.utcnow() + timedelta(hours=4)).isoformat() + "Z"
        resp = client.post(f"/api/v1/worker/tasks/{issue.id}/accept?eta_date={eta}")
        assert resp.status_code == 200

        session.expire_all()
        audits = _get_audits(session, entity_id=issue.id, action="STATUS_CHANGE")
        assert len(audits) == 1
        assert audits[0].old_value == "ASSIGNED"
        assert audits[0].new_value == "ACCEPTED"
        assert audits[0].actor_id == worker_a.id

    def test_start_logs_to_in_progress(self, client, session):
        cat, citizen, _, worker_a, _ = _seed(session)
        issue = _create_issue(session, cat, citizen, status="ACCEPTED", worker=worker_a)
        issue.accepted_at = datetime.utcnow()
        session.add(issue)
        session.commit()

        _login(client, session, worker_a.email)
        resp = client.post(f"/api/v1/worker/tasks/{issue.id}/start")
        assert resp.status_code == 200

        session.expire_all()
        audits = _get_audits(session, entity_id=issue.id, action="STATUS_CHANGE")
        assert len(audits) == 1
        assert audits[0].old_value == "ACCEPTED"
        assert audits[0].new_value == "IN_PROGRESS"
        assert audits[0].actor_id == worker_a.id

    def test_resolve_logs_to_resolved(self, client, session):
        cat, citizen, _, worker_a, _ = _seed(session)
        issue = _create_issue(
            session, cat, citizen, status="IN_PROGRESS", worker=worker_a
        )

        _login(client, session, worker_a.email)

        from PIL import Image
        import io

        img = Image.new("RGB", (100, 100), color=(0, 128, 0))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")

        resp = client.post(
            f"/api/v1/worker/tasks/{issue.id}/resolve",
            files={"photo": ("after.jpg", buf.getvalue(), "image/jpeg")},
        )
        assert resp.status_code == 200

        session.expire_all()
        audits = _get_audits(session, entity_id=issue.id, action="STATUS_CHANGE")
        assert len(audits) == 1
        assert audits[0].old_value == "IN_PROGRESS"
        assert audits[0].new_value == "RESOLVED"
        assert audits[0].actor_id == worker_a.id


# ===========================================================================
# 4. PRIORITY AUDITS
# ===========================================================================


class TestPriorityAudits:
    def test_priority_change_logged(self, client, session):
        cat, citizen, admin, *_ = _seed(session)
        issue = _create_issue(session, cat, citizen)

        _login(client, session, admin.email)
        resp = client.post(
            f"/api/v1/admin/update-priority?issue_id={issue.id}&priority=P1"
        )
        assert resp.status_code == 200

        session.expire_all()
        audits = _get_audits(session, entity_id=issue.id, action="PRIORITY_CHANGE")
        assert len(audits) == 1
        assert audits[0].new_value == "P1"

    def test_priority_change_actor_is_admin(self, client, session):
        cat, citizen, admin, *_ = _seed(session)
        issue = _create_issue(session, cat, citizen)

        _login(client, session, admin.email)
        client.post(f"/api/v1/admin/update-priority?issue_id={issue.id}&priority=P2")

        session.expire_all()
        audits = _get_audits(session, entity_id=issue.id, action="PRIORITY_CHANGE")
        assert len(audits) == 1
        assert audits[0].actor_id == admin.id


# ===========================================================================
# 5. AUDIT ENDPOINT
# ===========================================================================


class TestAuditEndpoint:
    """GET /api/v1/analytics/audit/{entity_id}"""

    def test_audit_endpoint_returns_all_entries(self, client, session):
        cat, citizen, admin, worker_a, _ = _seed(session)
        issue = _create_issue(session, cat, citizen)

        _login(client, session, admin.email)
        client.post(f"/api/v1/admin/assign?issue_id={issue.id}&worker_id={worker_a.id}")

        _login(client, session, worker_a.email)
        eta = (datetime.utcnow() + timedelta(hours=4)).isoformat() + "Z"
        client.post(f"/api/v1/worker/tasks/{issue.id}/accept?eta_date={eta}")

        client.post(f"/api/v1/worker/tasks/{issue.id}/start")

        resp = client.get(f"/api/v1/analytics/audit/{issue.id}")
        assert resp.status_code == 200
        data = resp.json()
        # assign → 1 ASSIGNMENT, accept → 1 STATUS_CHANGE, start → 1 STATUS_CHANGE = 3
        assert len(data) >= 3

    def test_audit_endpoint_ordered_chronologically(self, client, session):
        cat, citizen, admin, worker_a, _ = _seed(session)
        issue = _create_issue(session, cat, citizen)

        _login(client, session, admin.email)
        client.post(f"/api/v1/admin/assign?issue_id={issue.id}&worker_id={worker_a.id}")

        _login(client, session, worker_a.email)
        eta = (datetime.utcnow() + timedelta(hours=4)).isoformat() + "Z"
        client.post(f"/api/v1/worker/tasks/{issue.id}/accept?eta_date={eta}")

        resp = client.get(f"/api/v1/analytics/audit/{issue.id}")
        data = resp.json()

        for i in range(1, len(data)):
            assert data[i]["created_at"] >= data[i - 1]["created_at"]

    def test_audit_endpoint_empty_for_fresh_issue(self, client, session):
        cat, citizen, *_ = _seed(session)
        issue = _create_issue(session, cat, citizen)

        resp = client.get(f"/api/v1/analytics/audit/{issue.id}")
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_audit_endpoint_nonexistent_entity(self, client, session):
        _seed(session)
        fake_id = uuid4()
        resp = client.get(f"/api/v1/analytics/audit/{fake_id}")
        assert resp.status_code == 200
        assert len(resp.json()) == 0


# ===========================================================================
# 6. GOLDEN PATH AUDIT TRAIL
# ===========================================================================


class TestGoldenPathAuditTrail:
    """Full lifecycle audit trail verification."""

    def test_full_lifecycle_produces_complete_audit_trail(self, client, session):
        cat, citizen, admin, worker_a, _ = _seed(session)
        issue = _create_issue(session, cat, citizen)

        _login(client, session, admin.email)
        client.post(f"/api/v1/admin/assign?issue_id={issue.id}&worker_id={worker_a.id}")

        _login(client, session, worker_a.email)
        eta = (datetime.utcnow() + timedelta(hours=4)).isoformat() + "Z"
        client.post(f"/api/v1/worker/tasks/{issue.id}/accept?eta_date={eta}")

        client.post(f"/api/v1/worker/tasks/{issue.id}/start")

        from PIL import Image
        import io

        img = Image.new("RGB", (100, 100), color=(0, 128, 0))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")

        client.post(
            f"/api/v1/worker/tasks/{issue.id}/resolve",
            files={"photo": ("after.jpg", buf.getvalue(), "image/jpeg")},
        )

        _login(client, session, admin.email)
        client.post(f"/api/v1/admin/approve?issue_id={issue.id}")

        session.expire_all()
        all_audits = _get_audits(session, entity_id=issue.id)

        # 1 ASSIGNMENT + 4 STATUS_CHANGE (accept, start, resolve, approve) = 5
        assert len(all_audits) >= 5

        status_changes = [a for a in all_audits if a.action == "STATUS_CHANGE"]
        assignments = [a for a in all_audits if a.action == "ASSIGNMENT"]

        assert len(assignments) >= 1
        assert len(status_changes) >= 4

        new_values = [sc.new_value for sc in status_changes]
        assert "ACCEPTED" in new_values
        assert "IN_PROGRESS" in new_values
        assert "RESOLVED" in new_values
        assert "CLOSED" in new_values

        for audit in all_audits:
            assert audit.entity_type == "ISSUE"
            assert audit.entity_id == issue.id
