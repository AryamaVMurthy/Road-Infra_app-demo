from sqlmodel import Session, select

from app.models.domain import Category, Issue, Organization, Otp, User, Zone


def _login(client, session: Session, email: str):
    otp_request = client.post("/api/v1/auth/otp-request", json={"email": email})
    assert otp_request.status_code == 200
    otp = session.exec(select(Otp).where(Otp.email == email)).first()
    assert otp is not None
    login = client.post("/api/v1/auth/login", json={"email": email, "otp": otp.code})
    assert login.status_code == 200


def _seed_org_scoped_analytics(session: Session):
    zone_a = Zone(
        name="Zone A",
        boundary="SRID=4326;POLYGON((78.30 17.38,78.40 17.38,78.40 17.48,78.30 17.48,78.30 17.38))",
    )
    zone_b = Zone(
        name="Zone B",
        boundary="SRID=4326;POLYGON((78.50 17.58,78.60 17.58,78.60 17.68,78.50 17.68,78.50 17.58))",
    )
    session.add(zone_a)
    session.add(zone_b)
    session.flush()

    org_a = Organization(name="Authority A", zone_id=zone_a.id)
    org_b = Organization(name="Authority B", zone_id=zone_b.id)
    session.add(org_a)
    session.add(org_b)
    session.flush()

    category = Category(name="Pothole", default_priority="P2")
    reporter = User(email="citizen@test.com", role="CITIZEN")
    admin_a = User(email="admin-a@authority.gov.in", role="ADMIN", org_id=org_a.id)
    admin_b = User(email="admin-b@authority.gov.in", role="ADMIN", org_id=org_b.id)
    sysadmin = User(email="sysadmin@marg.gov.in", role="SYSADMIN")
    session.add(category)
    session.add(reporter)
    session.add(admin_a)
    session.add(admin_b)
    session.add(sysadmin)
    session.commit()
    session.refresh(category)
    session.refresh(reporter)
    session.refresh(admin_a)
    session.refresh(admin_b)
    session.refresh(sysadmin)

    issue_a = Issue(
        category_id=category.id,
        status="REPORTED",
        location="SRID=4326;POINT(78.35 17.44)",
        reporter_id=reporter.id,
        org_id=org_a.id,
    )
    issue_b = Issue(
        category_id=category.id,
        status="REPORTED",
        location="SRID=4326;POINT(78.55 17.64)",
        reporter_id=reporter.id,
        org_id=org_b.id,
    )
    session.add(issue_a)
    session.add(issue_b)
    session.commit()
    session.refresh(issue_a)
    session.refresh(issue_b)

    return admin_a, admin_b, sysadmin, issue_a, issue_b


def test_admin_scoped_heatmap_excludes_other_authorities(client, session):
    admin_a, _, _, issue_a, issue_b = _seed_org_scoped_analytics(session)
    _login(client, session, admin_a.email)

    response = client.get("/api/v1/admin/heatmap")

    assert response.status_code == 200
    body = response.json()
    assert body == [
        {"lat": issue_a.lat, "lng": issue_a.lng, "intensity": 0.5}
    ]
    assert {"lat": issue_b.lat, "lng": issue_b.lng, "intensity": 0.5} not in body


def test_admin_scoped_issue_map_excludes_other_authorities(client, session):
    admin_a, _, _, issue_a, issue_b = _seed_org_scoped_analytics(session)
    _login(client, session, admin_a.email)

    response = client.get("/api/v1/admin/issues-map")

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [str(issue_a.id)]
    assert str(issue_b.id) not in [item["id"] for item in body]


def test_sysadmin_scoped_analytics_stays_global(client, session):
    _, _, sysadmin, issue_a, issue_b = _seed_org_scoped_analytics(session)
    _login(client, session, sysadmin.email)

    stats_response = client.get("/api/v1/admin/stats")
    issues_response = client.get("/api/v1/admin/issues-map")

    assert stats_response.status_code == 200
    assert issues_response.status_code == 200
    assert stats_response.json()["summary"]["reported"] == 2
    assert {item["id"] for item in issues_response.json()} == {
        str(issue_a.id),
        str(issue_b.id),
    }
