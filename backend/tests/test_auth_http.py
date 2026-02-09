import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool
from datetime import datetime, timedelta
import hashlib
from unittest.mock import patch, AsyncMock

from app.main import app
from app.db.session import get_session
from app.models.domain import User, Otp
from app.models.auth import RefreshToken
from app.core.config import settings


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(
        engine, tables=[User.__table__, Otp.__table__, RefreshToken.__table__]
    )
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app, base_url="https://testserver") as client:
        yield client
    app.dependency_overrides.clear()


def test_otp_request_and_login_flow(client: TestClient, session: Session):
    email = "test@example.com"

    with patch(
        "app.services.email.EmailService.send_otp", new_callable=AsyncMock
    ) as mock_send:
        response = client.post("/api/v1/auth/otp-request", json={"email": email})
        assert response.status_code == 200

        statement = select(Otp).where(Otp.email == email)
        otp_record = session.exec(statement).first()
        assert otp_record is not None

        login_data = {"email": email, "otp": otp_record.code}
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200

        assert "access_token" in client.cookies

        response = client.get("/api/v1/auth/me")
        assert response.status_code == 200
        assert response.json()["email"] == email


def test_refresh_token_rotation_integration(client: TestClient, session: Session):
    email = "rotate@example.com"
    user = User(email=email, role="CITIZEN")
    session.add(user)
    otp = Otp(
        email=email, code="123456", expires_at=datetime.utcnow() + timedelta(minutes=5)
    )
    session.add(otp)
    session.commit()

    login_res = client.post(
        "/api/v1/auth/login", json={"email": email, "otp": "123456"}
    )
    assert login_res.status_code == 200
    rt_old = client.cookies.get("refresh_token")
    assert rt_old is not None

    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 200
    rt_new = client.cookies.get("refresh_token")
    assert rt_new != rt_old

    statement = select(RefreshToken).where(
        RefreshToken.token_lookup == hashlib.sha256(rt_old.encode()).hexdigest()
    )
    ref_token_db = session.exec(statement).first()
    assert ref_token_db is not None
    assert ref_token_db.revoked_at is not None


def test_logout_clears_cookies(client: TestClient, session: Session):
    email = "logout@example.com"
    user = User(email=email, role="CITIZEN")
    session.add(user)
    otp = Otp(
        email=email, code="111111", expires_at=datetime.utcnow() + timedelta(minutes=5)
    )
    session.add(otp)
    session.commit()

    client.post("/api/v1/auth/login", json={"email": email, "otp": "111111"})
    assert "access_token" in client.cookies
    refresh_token = client.cookies.get("refresh_token")
    assert refresh_token is not None

    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200

    at = client.cookies.get("access_token")
    assert at is None or at == ""

    db_row = session.exec(
        select(RefreshToken).where(
            RefreshToken.token_lookup
            == hashlib.sha256(refresh_token.encode()).hexdigest()
        )
    ).first()
    assert db_row is not None
    assert db_row.revoked_at is not None


def test_hsts_header_present(client: TestClient):
    response = client.get("/")
    assert "Strict-Transport-Security" in response.headers
    assert "max-age=31536000" in response.headers["Strict-Transport-Security"]
