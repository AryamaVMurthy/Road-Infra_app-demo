"""
Analytics Accuracy Tests

Verifies that analytics endpoints return mathematically correct data
for known seeded state. Every assertion checks EXACT values.

Covers:
  1. Global stats (summary, category_split, status_split)
  2. Heatmap data (exclusion of CLOSED, correct coordinates)
  3. Public issues list (all issues, correct category names)
  4. Audit trail endpoint (order, empty cases)
  5. Dashboard stats (reported/in_progress/resolved counts)
  6. Workers-with-stats (sorted by workload, accurate counts)
  7. Worker analytics (breakdown, avg resolution hours, summary)
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
    """Create categories and users for analytics tests."""
    cat_pothole = Category(name="Pothole", default_priority="P2", expected_sla_days=7)
    cat_drainage = Category(name="Drainage", default_priority="P3", expected_sla_days=5)
    cat_light = Category(
        name="Street Light", default_priority="P3", expected_sla_days=3
    )
    session.add_all([cat_pothole, cat_drainage, cat_light])

    citizen = User(email="citizen@test.com", role="CITIZEN")
    admin = User(email="admin@authority.gov.in", role="ADMIN")
    worker_a = User(
        email="worker_a@authority.gov.in", role="WORKER", full_name="Worker A"
    )
    worker_b = User(
        email="worker_b@authority.gov.in", role="WORKER", full_name="Worker B"
    )
    worker_inactive = User(
        email="worker_c@authority.gov.in",
        role="WORKER",
        full_name="Worker C",
        status="INACTIVE",
    )
    for u in (citizen, admin, worker_a, worker_b, worker_inactive):
        session.add(u)

    session.commit()
    for obj in (
        cat_pothole,
        cat_drainage,
        cat_light,
        citizen,
        admin,
        worker_a,
        worker_b,
        worker_inactive,
    ):
        session.refresh(obj)

    return (
        cat_pothole,
        cat_drainage,
        cat_light,
        citizen,
        admin,
        worker_a,
        worker_b,
        worker_inactive,
    )


def _create_issue(
    session: Session, cat, reporter, status="REPORTED", worker=None, **kwargs
):
    issue = Issue(
        category_id=cat.id,
        status=status,
        location="SRID=4326;POINT(78.35 17.44)",
        reporter_id=reporter.id,
        worker_id=worker.id if worker else None,
        **kwargs,
    )
    session.add(issue)
    session.commit()
    session.refresh(issue)
    return issue


def _login(client, session: Session, email: str):
    client.post("/api/v1/auth/otp-request", json={"email": email})
    otp = session.exec(
        select(Otp).where(Otp.email == email).order_by(desc(Otp.created_at))
    ).first()
    assert otp is not None
    resp = client.post("/api/v1/auth/login", json={"email": email, "otp": otp.code})
    assert resp.status_code == 200


# ===========================================================================
# 1. GLOBAL STATS
# ===========================================================================


class TestGlobalStats:
    """GET /api/v1/analytics/stats — public endpoint."""

    def test_empty_database_returns_zero_stats(self, client, session):
        _seed(session)
        resp = client.get("/api/v1/analytics/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["reported"] == 0
        assert data["summary"]["workers"] == 2  # 2 ACTIVE workers
        assert data["summary"]["resolved"] == 0
        assert data["summary"]["compliance"] == "N/A"

    def test_exact_counts_by_status(self, client, session):
        cats = _seed(session)
        cat, _, _, citizen, _, worker_a, worker_b, _ = cats

        # 3 REPORTED
        for _ in range(3):
            _create_issue(session, cat, citizen, status="REPORTED")
        # 2 ASSIGNED
        for _ in range(2):
            _create_issue(session, cat, citizen, status="ASSIGNED", worker=worker_a)
        # 1 IN_PROGRESS
        _create_issue(session, cat, citizen, status="IN_PROGRESS", worker=worker_a)
        # 2 RESOLVED
        for _ in range(2):
            _create_issue(session, cat, citizen, status="RESOLVED", worker=worker_b)
        # 1 CLOSED
        _create_issue(session, cat, citizen, status="CLOSED", worker=worker_b)

        resp = client.get("/api/v1/analytics/stats")
        assert resp.status_code == 200
        data = resp.json()

        # summary.reported = total issue count (all statuses)
        assert data["summary"]["reported"] == 9
        # summary.workers = active WORKER users
        assert data["summary"]["workers"] == 2
        # summary.resolved = CLOSED count only
        assert data["summary"]["resolved"] == 1
        # compliance = (RESOLVED + CLOSED) / total = 3/9 = 33.3%
        assert data["summary"]["compliance"] == "33.3%"

    def test_category_split_matches_seeded_data(self, client, session):
        cat_p, cat_d, cat_l, citizen, *_ = _seed(session)

        # 3 Pothole, 2 Drainage, 1 Street Light
        for _ in range(3):
            _create_issue(session, cat_p, citizen)
        for _ in range(2):
            _create_issue(session, cat_d, citizen)
        _create_issue(session, cat_l, citizen)

        resp = client.get("/api/v1/analytics/stats")
        data = resp.json()

        cat_map = {c["name"]: c["value"] for c in data["category_split"]}
        assert cat_map["Pothole"] == 3
        assert cat_map["Drainage"] == 2
        assert cat_map["Street Light"] == 1

    def test_status_split_covers_all_statuses(self, client, session):
        cat, _, _, citizen, _, worker_a, worker_b, _ = _seed(session)

        _create_issue(session, cat, citizen, status="REPORTED")
        _create_issue(session, cat, citizen, status="ASSIGNED", worker=worker_a)
        _create_issue(session, cat, citizen, status="IN_PROGRESS", worker=worker_a)
        _create_issue(session, cat, citizen, status="RESOLVED", worker=worker_b)
        _create_issue(session, cat, citizen, status="CLOSED", worker=worker_b)

        resp = client.get("/api/v1/analytics/stats")
        data = resp.json()

        status_map = {s["name"]: s["value"] for s in data["status_split"]}
        assert status_map["REPORTED"] == 1
        assert status_map["ASSIGNED"] == 1
        assert status_map["IN_PROGRESS"] == 1
        assert status_map["RESOLVED"] == 1
        assert status_map["CLOSED"] == 1
        # ACCEPTED is not in the list
        assert "ACCEPTED" not in status_map


# ===========================================================================
# 2. HEATMAP
# ===========================================================================


class TestHeatmap:
    """GET /api/v1/analytics/heatmap — public endpoint."""

    def test_heatmap_excludes_closed_issues(self, client, session):
        cat, _, _, citizen, _, worker_a, *_ = _seed(session)

        _create_issue(session, cat, citizen, status="REPORTED")
        _create_issue(session, cat, citizen, status="IN_PROGRESS", worker=worker_a)
        _create_issue(session, cat, citizen, status="CLOSED", worker=worker_a)

        resp = client.get("/api/v1/analytics/heatmap")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_heatmap_returns_correct_coordinates(self, client, session):
        cat, _, _, citizen, *_ = _seed(session)

        # Issue at known coordinates
        _create_issue(session, cat, citizen, status="REPORTED")

        resp = client.get("/api/v1/analytics/heatmap")
        data = resp.json()
        assert len(data) == 1
        assert abs(data[0]["lat"] - 17.44) < 0.001
        assert abs(data[0]["lng"] - 78.35) < 0.001
        assert data[0]["intensity"] == 0.5

    def test_heatmap_empty_when_all_closed(self, client, session):
        cat, _, _, citizen, _, worker_a, *_ = _seed(session)

        _create_issue(session, cat, citizen, status="CLOSED", worker=worker_a)
        _create_issue(session, cat, citizen, status="CLOSED", worker=worker_a)

        resp = client.get("/api/v1/analytics/heatmap")
        data = resp.json()
        assert len(data) == 0


# ===========================================================================
# 3. PUBLIC ISSUES
# ===========================================================================


class TestPublicIssues:
    """GET /api/v1/analytics/issues-public — public endpoint."""

    def test_issues_public_returns_all_issues(self, client, session):
        cat, _, _, citizen, _, worker_a, *_ = _seed(session)

        _create_issue(session, cat, citizen, status="REPORTED")
        _create_issue(session, cat, citizen, status="ASSIGNED", worker=worker_a)
        _create_issue(session, cat, citizen, status="IN_PROGRESS", worker=worker_a)
        _create_issue(session, cat, citizen, status="RESOLVED", worker=worker_a)
        _create_issue(session, cat, citizen, status="CLOSED", worker=worker_a)

        resp = client.get("/api/v1/analytics/issues-public")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5

    def test_issues_public_includes_category_name(self, client, session):
        cat_p, cat_d, _, citizen, *_ = _seed(session)

        _create_issue(session, cat_p, citizen)
        _create_issue(session, cat_d, citizen)

        resp = client.get("/api/v1/analytics/issues-public")
        data = resp.json()
        names = {d["category_name"] for d in data}
        assert "Pothole" in names
        assert "Drainage" in names

    def test_issues_public_has_required_fields(self, client, session):
        cat, _, _, citizen, *_ = _seed(session)
        _create_issue(session, cat, citizen)

        resp = client.get("/api/v1/analytics/issues-public")
        data = resp.json()
        item = data[0]
        assert "id" in item
        assert "lat" in item
        assert "lng" in item
        assert "status" in item
        assert "category_name" in item
        assert "created_at" in item


# ===========================================================================
# 4. AUDIT ENDPOINT
# ===========================================================================


class TestAuditEndpoint:
    """GET /api/v1/analytics/audit/{entity_id} — public endpoint."""

    def test_audit_trail_returns_entries_in_order(self, client, session):
        cat, _, _, citizen, admin, worker_a, *_ = _seed(session)
        issue = _create_issue(session, cat, citizen)

        # Assign
        _login(client, session, admin.email)
        client.post(f"/api/v1/admin/assign?issue_id={issue.id}&worker_id={worker_a.id}")

        # Accept
        _login(client, session, worker_a.email)
        eta = (utc_now() + timedelta(days=1)).date().isoformat()
        client.post(f"/api/v1/worker/tasks/{issue.id}/accept?eta_date={eta}")

        resp = client.get(f"/api/v1/analytics/audit/{issue.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2

        # Verify chronological order
        for i in range(1, len(data)):
            assert data[i]["created_at"] >= data[i - 1]["created_at"]

    def test_audit_trail_empty_for_unknown_entity(self, client, session):
        _seed(session)
        fake_id = uuid4()
        resp = client.get(f"/api/v1/analytics/audit/{fake_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 0


# ===========================================================================
# 5. DASHBOARD STATS
# ===========================================================================


class TestDashboardStats:
    """GET /api/v1/admin/dashboard-stats — auth required."""

    def test_dashboard_counts_match_seeded_data(self, client, session):
        cat, _, _, citizen, admin, worker_a, worker_b, _ = _seed(session)

        # 2 REPORTED
        _create_issue(session, cat, citizen, status="REPORTED")
        _create_issue(session, cat, citizen, status="REPORTED")
        # 1 ASSIGNED, 1 IN_PROGRESS
        _create_issue(session, cat, citizen, status="ASSIGNED", worker=worker_a)
        _create_issue(session, cat, citizen, status="IN_PROGRESS", worker=worker_a)
        # 1 RESOLVED, 1 CLOSED
        _create_issue(session, cat, citizen, status="RESOLVED", worker=worker_b)
        _create_issue(session, cat, citizen, status="CLOSED", worker=worker_b)

        _login(client, session, admin.email)
        resp = client.get("/api/v1/admin/dashboard-stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["reported"] == 2
        assert data["in_progress"] == 2  # ASSIGNED + IN_PROGRESS
        assert data["resolved"] == 2  # RESOLVED + CLOSED

    def test_dashboard_in_progress_includes_accepted(self, client, session):
        cat, _, _, citizen, admin, worker_a, *_ = _seed(session)

        _create_issue(session, cat, citizen, status="ACCEPTED", worker=worker_a)
        _create_issue(session, cat, citizen, status="IN_PROGRESS", worker=worker_a)
        _create_issue(session, cat, citizen, status="ASSIGNED", worker=worker_a)

        _login(client, session, admin.email)
        resp = client.get("/api/v1/admin/dashboard-stats")
        data = resp.json()
        # ASSIGNED + ACCEPTED + IN_PROGRESS = 3
        assert data["in_progress"] == 3


# ===========================================================================
# 6. WORKERS WITH STATS
# ===========================================================================


class TestWorkersWithStats:
    """GET /api/v1/admin/workers-with-stats — auth required."""

    def test_workers_sorted_by_workload(self, client, session):
        cat, _, _, citizen, admin, worker_a, worker_b, _ = _seed(session)

        # worker_a: 3 active tasks
        for _ in range(3):
            _create_issue(session, cat, citizen, status="ASSIGNED", worker=worker_a)
        # worker_b: 1 active task
        _create_issue(session, cat, citizen, status="ASSIGNED", worker=worker_b)

        _login(client, session, admin.email)
        resp = client.get("/api/v1/admin/workers-with-stats")
        assert resp.status_code == 200
        data = resp.json()

        # Sorted by active_task_count ascending — worker_b first
        worker_emails = [w["email"] for w in data]
        assert worker_emails.index(worker_b.email) < worker_emails.index(worker_a.email)

    def test_worker_stats_counts_accurate(self, client, session):
        cat, _, _, citizen, admin, worker_a, worker_b, _ = _seed(session)

        # worker_a: 2 ASSIGNED, 1 IN_PROGRESS, 1 CLOSED
        _create_issue(session, cat, citizen, status="ASSIGNED", worker=worker_a)
        _create_issue(session, cat, citizen, status="ASSIGNED", worker=worker_a)
        _create_issue(session, cat, citizen, status="IN_PROGRESS", worker=worker_a)
        _create_issue(session, cat, citizen, status="CLOSED", worker=worker_a)

        _login(client, session, admin.email)
        resp = client.get("/api/v1/admin/workers-with-stats")
        data = resp.json()

        wa = next(w for w in data if w["email"] == worker_a.email)
        assert wa["active_task_count"] == 3  # 2 ASSIGNED + 1 IN_PROGRESS
        assert wa["total_assigned"] == 4  # all 4
        assert wa["resolved_count"] == 1  # 1 CLOSED

    def test_inactive_worker_included_in_list(self, client, session):
        """Workers-with-stats returns ALL workers (including inactive) since
        the service queries role=WORKER without filtering by status."""
        _, _, _, _, admin, _, _, worker_inactive = _seed(session)

        _login(client, session, admin.email)
        resp = client.get("/api/v1/admin/workers-with-stats")
        data = resp.json()
        emails = [w["email"] for w in data]
        assert worker_inactive.email in emails


# ===========================================================================
# 7. WORKER ANALYTICS
# ===========================================================================


class TestWorkerAnalytics:
    """GET /api/v1/admin/worker-analytics — auth required."""

    def test_worker_analytics_summary_totals(self, client, session):
        cat, _, _, citizen, admin, worker_a, worker_b, _ = _seed(session)

        # worker_a: 2 active, 1 resolved
        _create_issue(session, cat, citizen, status="ASSIGNED", worker=worker_a)
        _create_issue(session, cat, citizen, status="IN_PROGRESS", worker=worker_a)
        _create_issue(session, cat, citizen, status="RESOLVED", worker=worker_a)
        # worker_b: 1 active, 1 closed
        _create_issue(session, cat, citizen, status="ASSIGNED", worker=worker_b)
        _create_issue(session, cat, citizen, status="CLOSED", worker=worker_b)

        _login(client, session, admin.email)
        resp = client.get("/api/v1/admin/worker-analytics")
        assert resp.status_code == 200
        data = resp.json()

        summary = data["summary"]
        # total_workers = ALL workers (including inactive)
        assert summary["total_workers"] == 3
        # total_active_tasks = 2 (worker_a) + 1 (worker_b) = 3
        assert summary["total_active_tasks"] == 3
        # total_resolved = (resolved + closed) across all = 1 + 1 = 2
        assert summary["total_resolved"] == 2

    def test_worker_pending_vs_in_progress_breakdown(self, client, session):
        cat, _, _, citizen, admin, worker_a, *_ = _seed(session)

        # 2 ASSIGNED (pending), 1 ACCEPTED + 1 IN_PROGRESS (in_progress)
        _create_issue(session, cat, citizen, status="ASSIGNED", worker=worker_a)
        _create_issue(session, cat, citizen, status="ASSIGNED", worker=worker_a)
        _create_issue(session, cat, citizen, status="ACCEPTED", worker=worker_a)
        _create_issue(session, cat, citizen, status="IN_PROGRESS", worker=worker_a)

        _login(client, session, admin.email)
        resp = client.get("/api/v1/admin/worker-analytics")
        data = resp.json()

        wa = next(w for w in data["workers"] if w["email"] == worker_a.email)
        assert wa["pending_acceptance"] == 2
        assert wa["in_progress"] == 2  # ACCEPTED + IN_PROGRESS
        assert wa["active_tasks"] == 4

    def test_avg_resolution_days_computed(self, client, session):
        cat, _, _, citizen, admin, worker_a, *_ = _seed(session)

        issue = _create_issue(session, cat, citizen, status="RESOLVED", worker=worker_a)
        now = utc_now()
        issue.accepted_at = now - timedelta(days=3)
        issue.resolved_at = now
        session.add(issue)
        session.commit()

        _login(client, session, admin.email)
        resp = client.get("/api/v1/admin/worker-analytics")
        data = resp.json()

        wa = next(w for w in data["workers"] if w["email"] == worker_a.email)
        assert wa["avg_resolution_days"] is not None
        assert abs(wa["avg_resolution_days"] - 3.0) < 0.1

    def test_worker_with_no_resolved_tasks_has_null_avg(self, client, session):
        cat, _, _, citizen, admin, worker_a, *_ = _seed(session)

        # Only active tasks, nothing resolved
        _create_issue(session, cat, citizen, status="ASSIGNED", worker=worker_a)

        _login(client, session, admin.email)
        resp = client.get("/api/v1/admin/worker-analytics")
        data = resp.json()

        wa = next(w for w in data["workers"] if w["email"] == worker_a.email)
        assert wa["avg_resolution_days"] is None
