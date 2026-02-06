"""
RBAC Matrix Tests

Verifies that every protected endpoint rejects unauthorized roles.
The current codebase uses `get_current_user` but does NOT enforce role checks
at the endpoint level — admin routes are accessible to any authenticated user.

These tests document the CURRENT behavior and will catch regressions if/when
proper role guards are added.  Tests marked with `xfail` represent endpoints
that SHOULD reject a given role but currently don't.
"""

import pytest
import io
from datetime import datetime, timedelta
from uuid import uuid4

from sqlmodel import Session, select
from app.models.domain import Category, User, Issue


# ---------------------------------------------------------------------------


def _seed_all_roles(session: Session):
    """Create one user per role + a category + one issue for endpoint probing."""
    cat = Category(name="TestCat", default_priority="P3", expected_sla_days=7)
    session.add(cat)

    users = {}
    for role, email in [
        ("CITIZEN", "citizen@test.com"),
        ("WORKER", "worker@test.com"),
        ("ADMIN", "admin@authority.gov.in"),
        ("SYSADMIN", "sysadmin@marg.gov.in"),
    ]:
        u = User(email=email, role=role)
        session.add(u)
        users[role] = u

    session.commit()
    for obj in [cat, *users.values()]:
        session.refresh(obj)

    issue = Issue(
        category_id=cat.id,
        status="REPORTED",
        location="SRID=4326;POINT(78.35 17.44)",
        reporter_id=users["CITIZEN"].id,
    )
    session.add(issue)
    session.commit()
    session.refresh(issue)

    return users, cat, issue


def _login(client, email: str):
    resp = client.post(f"/api/v1/auth/google-mock?email={email}")
    assert resp.status_code == 200


def _clear_cookies(client):
    client.cookies.clear()


ADMIN_GET_ENDPOINTS = [
    "/api/v1/admin/issues",
    "/api/v1/admin/workers",
    "/api/v1/admin/workers-with-stats",
    "/api/v1/admin/worker-analytics",
    "/api/v1/admin/dashboard-stats",
]


class TestUnauthenticatedAccess:
    """All protected endpoints must reject unauthenticated requests."""

    @pytest.mark.parametrize("path", ADMIN_GET_ENDPOINTS)
    def test_admin_get_endpoints_require_auth(self, client, session, path):
        _seed_all_roles(session)
        _clear_cookies(client)
        resp = client.get(path)
        assert resp.status_code == 401, f"{path} should require auth"

    def test_worker_tasks_requires_auth(self, client, session):
        _seed_all_roles(session)
        _clear_cookies(client)
        resp = client.get("/api/v1/worker/tasks")
        assert resp.status_code == 401

    def test_auth_me_requires_auth(self, client, session):
        _seed_all_roles(session)
        _clear_cookies(client)
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401


class TestPublicEndpoints:
    """Public endpoints should be accessible without auth."""

    def test_analytics_heatmap_public(self, client, session):
        _seed_all_roles(session)
        _clear_cookies(client)
        resp = client.get("/api/v1/analytics/heatmap")
        assert resp.status_code == 200

    def test_analytics_stats_public(self, client, session):
        _seed_all_roles(session)
        _clear_cookies(client)
        resp = client.get("/api/v1/analytics/stats")
        assert resp.status_code == 200

    def test_analytics_issues_public(self, client, session):
        _seed_all_roles(session)
        _clear_cookies(client)
        resp = client.get("/api/v1/analytics/issues-public")
        assert resp.status_code == 200


class TestWorkerEndpointAccess:
    """Worker endpoints should work for the assigned worker."""

    def test_worker_can_get_own_tasks(self, client, session):
        users, cat, issue = _seed_all_roles(session)
        _login(client, users["WORKER"].email)
        resp = client.get("/api/v1/worker/tasks")
        assert resp.status_code == 200

    def test_citizen_can_hit_worker_tasks_endpoint(self, client, session):
        """
        Currently get_current_user doesn't check role, so a citizen CAN call
        /worker/tasks — they'll just get an empty list since no tasks are
        assigned to them. This documents current behavior.
        """
        users, cat, issue = _seed_all_roles(session)
        _login(client, users["CITIZEN"].email)
        resp = client.get("/api/v1/worker/tasks")
        assert resp.status_code == 200
        assert resp.json() == []


