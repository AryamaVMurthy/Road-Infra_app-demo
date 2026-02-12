from uuid import UUID

from sqlmodel import Session, select

from app.models.domain import Category, Issue, Organization, Otp, User, Zone
from conftest import login_via_otp


def _seed_sysadmin(session: Session):
    sysadmin = User(email="sysadmin@marg.gov.in", role="SYSADMIN", status="ACTIVE")
    session.add(sysadmin)
    session.commit()
    session.refresh(sysadmin)
    return sysadmin


def _seed_authority_admin(session: Session):
    zone = Zone(
        name="Central Zone",
        boundary="SRID=4326;POLYGON((78.30 17.30,78.60 17.30,78.60 17.60,78.30 17.60,78.30 17.30))",
    )
    session.add(zone)
    session.flush()

    organization = Organization(name="Central Authority", zone_id=zone.id)
    session.add(organization)
    session.flush()

    admin = User(
        email="admin@authority.gov.in",
        role="ADMIN",
        status="ACTIVE",
        org_id=organization.id,
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)
    session.refresh(organization)
    return admin, organization


def test_bulk_worker_onboarding_flow(client, session):
    admin, org = _seed_authority_admin(session)
    login_via_otp(client, session, admin.email)

    response = client.post(
        "/api/v1/admin/bulk-register",
        json={
            "emails_csv": "w1@authority.gov.in, w2@authority.gov.in, w1@authority.gov.in"
        },
    )
    assert response.status_code == 200

    workers = session.exec(
        select(User).where(User.role == "WORKER", User.org_id == org.id)
    ).all()
    assert len(workers) == 2

    client.cookies.clear()
    otp_response = client.post(
        "/api/v1/auth/otp-request", json={"email": "w1@authority.gov.in"}
    )
    assert otp_response.status_code == 200
    otp = session.exec(select(Otp).where(Otp.email == "w1@authority.gov.in")).first()
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "w1@authority.gov.in", "otp": otp.code},
    )
    assert login_response.status_code == 200
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "WORKER"


def test_sysadmin_authority_issue_type_and_manual_issue(client, session):
    sysadmin = _seed_sysadmin(session)
    login_via_otp(client, session, sysadmin.email)

    authority_response = client.post(
        "/api/v1/admin/authorities",
        json={
            "name": "North Authority",
            "admin_email": "north-admin@authority.gov.in",
            "zone_name": "North Zone",
            "jurisdiction_points": [
                [78.40, 17.40],
                [78.55, 17.40],
                [78.55, 17.55],
                [78.40, 17.55],
            ],
        },
    )
    assert authority_response.status_code == 200

    issue_type_response = client.post(
        "/api/v1/admin/issue-types",
        json={
            "name": "Street Sign Damage",
        },
    )
    assert issue_type_response.status_code == 200
    category_id = issue_type_response.json()["id"]

    manual_issue_response = client.post(
        "/api/v1/admin/manual-issues",
        json={
            "category_id": category_id,
            "lat": 17.45,
            "lng": 78.48,
            "address": "Ward 3 Main Road",
        },
    )
    assert manual_issue_response.status_code == 200

    issue = session.exec(
        select(Issue).where(Issue.id == UUID(manual_issue_response.json()["issue_id"]))
    ).first()
    assert issue is not None
    assert issue.reporter_id == sysadmin.id

    active_category = session.exec(
        select(Category).where(Category.id == category_id)
    ).first()
    assert active_category is not None

    deactivate_response = client.delete(f"/api/v1/admin/issue-types/{category_id}")
    assert deactivate_response.status_code == 200
    session.refresh(active_category)
    assert active_category.is_active is False
