import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlmodel import select
from datetime import datetime, timedelta
from app.main import app
from app.models.domain import User, Otp
from app.models.auth import RefreshToken
from app.services.auth_service import AuthService
from sqlmodel import Session


@pytest.mark.anyio
async def test_refresh_token_concurrency_protection(session: Session):
    email = "concurrent_rigor@example.com"
    user = User(email=email, role="CITIZEN")
    session.add(user)
    session.commit()
    session.refresh(user)
    user_id = user.id

    token_str, db_token = AuthService.create_refresh_token(session, user_id)
    session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        tasks = [
            ac.post("/api/v1/auth/refresh", cookies={"refresh_token": token_str}),
            ac.post("/api/v1/auth/refresh", cookies={"refresh_token": token_str}),
            ac.post("/api/v1/auth/refresh", cookies={"refresh_token": token_str}),
        ]

        responses = await asyncio.gather(*tasks)

    success_count = 0
    breach_count = 0

    for r in responses:
        if r.status_code == 200:
            success_count += 1
        else:
            print(f"Failed refresh: {r.status_code} {r.text}")
            if r.status_code == 401 and "Security breach detected" in r.text:
                breach_count += 1

    assert success_count >= 1
    assert success_count == 1
