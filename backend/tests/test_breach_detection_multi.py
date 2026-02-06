import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool
from app.services.auth_service import AuthService
from app.models.auth import RefreshToken
from app.models.domain import User
from fastapi import HTTPException

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
    User.__table__.create(engine)
    RefreshToken.__table__.create(engine)
    with Session(engine) as session:
        yield session


def test_multi_session_breach_revocation(session: Session):
    user = User(email="multi@example.com", role="CITIZEN")
    session.add(user)
    session.commit()

    # 1. Session 1 Login (Family A)
    token_A1_str, token_A1 = AuthService.create_refresh_token(session, user.id)
    # 2. Session 2 Login (Family B)
    token_B1_str, token_B1 = AuthService.create_refresh_token(session, user.id)

    assert token_A1.family_id != token_B1.family_id

    # 3. Session 1 Rotates (A1 -> A2)
    _, token_A2_str = AuthService.rotate_refresh_token(session, token_A1_str)

    # 4. Attacker tries to use A1 again (Breach!)
    with pytest.raises(HTTPException) as excinfo:
        AuthService.rotate_refresh_token(session, token_A1_str)

    assert excinfo.value.status_code == 401
    assert "Security breach detected" in excinfo.value.detail

    # 5. VERIFY: ALL tokens for user are now revoked, including Family B
    statement = select(RefreshToken).where(RefreshToken.user_id == user.id)
    all_tokens = session.exec(statement).all()

    for t in all_tokens:
        assert t.revoked_at is not None, f"Token {t.token_hash} should be revoked"
