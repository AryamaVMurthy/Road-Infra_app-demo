from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from app.core.config import settings
from app.models.domain import User
from app.db.session import get_session
from sqlmodel import Session
from uuid import UUID

# Keep OAuth2PasswordBearer for Swagger UI support (it sends Authorization header)
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False
)


def get_current_user(
    request: Request,
    session: Session = Depends(get_session),
    token_auth: str | None = Depends(oauth2_scheme),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Priority: 1. Cookie, 2. Header (for Swagger UI / Dev tools)
    token = request.cookies.get("access_token")
    if not token:
        token = token_auth

    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str | None = payload.get("id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = session.get(User, UUID(user_id))
    if user is None:
        raise credentials_exception
    return user


VALID_ROLES = {"CITIZEN", "WORKER", "ADMIN", "SYSADMIN"}


def require_roles(*allowed_roles: str):
    allowed = {role.upper() for role in allowed_roles}
    invalid = allowed - VALID_ROLES
    if invalid:
        raise ValueError(f"Invalid role names: {sorted(invalid)}")

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user account",
            )
        user_role = (current_user.role or "").upper()
        if user_role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return dependency


require_admin_user = require_roles("ADMIN", "SYSADMIN")
require_worker_user = require_roles("WORKER")
require_citizen_user = require_roles("CITIZEN")
