import pytest
from fastapi.testclient import TestClient
from app.models.domain import User, Otp
from sqlmodel import Session
from datetime import datetime, timedelta
from app.core.time import utc_now


def test_csrf_samesite_protection_simulation(client: TestClient, session: Session):
    email = "csrf_rigor@example.com"
    user = User(email=email, role="CITIZEN")
    session.add(user)
    otp = Otp(
        email=email, code="123456", expires_at=utc_now() + timedelta(minutes=5)
    )
    session.add(otp)
    session.commit()

    login_res = client.post(
        "/api/v1/auth/login", json={"email": email, "otp": "123456"}
    )
    assert login_res.status_code == 200
    assert "access_token" in client.cookies

    set_cookie = login_res.headers.get("set-cookie")
    assert "samesite=lax" in set_cookie.lower()