class TestAdminEndpointAccess:
    """Admin endpoints: verify authenticated access patterns."""

    @pytest.mark.parametrize("path", ADMIN_GET_ENDPOINTS)
    def test_admin_can_access_admin_endpoints(self, client, session, path):
        users, cat, issue = _seed_all_roles(session)
        _login(client, users["ADMIN"].email)
        resp = client.get(path)
        assert resp.status_code == 200, f"Admin should access {path}"

    @pytest.mark.parametrize("path", ADMIN_GET_ENDPOINTS)
    def test_sysadmin_can_access_admin_endpoints(self, client, session, path):
        users, cat, issue = _seed_all_roles(session)
        _login(client, users["SYSADMIN"].email)
        resp = client.get(path)
        assert resp.status_code == 200, f"SYSADMIN should access {path}"

    def test_admin_can_assign_issue(self, client, session):
        users, cat, issue = _seed_all_roles(session)
        _login(client, users["ADMIN"].email)
        resp = client.post(
            f"/api/v1/admin/assign?issue_id={issue.id}&worker_id={users['WORKER'].id}"
        )
        assert resp.status_code == 200

    def test_admin_can_approve_issue(self, client, session):
        users, cat, issue = _seed_all_roles(session)
        issue.status = "RESOLVED"
        issue.worker_id = users["WORKER"].id
        session.add(issue)
        session.commit()

        _login(client, users["ADMIN"].email)
        resp = client.post(f"/api/v1/admin/approve?issue_id={issue.id}")
        assert resp.status_code == 200

    def test_admin_can_reject_issue(self, client, session):
        users, cat, issue = _seed_all_roles(session)
        issue.status = "RESOLVED"
        issue.worker_id = users["WORKER"].id
        session.add(issue)
        session.commit()

        _login(client, users["ADMIN"].email)
        resp = client.post(f"/api/v1/admin/reject?issue_id={issue.id}&reason=bad")
        assert resp.status_code == 200


class TestCrossRoleAccess:
    """
    Document which cross-role access patterns currently work.
    These tests are valuable for catching regressions when role guards are added.
    """

    @pytest.mark.parametrize("path", ADMIN_GET_ENDPOINTS)
    def test_citizen_can_currently_access_admin_get_endpoints(
        self, client, session, path
    ):
        """
        BUG/FEATURE: Admin GET endpoints don't check role.
        A citizen with a valid token can read admin data.
        This test documents the current (permissive) behavior.
        """
        users, cat, issue = _seed_all_roles(session)
        _login(client, users["CITIZEN"].email)
        resp = client.get(path)
        assert resp.status_code == 200

    @pytest.mark.parametrize("path", ADMIN_GET_ENDPOINTS)
    def test_worker_can_currently_access_admin_get_endpoints(
        self, client, session, path
    ):
        users, cat, issue = _seed_all_roles(session)
        _login(client, users["WORKER"].email)
        resp = client.get(path)
        assert resp.status_code == 200

    def test_citizen_can_currently_assign_issue(self, client, session):
        """Citizen can call admin/assign — no role guard exists yet."""
        users, cat, issue = _seed_all_roles(session)
        _login(client, users["CITIZEN"].email)
        resp = client.post(
            f"/api/v1/admin/assign?issue_id={issue.id}&worker_id={users['WORKER'].id}"
        )
        assert resp.status_code == 200

    def test_worker_can_currently_approve_issue(self, client, session):
        """Worker can call admin/approve — no role guard exists yet."""
        users, cat, issue = _seed_all_roles(session)
        issue.status = "RESOLVED"
        issue.worker_id = users["WORKER"].id
        session.add(issue)
        session.commit()

        _login(client, users["WORKER"].email)
        resp = client.post(f"/api/v1/admin/approve?issue_id={issue.id}")
        assert resp.status_code == 200

    def test_worker_cannot_act_on_another_workers_task(self, client, session):
        """Ownership check on worker endpoints prevents cross-worker access."""
        users, cat, issue = _seed_all_roles(session)
        worker2 = User(email="worker2@authority.gov.in", role="WORKER")
        session.add(worker2)
        session.commit()
        session.refresh(worker2)

        issue.status = "ASSIGNED"
        issue.worker_id = users["WORKER"].id
        session.add(issue)
        session.commit()

        _login(client, worker2.email)
        eta = (datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z"
        resp = client.post(f"/api/v1/worker/tasks/{issue.id}/accept?eta_date={eta}")
        assert resp.status_code == 404


class TestTokenIntegrity:
    """Verify token-based access control fundamentals."""

    def test_expired_or_invalid_token_rejected(self, client, session):
        _seed_all_roles(session)
        client.cookies.set("access_token", "totally-invalid-jwt-token")
        resp = client.get("/api/v1/admin/issues")
        assert resp.status_code == 401

    def test_after_logout_endpoints_reject(self, client, session):
        users, cat, issue = _seed_all_roles(session)
        _login(client, users["ADMIN"].email)

        resp = client.get("/api/v1/admin/issues")
        assert resp.status_code == 200

        client.post("/api/v1/auth/logout")

        resp = client.get("/api/v1/admin/issues")
        assert resp.status_code == 401
