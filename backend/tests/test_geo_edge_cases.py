"""
Geo Edge Cases Tests

Tests PostGIS spatial queries, duplicate detection, coordinate handling,
and the lat/lng property accessors on the Issue model.

Covers:
  1. IssueService.build_point_wkt() format
  2. IssueService.find_duplicate_issue() — proximity threshold logic
  3. POST /api/v1/issues/report — duplicate merging via API
  4. Issue.lat / Issue.lng property accessors
  5. Heatmap coordinate accuracy
"""

import pytest
from datetime import datetime
from uuid import uuid4, UUID
from sqlmodel import Session, select

from app.models.domain import Category, User, Issue, Evidence
from app.services.issue_service import IssueService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed(session: Session):
    cat = Category(name="Pothole", default_priority="P2", expected_sla_days=7)
    session.add(cat)
    citizen = User(email="citizen@test.com", role="CITIZEN")
    admin = User(email="admin@authority.gov.in", role="ADMIN")
    for u in (citizen, admin):
        session.add(u)
    session.commit()
    for obj in (cat, citizen, admin):
        session.refresh(obj)
    return cat, citizen, admin


def _create_issue(
    session: Session,
    cat,
    reporter,
    status="REPORTED",
    lat=17.44,
    lng=78.35,
    worker=None,
):
    issue = Issue(
        category_id=cat.id,
        status=status,
        location=f"SRID=4326;POINT({lng} {lat})",
        reporter_id=reporter.id,
        worker_id=worker.id if worker else None,
    )
    session.add(issue)
    session.commit()
    session.refresh(issue)
    return issue


def _login(client, email: str):
    resp = client.post(f"/api/v1/auth/google-mock?email={email}")
    assert resp.status_code == 200


