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
    token_auth: str = Depends(oauth2_scheme),
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
        user_id: str = payload.get("id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = session.get(User, UUID(user_id))
    if user is None:
        raise credentials_exception
    return user
