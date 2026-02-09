import pytest
from datetime import datetime, timedelta
import hashlib
from uuid import uuid4
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool
from app.services.auth_service import AuthService
from app.models.auth import RefreshToken
from app.models.domain import User

# Mock Settings
from app.core import config

config.settings.SECRET_KEY = "test_secret"
config.settings.ACCESS_TOKEN_EXPIRE_MINUTES = 15
config.settings.REFRESH_TOKEN_EXPIRE_DAYS = 7


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    # Only create relevant tables to avoid GeoAlchemy/SQLite issues
    User.__table__.create(engine)
    RefreshToken.__table__.create(engine)

    with Session(engine) as session:
        yield session


def test_refresh_token_lifecycle(session: Session):
    # 1. Create User
    user = User(email="test@example.com", role="CITIZEN", full_name="Test User")
    session.add(user)
    session.commit()
    session.refresh(user)

    # 2. Create Refresh Token
    token_str, db_token = AuthService.create_refresh_token(session, user.id)
    assert db_token.token_hash != token_str
    assert db_token.token_lookup == hashlib.sha256(token_str.encode()).hexdigest()
    assert db_token.revoked_at is None
    assert db_token.user_id == user.id

    # 3. Rotate Token
    new_access, new_refresh_str = AuthService.rotate_refresh_token(session, token_str)

    # Verify Old Token Revoked
    session.refresh(db_token)
    assert db_token.revoked_at is not None
    assert db_token.replaced_by is not None
    assert db_token.replaced_by != new_refresh_str

    # Verify New Token
    statement = select(RefreshToken).where(
        RefreshToken.token_lookup == hashlib.sha256(new_refresh_str.encode()).hexdigest()
    )
    new_db_token = session.exec(statement).first()
    assert new_db_token is not None
    assert new_db_token.family_id == db_token.family_id
    assert new_db_token.revoked_at is None


def test_breach_detection(session: Session):
    user = User(email="victim@example.com", role="CITIZEN")
    session.add(user)
    session.commit()

    # 1. Honest User Login
    token_A_str, token_A = AuthService.create_refresh_token(session, user.id)

    # 2. Honest User Rotates (A -> B)
    _, token_B_str = AuthService.rotate_refresh_token(session, token_A_str)

    # 3. Attacker tries to use A again
    # Should trigger revocation of family
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as excinfo:
        AuthService.rotate_refresh_token(session, token_A_str)

    assert excinfo.value.status_code == 401
    assert "Security breach detected" in excinfo.value.detail

    # 4. Verify B is now revoked (Victim locked out)
    statement = select(RefreshToken).where(
        RefreshToken.token_lookup == hashlib.sha256(token_B_str.encode()).hexdigest()
    )
    token_B = session.exec(statement).first()
    assert token_B.revoked_at is not None
