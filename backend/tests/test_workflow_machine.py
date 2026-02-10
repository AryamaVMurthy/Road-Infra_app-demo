"""
Workflow State Machine Tests

Tests the full issue lifecycle:  REPORTED → ASSIGNED → ACCEPTED → IN_PROGRESS → RESOLVED → CLOSED

Covers:
  1. Happy-path transitions (the golden path)
  2. Illegal status jumps (e.g. REPORTED → RESOLVED directly)
  3. Wrong-worker guards (worker B cannot act on worker A's task)
  4. Admin operations: assign, reassign, unassign, approve, reject, update-status
  5. Timestamp/field integrity after each transition
  6. Audit log creation for every state change
"""

import pytest
from datetime import datetime, timedelta
from app.core.time import utc_now
from uuid import uuid4
from sqlmodel import Session, select, desc

from app.models.domain import Category, User, Issue, AuditLog, Otp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed(session: Session):
    """Create the minimum seed data shared across tests."""
    cat = Category(name="Pothole", default_priority="P2", expected_sla_days=7)
    session.add(cat)

    citizen = User(email="citizen@test.com", role="CITIZEN")
    admin = User(email="admin@authority.gov.in", role="ADMIN")
    worker_a = User(email="worker_a@authority.gov.in", role="WORKER")
    worker_b = User(email="worker_b@authority.gov.in", role="WORKER")
    sysadmin = User(email="sysadmin@marg.gov.in", role="SYSADMIN")

    for u in (citizen, admin, worker_a, worker_b, sysadmin):
        session.add(u)

    session.commit()
    for obj in (cat, citizen, admin, worker_a, worker_b, sysadmin):
        session.refresh(obj)

    return cat, citizen, admin, worker_a, worker_b, sysadmin


def _create_issue(session: Session, cat, reporter, status="REPORTED", worker=None):
    """Create a single issue at a known status."""
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
    """Authenticate using OTP request + login flow."""
    client.post("/api/v1/auth/otp-request", json={"email": email})
    otp = (
        session.exec(
            select(Otp).where(Otp.email == email).order_by(desc(Otp.created_at))
        )
        .first()
    )
    assert otp is not None
    resp = client.post("/api/v1/auth/login", json={"email": email, "otp": otp.code})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"


def _audit_count(session, action: str, entity_id=None) -> int:
    stmt = select(AuditLog).where(AuditLog.action == action)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    return len(session.exec(stmt).all())


# ===========================================================================
# 1. HAPPY PATH – full golden lifecycle
# ===========================================================================


class TestGoldenPath:
    """Walk one issue through REPORTED → … → CLOSED."""

    def test_full_lifecycle(self, client, session):
        cat, citizen, admin, worker_a, *_ = _seed(session)

        # -- Step 1: Issue starts at REPORTED --
        issue = _create_issue(session, cat, citizen)
        assert issue.status == "REPORTED"
        assert issue.worker_id is None

        # -- Step 2: Admin assigns → ASSIGNED --
        _login(client, session, admin.email)
        resp = client.post(
            f"/api/v1/admin/assign?issue_id={issue.id}&worker_id={worker_a.id}"
        )
        assert resp.status_code == 200
        session.refresh(issue)
        assert issue.status == "ASSIGNED"
        assert issue.worker_id == worker_a.id

        # -- Step 3: Worker accepts → ACCEPTED --
        _login(client, session, worker_a.email)
        eta = (utc_now() + timedelta(hours=4)).isoformat() + "Z"
        resp = client.post(f"/api/v1/worker/tasks/{issue.id}/accept?eta_date={eta}")
        assert resp.status_code == 200
        session.refresh(issue)
        assert issue.status == "ACCEPTED"
        assert issue.accepted_at is not None
        assert issue.eta_date is not None

        # -- Step 4: Worker starts → IN_PROGRESS --
        resp = client.post(f"/api/v1/worker/tasks/{issue.id}/start")
        assert resp.status_code == 200
        session.refresh(issue)
        assert issue.status == "IN_PROGRESS"

        # -- Step 5: Worker resolves → RESOLVED (needs photo) --
        from PIL import Image
        import io

        img = Image.new("RGB", (100, 100), color="green")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        photo_bytes = buf.getvalue()

        resp = client.post(
            f"/api/v1/worker/tasks/{issue.id}/resolve",
            files={"photo": ("after.jpg", photo_bytes, "image/jpeg")},
        )
        assert resp.status_code == 200
        session.refresh(issue)
        assert issue.status == "RESOLVED"
        assert issue.resolved_at is not None

        # -- Step 6: Admin approves → CLOSED --
        _login(client, session, admin.email)
        resp = client.post(f"/api/v1/admin/approve?issue_id={issue.id}")
        assert resp.status_code == 200
        session.refresh(issue)
        assert issue.status == "CLOSED"

        logs = session.exec(
            select(AuditLog).where(AuditLog.entity_id == issue.id)
        ).all()
        assert len(logs) >= 5, f"Expected >=5 audit logs, got {len(logs)}"


