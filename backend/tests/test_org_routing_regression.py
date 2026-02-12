"""
Regression tests for the three bugs fixed in commit 5c7ba18:

1. Zone boundaries must cover realistic coordinates (not 0,0)
2. Admin /admin/issues must only return issues matching admin's org_id
3. Issues created without org_id must NOT appear in admin dashboard

These tests verify the invariants that, when violated, caused the admin
dashboard to show 0 issues despite 60+ issues in the database.
"""

from uuid import uuid4
from sqlmodel import Session, select

from app.models.domain import Category, Issue, Organization, Otp, User, Zone
from app.services.issue_service import IssueService
from conftest import login_via_otp


HYDERABAD_LAT = 17.42
HYDERABAD_LNG = 78.44


def _seed_org_with_zone(session: Session):
    zone = Zone(
        name="Central Zone",
        boundary="SRID=4326;POLYGON((78.33 17.40,78.52 17.40,78.52 17.47,78.33 17.47,78.33 17.40))",
    )
    session.add(zone)
    session.flush()

    org = Organization(name="BBMP Central", zone_id=zone.id)
    session.add(org)
    session.flush()

    return zone, org


def _seed_users(session: Session, org):
    admin = User(
        email="admin@authority.gov.in", role="ADMIN", org_id=org.id, status="ACTIVE"
    )
    citizen = User(email="citizen@test.com", role="CITIZEN", status="ACTIVE")
    session.add_all([admin, citizen])
    session.commit()
    for u in (admin, citizen):
        session.refresh(u)
    return admin, citizen


class TestAdminIssueOrgFiltering:
    """Admin /admin/issues MUST only return issues with matching org_id."""

    def test_admin_sees_only_own_org_issues(self, client, session):
        zone, org = _seed_org_with_zone(session)
        admin, citizen = _seed_users(session, org)
        cat = Category(name="Pothole", default_priority="P2", expected_sla_days=3)
        session.add(cat)
        session.commit()
        session.refresh(cat)

        own_issue = Issue(
            category_id=cat.id,
            status="REPORTED",
            location=f"SRID=4326;POINT({HYDERABAD_LNG} {HYDERABAD_LAT})",
            reporter_id=citizen.id,
            org_id=org.id,
        )
        session.add(own_issue)
        session.commit()
        session.refresh(own_issue)

        login_via_otp(client, session, admin.email)
        resp = client.get("/api/v1/admin/issues")
        assert resp.status_code == 200
        issues = resp.json()
        assert len(issues) == 1
        assert issues[0]["id"] == str(own_issue.id)

    def test_admin_does_not_see_null_org_issues(self, client, session):
        zone, org = _seed_org_with_zone(session)
        admin, citizen = _seed_users(session, org)
        cat = Category(name="Pothole", default_priority="P2", expected_sla_days=3)
        session.add(cat)
        session.commit()
        session.refresh(cat)

        orphan_issue = Issue(
            category_id=cat.id,
            status="REPORTED",
            location=f"SRID=4326;POINT({HYDERABAD_LNG} {HYDERABAD_LAT})",
            reporter_id=citizen.id,
            org_id=None,
        )
        session.add(orphan_issue)
        session.commit()

        login_via_otp(client, session, admin.email)
        resp = client.get("/api/v1/admin/issues")
        assert resp.status_code == 200
        issues = resp.json()
        assert len(issues) == 0

    def test_admin_does_not_see_other_org_issues(self, client, session):
        zone1, org1 = _seed_org_with_zone(session)
        admin, citizen = _seed_users(session, org1)

        zone2 = Zone(
            name="North Zone",
            boundary="SRID=4326;POLYGON((78.33 17.47,78.52 17.47,78.52 17.54,78.33 17.54,78.33 17.47))",
        )
        session.add(zone2)
        session.flush()
        org2 = Organization(name="BBMP North", zone_id=zone2.id)
        session.add(org2)
        session.commit()
        session.refresh(org2)

        cat = Category(name="Pothole", default_priority="P2", expected_sla_days=3)
        session.add(cat)
        session.commit()
        session.refresh(cat)

        other_org_issue = Issue(
            category_id=cat.id,
            status="REPORTED",
            location=f"SRID=4326;POINT({HYDERABAD_LNG} {HYDERABAD_LAT})",
            reporter_id=citizen.id,
            org_id=org2.id,
        )
        session.add(other_org_issue)
        session.commit()

        login_via_otp(client, session, admin.email)
        resp = client.get("/api/v1/admin/issues")
        assert resp.status_code == 200
        assert len(resp.json()) == 0


class TestZoneBoundaryRouting:
    """Issues reported inside a zone must be auto-routed to the correct org."""

    def test_hyderabad_coords_match_zone(self, client, session):
        zone, org = _seed_org_with_zone(session)
        point_wkt = f"SRID=4326;POINT({HYDERABAD_LNG} {HYDERABAD_LAT})"
        found_org_id = IssueService.find_org_for_location(session, point_wkt)
        assert found_org_id == org.id

    def test_outside_zone_returns_none(self, client, session):
        _seed_org_with_zone(session)
        point_wkt = "SRID=4326;POINT(0 0)"
        found_org_id = IssueService.find_org_for_location(session, point_wkt)
        assert found_org_id is None

    def test_all_mock_locations_inside_central_zone(self, client, session):
        zone, org = _seed_org_with_zone(session)
        locations = [
            (17.4156, 78.4347),
            (17.4189, 78.4401),
            (17.4203, 78.4289),
            (17.4267, 78.4355),
            (17.4325, 78.4073),
            (17.4356, 78.4156),
            (17.4289, 78.4012),
            (17.4412, 78.4098),
            (17.4401, 78.3489),
            (17.4456, 78.3567),
        ]
        for lat, lng in locations:
            point_wkt = f"SRID=4326;POINT({lng} {lat})"
            found = IssueService.find_org_for_location(session, point_wkt)
            assert found == org.id, f"Location ({lat}, {lng}) not inside Central Zone"


class TestSysadminSeesAllIssues:
    """SYSADMIN should see all issues regardless of org_id."""

    def test_sysadmin_sees_all_orgs(self, client, session):
        zone, org = _seed_org_with_zone(session)
        _, citizen = _seed_users(session, org)
        sysadmin = User(email="sysadmin@marg.gov.in", role="SYSADMIN", status="ACTIVE")
        session.add(sysadmin)
        session.commit()

        cat = Category(name="Pothole", default_priority="P2", expected_sla_days=3)
        session.add(cat)
        session.commit()
        session.refresh(cat)

        issue_with_org = Issue(
            category_id=cat.id,
            status="REPORTED",
            location=f"SRID=4326;POINT({HYDERABAD_LNG} {HYDERABAD_LAT})",
            reporter_id=citizen.id,
            org_id=org.id,
        )
        issue_without_org = Issue(
            category_id=cat.id,
            status="REPORTED",
            location="SRID=4326;POINT(0 0)",
            reporter_id=citizen.id,
            org_id=None,
        )
        session.add_all([issue_with_org, issue_without_org])
        session.commit()

        login_via_otp(client, session, sysadmin.email)
        resp = client.get("/api/v1/admin/issues")
        assert resp.status_code == 200
        assert len(resp.json()) == 2
