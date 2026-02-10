import io
from datetime import datetime, timedelta
from app.core.time import utc_now
from uuid import UUID

import pytest
from PIL import Image
from sqlmodel import Session

from app.models.domain import Category, Issue, User
from conftest import login_via_otp


def _seed_all_roles(session: Session):
    category = Category(name="TestCat", default_priority="P3", expected_sla_days=7)
    session.add(category)

    users = {}
    for role, email in [
        ("CITIZEN", "citizen@test.com"),
        ("WORKER", "worker@test.com"),
        ("ADMIN", "admin@authority.gov.in"),
        ("SYSADMIN", "sysadmin@marg.gov.in"),
    ]:
        user = User(email=email, role=role)
        session.add(user)
        users[role] = user

    session.commit()
    for obj in [category, *users.values()]:
        session.refresh(obj)

    issue = Issue(
        category_id=category.id,
        status="REPORTED",
        location="SRID=4326;POINT(78.35 17.44)",
        reporter_id=users["CITIZEN"].id,
    )
    session.add(issue)
    session.commit()
    session.refresh(issue)

    return users, category, issue


def _make_jpeg():
    image = Image.new("RGB", (100, 100), color=(255, 0, 0))
    buf = io.BytesIO()
    image.save(buf, format="JPEG")
    return buf.getvalue()


ADMIN_ENDPOINTS = [
    "/api/v1/admin/issues",
    "/api/v1/admin/workers",
    "/api/v1/admin/workers-with-stats",
    "/api/v1/admin/worker-analytics",
    "/api/v1/admin/dashboard-stats",
    "/api/v1/analytics/audit-all",
]


class TestUnauthenticatedAccess:
    @pytest.mark.parametrize("path", ADMIN_ENDPOINTS)
    def test_admin_endpoints_require_auth(self, client, session, path):
        _seed_all_roles(session)
        client.cookies.clear()
        response = client.get(path)
        assert response.status_code == 401

    def test_worker_tasks_require_auth(self, client, session):
        _seed_all_roles(session)
        client.cookies.clear()
        response = client.get("/api/v1/worker/tasks")
        assert response.status_code == 401


class TestPublicEndpoints:
    def test_public_analytics_remain_public(self, client, session):
        _seed_all_roles(session)
        assert client.get("/api/v1/analytics/heatmap").status_code == 200
        assert client.get("/api/v1/analytics/stats").status_code == 200
        assert client.get("/api/v1/analytics/issues-public").status_code == 200


class TestAdminRBAC:
    @pytest.mark.parametrize("path", ADMIN_ENDPOINTS)
    def test_admin_can_access(self, client, session, path):
        users, *_ = _seed_all_roles(session)
        login_via_otp(client, session, users["ADMIN"].email)
        response = client.get(path)
        assert response.status_code == 200

    @pytest.mark.parametrize("path", ADMIN_ENDPOINTS)
    def test_sysadmin_can_access(self, client, session, path):
        users, *_ = _seed_all_roles(session)
        login_via_otp(client, session, users["SYSADMIN"].email)
        response = client.get(path)
        assert response.status_code == 200

    @pytest.mark.parametrize("path", ADMIN_ENDPOINTS)
    def test_citizen_forbidden(self, client, session, path):
        users, *_ = _seed_all_roles(session)
        login_via_otp(client, session, users["CITIZEN"].email)
        response = client.get(path)
        assert response.status_code == 403

    @pytest.mark.parametrize("path", ADMIN_ENDPOINTS)
    def test_worker_forbidden(self, client, session, path):
        users, *_ = _seed_all_roles(session)
        login_via_otp(client, session, users["WORKER"].email)
        response = client.get(path)
        assert response.status_code == 403


class TestWorkerRBAC:
    def test_worker_can_access_own_tasks(self, client, session):
        users, _, issue = _seed_all_roles(session)
        issue.status = "ASSIGNED"
        issue.worker_id = users["WORKER"].id
        session.add(issue)
        session.commit()

        login_via_otp(client, session, users["WORKER"].email)
        response = client.get("/api/v1/worker/tasks")
        assert response.status_code == 200
        assert len(response.json()) == 1

    @pytest.mark.parametrize("role", ["CITIZEN", "ADMIN", "SYSADMIN"])
    def test_non_worker_forbidden_from_worker_routes(self, client, session, role):
        users, _, issue = _seed_all_roles(session)
        issue.status = "ASSIGNED"
        issue.worker_id = users["WORKER"].id
        session.add(issue)
        session.commit()

        login_via_otp(client, session, users[role].email)
        eta = (utc_now() + timedelta(hours=2)).isoformat() + "Z"
        response = client.post(f"/api/v1/worker/tasks/{issue.id}/accept?eta_date={eta}")
        assert response.status_code == 403

    def test_worker_cannot_access_other_workers_task(self, client, session):
        users, _, issue = _seed_all_roles(session)
        worker2 = User(email="worker2@authority.gov.in", role="WORKER")
        session.add(worker2)
        session.commit()
        session.refresh(worker2)

        issue.status = "ASSIGNED"
        issue.worker_id = users["WORKER"].id
        session.add(issue)
        session.commit()

        login_via_otp(client, session, worker2.email)
        eta = (utc_now() + timedelta(hours=2)).isoformat() + "Z"
        response = client.post(f"/api/v1/worker/tasks/{issue.id}/accept?eta_date={eta}")
        assert response.status_code == 404


class TestCitizenIssueOwnership:
    def test_report_endpoint_uses_authenticated_identity(self, client, session):
        users, category, _ = _seed_all_roles(session)
        login_via_otp(client, session, users["CITIZEN"].email)

        response = client.post(
            "/api/v1/issues/report",
            data={
                "category_id": str(category.id),
                "lat": "17.44",
                "lng": "78.35",
                "address": "Main Road",
            },
            files={"photo": ("test.jpg", _make_jpeg(), "image/jpeg")},
        )
        assert response.status_code == 200

        issue = session.get(Issue, UUID(response.json()["issue_id"]))
        assert issue is not None
        assert issue.reporter_id == users["CITIZEN"].id

    def test_my_reports_does_not_accept_email_override(self, client, session):
        users, category, _ = _seed_all_roles(session)

        issue = Issue(
            category_id=category.id,
            status="REPORTED",
            location="SRID=4326;POINT(78.35 17.44)",
            reporter_id=users["CITIZEN"].id,
        )
        session.add(issue)
        session.commit()

        login_via_otp(client, session, users["WORKER"].email)
        response = client.get("/api/v1/issues/my-reports")
        assert response.status_code == 403