def _make_jpeg():
    from PIL import Image
    import io

    img = Image.new("RGB", (100, 100), color=(0, 128, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ===========================================================================
# 1. BUILD POINT WKT
# ===========================================================================


class TestBuildPointWkt:
    def test_point_wkt_format(self, client, session):
        """WKT format is POINT(lng lat) — longitude first."""
        wkt = IssueService.build_point_wkt(17.44, 78.35)
        assert wkt == "SRID=4326;POINT(78.35 17.44)"

    def test_negative_coordinates(self, client, session):
        """Southern/western hemisphere coordinates."""
        wkt = IssueService.build_point_wkt(-33.87, -151.21)
        assert wkt == "SRID=4326;POINT(-151.21 -33.87)"


# ===========================================================================
# 2. DUPLICATE DETECTION
# ===========================================================================


class TestDuplicateDetection:
    def test_exact_same_location_is_duplicate(self, client, session):
        cat, citizen, _ = _seed(session)
        _create_issue(session, cat, citizen, lat=17.44, lng=78.35)

        point = IssueService.build_point_wkt(17.44, 78.35)
        dup = IssueService.find_duplicate_issue(session, point)
        assert dup is not None

    def test_within_5m_is_duplicate(self, client, session):
        """3 meters away should still be detected as duplicate.
        ~3m ≈ 0.000027 degrees latitude at this latitude."""
        cat, citizen, _ = _seed(session)
        _create_issue(session, cat, citizen, lat=17.44, lng=78.35)

        offset = 0.000027  # ~3 meters
        point = IssueService.build_point_wkt(17.44 + offset, 78.35)
        dup = IssueService.find_duplicate_issue(session, point)
        assert dup is not None

    def test_outside_5m_is_not_duplicate(self, client, session):
        """10 meters away should NOT be detected.
        ~10m ≈ 0.0000899 degrees latitude."""
        cat, citizen, _ = _seed(session)
        _create_issue(session, cat, citizen, lat=17.44, lng=78.35)

        offset = 0.0001  # ~11 meters
        point = IssueService.build_point_wkt(17.44 + offset, 78.35)
        dup = IssueService.find_duplicate_issue(session, point)
        assert dup is None

    def test_closed_issue_not_detected_as_duplicate(self, client, session):
        """CLOSED issues are excluded from duplicate detection."""
        cat, citizen, _ = _seed(session)
        _create_issue(session, cat, citizen, lat=17.44, lng=78.35, status="CLOSED")

        point = IssueService.build_point_wkt(17.44, 78.35)
        dup = IssueService.find_duplicate_issue(session, point)
        assert dup is None

    def test_no_issues_returns_none(self, client, session):
        _seed(session)
        point = IssueService.build_point_wkt(17.44, 78.35)
        dup = IssueService.find_duplicate_issue(session, point)
        assert dup is None


# ===========================================================================
# 3. REPORT ENDPOINT — DUPLICATE MERGING
# ===========================================================================


class TestReportEndpointDuplicates:
    def test_report_at_same_location_increments_count(self, client, session):
        cat, citizen, _ = _seed(session)
        photo = _make_jpeg()

        # First report
        resp1 = client.post(
            "/api/v1/issues/report",
            data={
                "category_id": str(cat.id),
                "lat": "17.44",
                "lng": "78.35",
                "reporter_email": citizen.email,
            },
            files={"photo": ("test1.jpg", photo, "image/jpeg")},
        )
        assert resp1.status_code == 200
        issue_id_1 = resp1.json()["issue_id"]

        # Second report at same location
        resp2 = client.post(
            "/api/v1/issues/report",
            data={
                "category_id": str(cat.id),
                "lat": "17.44",
                "lng": "78.35",
                "reporter_email": citizen.email,
            },
            files={"photo": ("test2.jpg", photo, "image/jpeg")},
        )
        assert resp2.status_code == 200
        issue_id_2 = resp2.json()["issue_id"]

        # Same issue, incremented count
        assert issue_id_1 == issue_id_2

        session.expire_all()
        issue = session.get(Issue, UUID(issue_id_1))
        assert issue is not None
        assert issue.report_count == 2

    def test_report_far_away_creates_new_issue(self, client, session):
        cat, citizen, _ = _seed(session)
        photo = _make_jpeg()

        # Report at location A
        resp1 = client.post(
            "/api/v1/issues/report",
            data={
                "category_id": str(cat.id),
                "lat": "17.44",
                "lng": "78.35",
                "reporter_email": citizen.email,
            },
            files={"photo": ("test1.jpg", photo, "image/jpeg")},
        )
        assert resp1.status_code == 200
        id1 = resp1.json()["issue_id"]

        # Report at location B (far away)
        resp2 = client.post(
            "/api/v1/issues/report",
            data={
                "category_id": str(cat.id),
                "lat": "28.61",
                "lng": "77.21",
                "reporter_email": citizen.email,
            },
            files={"photo": ("test2.jpg", photo, "image/jpeg")},
        )
        assert resp2.status_code == 200
        id2 = resp2.json()["issue_id"]

        assert id1 != id2


# ===========================================================================
# 4. COORDINATE PROPERTIES
# ===========================================================================


class TestCoordinateProperties:
    def test_lat_lng_properties_correct(self, client, session):
        cat, citizen, _ = _seed(session)
        issue = _create_issue(session, cat, citizen, lat=17.44, lng=78.35)
        assert abs(issue.lat - 17.44) < 0.001
        assert abs(issue.lng - 78.35) < 0.001

    def test_various_coordinates(self, client, session):
        cat, citizen, _ = _seed(session)

        coords = [
            (17.385, 78.4867),  # Hyderabad
            (19.076, 72.8777),  # Mumbai
            (28.6139, 77.209),  # Delhi
        ]
        for lat, lng in coords:
            issue = _create_issue(session, cat, citizen, lat=lat, lng=lng)
            assert abs(issue.lat - lat) < 0.001, f"lat mismatch for ({lat}, {lng})"
            assert abs(issue.lng - lng) < 0.001, f"lng mismatch for ({lat}, {lng})"


# ===========================================================================
# 5. HEATMAP COORDINATES
# ===========================================================================


class TestHeatmapCoordinates:
    def test_heatmap_returns_correct_lat_lng(self, client, session):
        cat, citizen, _ = _seed(session)
        _create_issue(session, cat, citizen, lat=19.076, lng=72.8777)

        resp = client.get("/api/v1/analytics/heatmap")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert abs(data[0]["lat"] - 19.076) < 0.001
        assert abs(data[0]["lng"] - 72.8777) < 0.001
