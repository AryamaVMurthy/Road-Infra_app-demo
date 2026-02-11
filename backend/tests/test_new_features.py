import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.models.domain import User, Invite, Organization, Zone, Category, Issue
from app.services.issue_service import IssueService
from tests.conftest import login_via_otp
from uuid import uuid4


def test_worker_bulk_onboarding(client: TestClient, session: Session):
    # Setup: Create an Admin
    zone = Zone(
        name="Test Zone", boundary="SRID=4326;POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))"
    )
    session.add(zone)
    session.commit()
    session.refresh(zone)

    org = Organization(name="Test Org", zone_id=zone.id)
    session.add(org)
    session.commit()
    session.refresh(org)

    admin_email = "admin@test.gov.in"
    admin = User(email=admin_email, role="ADMIN", org_id=org.id)
    session.add(admin)
    session.commit()

    login_via_otp(client, session, admin_email)

    # Action: Bulk invite workers
    worker_emails = ["w1@test.com", "w2@test.com", "w3@test.com"]
    response = client.post("/api/v1/admin/bulk-invite", json={"emails": worker_emails})
    assert response.status_code == 200

    # Verify invites created
    invites = session.exec(select(Invite)).all()
    assert len(invites) == 3
    for inv in invites:
        assert inv.email in worker_emails
        assert inv.org_id == org.id
        assert inv.status == "INVITED"

    # Action: Worker logs in
    worker_email = "w1@test.com"
    login_via_otp(client, session, worker_email)

    # Verify worker user created and assigned to org
    worker = session.exec(select(User).where(User.email == worker_email)).first()
    assert worker is not None
    assert worker.role == "WORKER"
    assert worker.org_id == org.id

    # Verify invite status updated
    invite = session.exec(select(Invite).where(Invite.email == worker_email)).first()
    assert invite.status == "ACCEPTED"


def test_sysadmin_zone_and_org_creation(client: TestClient, session: Session):
    sysadmin_email = "sysadmin@marg.gov.in"
    sysadmin = User(email=sysadmin_email, role="SYSADMIN")
    session.add(sysadmin)
    session.commit()

    login_via_otp(client, session, sysadmin_email)

    auth_data = {
        "name": "New Authority",
        "admin_email": "admin@newauthority.gov.in",
        "jurisdiction_points": [
            [77.5, 12.9],
            [77.6, 12.9],
            [77.6, 13.0],
            [77.5, 13.0],
            [77.5, 12.9],
        ],
        "zone_name": "New City Zone",
    }
    response = client.post("/api/v1/admin/authorities", json=auth_data)
    assert response.status_code == 200
    assert response.json()["name"] == "New Authority"
    assert response.json()["zone_name"] == "New City Zone"


def test_issue_type_crud(client: TestClient, session: Session):
    sysadmin_email = "sysadmin@marg.gov.in"
    sysadmin = User(email=sysadmin_email, role="SYSADMIN")
    session.add(sysadmin)
    session.commit()

    login_via_otp(client, session, sysadmin_email)

    # Create
    cat_data = {
        "name": "New Issue Type",
        "default_priority": "P2",
        "expected_sla_days": 5,
    }
    response = client.post("/api/v1/admin/issue-types", json=cat_data)
    assert response.status_code == 200
    cat_id = response.json()["id"]

    # Update
    update_data = {
        "expected_sla_days": 3,
        "name": "New Issue Type",
        "default_priority": "P2",
    }
    response = client.put(f"/api/v1/admin/issue-types/{cat_id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["expected_sla_days"] == 3

    # Delete (Deactivate)
    response = client.delete(f"/api/v1/admin/issue-types/{cat_id}")
    assert response.status_code == 200

    cat = session.get(Category, cat_id)
    assert cat.is_active is False


def test_intelligent_issue_routing(client: TestClient, session: Session):
    # Setup Zone and Org
    zone_wkt = "POLYGON((77.5 12.9, 77.6 12.9, 77.6 13.0, 77.5 13.0, 77.5 12.9))"
    zone = Zone(name="Bangalore Center", boundary=zone_wkt)
    session.add(zone)
    session.commit()
    session.refresh(zone)

    org = Organization(name="BBMP West", zone_id=zone.id)
    session.add(org)

    category = Category(name="Pothole")
    session.add(category)

    citizen_email = "citizen@test.com"
    citizen = User(email=citizen_email, role="CITIZEN")
    session.add(citizen)
    session.commit()
    session.refresh(org)
    session.refresh(category)

    login_via_otp(client, session, citizen_email)

    # Report issue inside the zone
    # Bangalore coord: 12.97, 77.59 is inside our poly (77.5-77.6, 12.9-13.0)
    data = {
        "category_id": str(category.id),
        "lat": 12.97,
        "lng": 77.59,
        "address": "Test Address",
    }
    # Using multipart for photo
    import io

    dummy_photo = io.BytesIO(b"fake-photo-content")
    response = client.post(
        "/api/v1/issues/report",
        data=data,
        files={"photo": ("test.jpg", dummy_photo, "image/jpeg")},
    )

    assert response.status_code == 200
    issue_id = response.json()["issue_id"]

    # Verify auto-assignment to org
    issue = session.get(Issue, issue_id)
    assert issue.org_id == org.id