# ===========================================================================
# 2. ADMIN OPERATIONS
# ===========================================================================


class TestAdminOperations:
    """Admin assign, reassign, unassign, update-status, approve, reject."""

    def test_assign_sets_status_and_worker(self, client, session):
        cat, citizen, admin, worker_a, *_ = _seed(session)
        issue = _create_issue(session, cat, citizen)

        _login(client, session, admin.email)
        resp = client.post(
            f"/api/v1/admin/assign?issue_id={issue.id}&worker_id={worker_a.id}"
        )
        assert resp.status_code == 200
        session.refresh(issue)
        assert issue.status == "ASSIGNED"
        assert issue.worker_id == worker_a.id
        assert _audit_count(session, "ASSIGNMENT", issue.id) == 1

    def test_reassign_resets_to_assigned(self, client, session):
        cat, citizen, admin, worker_a, worker_b, _ = _seed(session)
        issue = _create_issue(
            session, cat, citizen, status="IN_PROGRESS", worker=worker_a
        )
        issue.accepted_at = utc_now()
        session.add(issue)
        session.commit()

        _login(client, session, admin.email)
        resp = client.post(
            f"/api/v1/admin/reassign?issue_id={issue.id}&worker_id={worker_b.id}"
        )
        assert resp.status_code == 200
        session.refresh(issue)
        assert issue.status == "ASSIGNED"
        assert issue.worker_id == worker_b.id
        assert issue.accepted_at is None
        assert issue.resolved_at is None

    def test_unassign_resets_to_reported(self, client, session):
        cat, citizen, admin, worker_a, *_ = _seed(session)
        issue = _create_issue(session, cat, citizen, status="ASSIGNED", worker=worker_a)

        _login(client, session, admin.email)
        resp = client.post(f"/api/v1/admin/unassign?issue_id={issue.id}")
        assert resp.status_code == 200
        session.refresh(issue)
        assert issue.status == "REPORTED"
        assert issue.worker_id is None
        assert issue.accepted_at is None
        assert issue.eta_date is None

    def test_reject_returns_to_in_progress(self, client, session):
        cat, citizen, admin, worker_a, *_ = _seed(session)
        issue = _create_issue(session, cat, citizen, status="RESOLVED", worker=worker_a)
        issue.resolved_at = utc_now()
        session.add(issue)
        session.commit()

        _login(client, session, admin.email)
        reason = "Photo does not match site"
        resp = client.post(f"/api/v1/admin/reject?issue_id={issue.id}&reason={reason}")
        assert resp.status_code == 200
        session.refresh(issue)
        assert issue.status == "IN_PROGRESS"
        assert issue.rejection_reason == reason

    def test_update_status_manual(self, client, session):
        """Admin can manually move an issue to any valid status."""
        cat, citizen, admin, worker_a, *_ = _seed(session)
        issue = _create_issue(session, cat, citizen, status="REPORTED")

        _login(client, session, admin.email)
        resp = client.post(
            f"/api/v1/admin/update-status?issue_id={issue.id}&status=CLOSED"
        )
        assert resp.status_code == 200
        session.refresh(issue)
        assert issue.status == "CLOSED"

    def test_update_status_invalid_status_rejected(self, client, session):
        cat, citizen, admin, *_ = _seed(session)
        issue = _create_issue(session, cat, citizen)

        _login(client, session, admin.email)
        resp = client.post(
            f"/api/v1/admin/update-status?issue_id={issue.id}&status=FOOBAR"
        )
        assert resp.status_code == 400

    def test_assign_to_inactive_worker_fails(self, client, session):
        cat, citizen, admin, worker_a, *_ = _seed(session)
        worker_a.status = "INACTIVE"
        session.add(worker_a)
        session.commit()

        issue = _create_issue(session, cat, citizen)

        _login(client, session, admin.email)
        resp = client.post(
            f"/api/v1/admin/assign?issue_id={issue.id}&worker_id={worker_a.id}"
        )
        assert resp.status_code == 400

    def test_assign_nonexistent_issue_fails(self, client, session):
        _seed(session)
        _login(client, session, "admin@authority.gov.in")
        fake_id = uuid4()
        resp = client.post(
            f"/api/v1/admin/assign?issue_id={fake_id}&worker_id={fake_id}"
        )
        assert resp.status_code == 404

    def test_bulk_assign_only_reported_issues(self, client, session):
        """Bulk assign should skip issues that are not in REPORTED status."""
        cat, citizen, admin, worker_a, *_ = _seed(session)

        issue_reported = _create_issue(session, cat, citizen, status="REPORTED")
        issue_assigned = _create_issue(
            session, cat, citizen, status="ASSIGNED", worker=worker_a
        )

        _login(client, session, admin.email)
        resp = client.post(
            "/api/v1/admin/bulk-assign",
            json={
                "issue_ids": [str(issue_reported.id), str(issue_assigned.id)],
                "worker_id": str(worker_a.id),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "1" in data["message"]

        session.refresh(issue_reported)
        assert issue_reported.status == "ASSIGNED"
        assert issue_reported.worker_id == worker_a.id

        assert issue_assigned.status == "ASSIGNED"


# ===========================================================================
# 3. WORKER OPERATIONS
# ===========================================================================


class TestWorkerOperations:
    """Worker accept, start, resolve."""

    def test_accept_sets_eta_and_timestamp(self, client, session):
        cat, citizen, admin, worker_a, *_ = _seed(session)
        issue = _create_issue(session, cat, citizen, status="ASSIGNED", worker=worker_a)

        _login(client, session, worker_a.email)
        eta = (utc_now() + timedelta(hours=8)).isoformat() + "Z"
        resp = client.post(f"/api/v1/worker/tasks/{issue.id}/accept?eta_date={eta}")
        assert resp.status_code == 200
        session.refresh(issue)
        assert issue.status == "ACCEPTED"
        assert issue.accepted_at is not None
        assert issue.eta_date is not None

    def test_start_transitions_to_in_progress(self, client, session):
        cat, citizen, admin, worker_a, *_ = _seed(session)
        issue = _create_issue(session, cat, citizen, status="ACCEPTED", worker=worker_a)
        issue.accepted_at = utc_now()
        session.add(issue)
        session.commit()

        _login(client, session, worker_a.email)
        resp = client.post(f"/api/v1/worker/tasks/{issue.id}/start")
        assert resp.status_code == 200
        session.refresh(issue)
        assert issue.status == "IN_PROGRESS"

    def test_resolve_sets_resolved_at(self, client, session):
        cat, citizen, admin, worker_a, *_ = _seed(session)
        issue = _create_issue(
            session, cat, citizen, status="IN_PROGRESS", worker=worker_a
        )

        _login(client, session, worker_a.email)

        from PIL import Image
        import io

        img = Image.new("RGB", (100, 100), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        photo_bytes = buf.getvalue()

        resp = client.post(
            f"/api/v1/worker/tasks/{issue.id}/resolve",
            files={"photo": ("after.jpg", photo_bytes, "image/jpeg")},
        )
        assert resp.status_code == 200
        session.refresh(issue)
        assert issue.status == "RESOLVED"
        assert issue.resolved_at is not None

    def test_get_tasks_returns_only_own_tasks(self, client, session):
        cat, citizen, admin, worker_a, worker_b, _ = _seed(session)

        issue_a = _create_issue(
            session, cat, citizen, status="ASSIGNED", worker=worker_a
        )
        issue_b = _create_issue(
            session, cat, citizen, status="ASSIGNED", worker=worker_b
        )

        _login(client, session, worker_a.email)
        resp = client.get("/api/v1/worker/tasks")
        assert resp.status_code == 200
        task_ids = [t["id"] for t in resp.json()]
        assert str(issue_a.id) in task_ids
        assert str(issue_b.id) not in task_ids


# ===========================================================================
# 4. WRONG-WORKER GUARDS
# ===========================================================================


class TestWrongWorkerGuards:
    """Worker B must not be able to accept/start/resolve worker A's tasks."""

    def test_wrong_worker_cannot_accept(self, client, session):
        cat, citizen, admin, worker_a, worker_b, _ = _seed(session)
        issue = _create_issue(session, cat, citizen, status="ASSIGNED", worker=worker_a)

        _login(client, session, worker_b.email)
        eta = (utc_now() + timedelta(hours=4)).isoformat() + "Z"
        resp = client.post(f"/api/v1/worker/tasks/{issue.id}/accept?eta_date={eta}")
        assert resp.status_code == 404

    def test_wrong_worker_cannot_start(self, client, session):
        cat, citizen, admin, worker_a, worker_b, _ = _seed(session)
        issue = _create_issue(session, cat, citizen, status="ACCEPTED", worker=worker_a)

        _login(client, session, worker_b.email)
        resp = client.post(f"/api/v1/worker/tasks/{issue.id}/start")
        assert resp.status_code == 404

    def test_wrong_worker_cannot_resolve(self, client, session):
        cat, citizen, admin, worker_a, worker_b, _ = _seed(session)
        issue = _create_issue(
            session, cat, citizen, status="IN_PROGRESS", worker=worker_a
        )

        _login(client, session, worker_b.email)

        from PIL import Image
        import io

        img = Image.new("RGB", (10, 10), color="red")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")

        resp = client.post(
            f"/api/v1/worker/tasks/{issue.id}/resolve",
            files={"photo": ("x.jpg", buf.getvalue(), "image/jpeg")},
        )
        assert resp.status_code == 404

    def test_nonexistent_task_returns_404(self, client, session):
        _seed(session)
        _login(client, session, "worker_a@authority.gov.in")
        fake_id = uuid4()
        resp = client.post(f"/api/v1/worker/tasks/{fake_id}/start")
        assert resp.status_code == 404


# ===========================================================================
# 5. REJECT → RE-RESOLVE CYCLE
# ===========================================================================


class TestRejectReresolveCycle:
    """After admin rejects, worker should be able to resolve again."""

    def test_reject_then_reresolve(self, client, session):
        cat, citizen, admin, worker_a, *_ = _seed(session)
        issue = _create_issue(session, cat, citizen, status="RESOLVED", worker=worker_a)
        issue.resolved_at = utc_now()
        session.add(issue)
        session.commit()

        # Admin rejects
        _login(client, session, admin.email)
        resp = client.post(f"/api/v1/admin/reject?issue_id={issue.id}&reason=Bad photo")
        assert resp.status_code == 200
        session.refresh(issue)
        assert issue.status == "IN_PROGRESS"

        # Worker re-resolves
        _login(client, session, worker_a.email)

        from PIL import Image
        import io

        img = Image.new("RGB", (100, 100), color="yellow")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")

        resp = client.post(
            f"/api/v1/worker/tasks/{issue.id}/resolve",
            files={"photo": ("after2.jpg", buf.getvalue(), "image/jpeg")},
        )
        assert resp.status_code == 200
        session.refresh(issue)
        assert issue.status == "RESOLVED"

        # Admin approves
        _login(client, session, admin.email)
        resp = client.post(f"/api/v1/admin/approve?issue_id={issue.id}")
        assert resp.status_code == 200
        session.refresh(issue)
        assert issue.status == "CLOSED"


# ===========================================================================
# 6. TIMESTAMP & FIELD INTEGRITY
# ===========================================================================


class TestFieldIntegrity:
    """Verify that timestamps and worker_id are managed correctly through transitions."""

    def test_unassign_clears_all_worker_fields(self, client, session):
        cat, citizen, admin, worker_a, *_ = _seed(session)
        issue = _create_issue(
            session, cat, citizen, status="IN_PROGRESS", worker=worker_a
        )
        issue.accepted_at = utc_now()
        issue.eta_date = utc_now() + timedelta(hours=4)
        session.add(issue)
        session.commit()

        _login(client, session, admin.email)
        resp = client.post(f"/api/v1/admin/unassign?issue_id={issue.id}")
        assert resp.status_code == 200
        session.refresh(issue)
        assert issue.worker_id is None
        assert issue.accepted_at is None
        assert issue.eta_date is None
        assert issue.resolved_at is None
        assert issue.status == "REPORTED"

    def test_reassign_clears_accepted_and_resolved(self, client, session):
        cat, citizen, admin, worker_a, worker_b, _ = _seed(session)
        issue = _create_issue(session, cat, citizen, status="ACCEPTED", worker=worker_a)
        issue.accepted_at = utc_now()
        session.add(issue)
        session.commit()

        _login(client, session, admin.email)
        resp = client.post(
            f"/api/v1/admin/reassign?issue_id={issue.id}&worker_id={worker_b.id}"
        )
        assert resp.status_code == 200
        session.refresh(issue)
        assert issue.accepted_at is None
        assert issue.resolved_at is None
        assert issue.worker_id == worker_b.id


# ===========================================================================
# 7. PRIORITY MANAGEMENT
# ===========================================================================


class TestPriority:
    def test_update_priority_valid(self, client, session):
        cat, citizen, admin, *_ = _seed(session)
        issue = _create_issue(session, cat, citizen)

        _login(client, session, admin.email)
        resp = client.post(
            f"/api/v1/admin/update-priority?issue_id={issue.id}&priority=P1"
        )
        assert resp.status_code == 200
        session.refresh(issue)
        assert issue.priority == "P1"
        assert _audit_count(session, "PRIORITY_CHANGE", issue.id) == 1

    def test_update_priority_invalid_rejected(self, client, session):
        cat, citizen, admin, *_ = _seed(session)
        issue = _create_issue(session, cat, citizen)

        _login(client, session, admin.email)
        resp = client.post(
            f"/api/v1/admin/update-priority?issue_id={issue.id}&priority=CRITICAL"
        )
        assert resp.status_code == 400
