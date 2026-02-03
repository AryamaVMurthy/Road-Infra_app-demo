import pytest
from app.models.domain import Category, User, Issue, Otp
from sqlmodel import Session, select
import io


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "Welcome to the Urban Infrastructure Issue Reporting API"
    }


def test_auth_flow(client, session):
    # Request OTP
    email = "test@example.com"
    response = client.post("/api/v1/auth/otp-request", json={"email": email})
    assert response.status_code == 200

    # Get OTP from DB
    otp_record = session.exec(select(Otp).where(Otp.email == email)).first()
    assert otp_record is not None
    otp_code = otp_record.code

    # Login
    response = client.post("/api/v1/auth/login", json={"email": email, "otp": otp_code})
    assert response.status_code == 200
    assert "access_token" in response.json()

    # Verify user created
    user = session.exec(select(User).where(User.email == "test@example.com")).first()
    assert user is not None
    assert user.role == "CITIZEN"


def test_report_issue_integration(client, session):
    # Setup: Category
    category = Category(name="Pothole", default_priority="P2")
    session.add(category)
    session.commit()
    session.refresh(category)

    # Setup: Reporter
    reporter = User(email="reporter@example.com", role="CITIZEN")
    session.add(reporter)
    session.commit()
    session.refresh(reporter)

    # Create a small valid JPEG in memory
    from PIL import Image

    img = Image.new("RGB", (100, 100), color="red")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="JPEG")
    file_content = img_byte_arr.getvalue()

    # Report
    response = client.post(
        "/api/v1/issues/report",
        data={
            "category_id": str(category.id),
            "lat": 17.4447,
            "lng": 78.3483,
            "reporter_email": "reporter@example.com",
            "address": "Banjara Hills",
        },
        files={"photo": ("test.jpg", file_content, "image/jpeg")},
    )

    assert response.status_code == 200
    assert "issue_id" in response.json()

    # Verify issue in DB
    from uuid import UUID as UUID_OBJ

    issue = session.get(Issue, UUID_OBJ(response.json()["issue_id"]))
    assert issue is not None
    assert issue.status == "REPORTED"
    assert issue.report_count == 1


def test_duplicate_report_integration(client, session):
    # Setup: Category and User
    category = Category(name="Pothole")
    session.add(category)
    user = User(email="user@example.com", role="CITIZEN")
    session.add(user)
    session.commit()

    # Valid image content
    from PIL import Image

    img = Image.new("RGB", (10, 10), color=(255, 0, 0))
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="JPEG")
    file_content = img_byte_arr.getvalue()

    # First report
    client.post(
        "/api/v1/issues/report",
        data={
            "category_id": str(category.id),
            "lat": 17.4447,
            "lng": 78.3483,
            "reporter_email": "user@example.com",
        },
        files={"photo": ("test1.jpg", file_content, "image/jpeg")},
    )

    # Second report at same location (within 5m)
    # 5m is roughly 0.000045 degrees
    response = client.post(
        "/api/v1/issues/report",
        data={
            "category_id": str(category.id),
            "lat": 17.444701,  # Extremely close
            "lng": 78.348301,
            "reporter_email": "user@example.com",
        },
        files={"photo": ("test2.jpg", file_content, "image/jpeg")},
    )

    assert response.status_code == 200

    # Verify report count incremented
    issues = session.exec(select(Issue)).all()
    assert len(issues) == 1
    assert issues[0].report_count == 2
