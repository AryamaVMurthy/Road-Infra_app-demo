from fastapi import APIRouter, Depends, HTTPException, Request, Response
from app.core.config import settings
from app.schemas.auth import CurrentUserResponse, Login, OTPRequest
from app.schemas.common import ErrorResponse, MessageResponse
from app.models.domain import User, Otp, Invite
from sqlmodel import Session, select, desc
from app.db.session import get_session
from datetime import timedelta
from app.services.email import EmailService
from app.services.auth_service import AuthService
from app.api.deps import get_current_user

from app.core.security import check_otp_rate_limit
from app.core.time import utc_now

router = APIRouter()


@router.post(
    "/otp-request",
    response_model=MessageResponse,
    summary="Request a one-time password",
    description="Generate and send an OTP to the supplied email address for passwordless sign-in.",
    responses={429: {"model": ErrorResponse, "description": "OTP request rate limit exceeded"}},
)
async def request_otp(data: OTPRequest, session: Session = Depends(get_session)):
    check_otp_rate_limit(data.email)
    otp_code = EmailService.generate_otp()
    expires_at = utc_now() + timedelta(minutes=10)

    otp_entry = Otp(email=data.email, code=otp_code, expires_at=expires_at)
    session.add(otp_entry)
    session.commit()

    await EmailService.send_otp(data.email, otp_code)
    return {"message": "OTP sent to your email"}


@router.post(
    "/login",
    response_model=MessageResponse,
    summary="Complete OTP login",
    description="Validate the latest OTP for the email address, create the user if needed, and set access and refresh cookies.",
    responses={400: {"model": ErrorResponse, "description": "OTP is invalid or expired"}},
)
def login(response: Response, data: Login, session: Session = Depends(get_session)):
    latest_otp_statement = (
        select(Otp).where(Otp.email == data.email).order_by(desc(Otp.created_at))
    )
    otp_record = session.exec(latest_otp_statement).first()

    if (
        not otp_record
        or otp_record.code != data.otp
        or otp_record.expires_at < utc_now()
    ):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    # Enforce one-time usage and invalidate any previous OTPs for this email.
    otp_rows = session.exec(select(Otp).where(Otp.email == data.email)).all()
    for row in otp_rows:
        session.delete(row)

    statement = select(User).where(User.email == data.email)
    user = session.exec(statement).first()

    if not user:
        # Check for active invite
        invite_stmt = select(Invite).where(
            Invite.email == data.email,
            Invite.status == "INVITED",
            Invite.expires_at > utc_now(),
        )
        invite = session.exec(invite_stmt).first()

        if invite:
            user = User(email=data.email, role="WORKER", org_id=invite.org_id)
            invite.status = "ACCEPTED"
            session.add(invite)
        else:
            user = User(email=data.email, role="CITIZEN")

        session.add(user)

    user.last_login_at = utc_now()
    session.add(user)
    session.commit()
    session.refresh(user)

    access_token = AuthService.create_access_token(
        data={"sub": user.email, "role": user.role, "id": str(user.id)}
    )
    refresh_token_str, _ = AuthService.create_refresh_token(session, user.id)

    cookie_secure = not settings.DEV_MODE
    refresh_cookie_path = f"{settings.API_V1_STR}/auth"

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=cookie_secure,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token_str,
        httponly=True,
        secure=cookie_secure,
        samesite="lax",
        path=refresh_cookie_path,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    return {"message": "Login successful"}


@router.post(
    "/refresh",
    response_model=MessageResponse,
    summary="Refresh the authenticated session",
    description="Rotate the refresh token cookie and issue a new access token for the current browser session.",
    responses={401: {"model": ErrorResponse, "description": "Refresh token is missing or invalid"}},
)
def refresh_token(
    request: Request, response: Response, session: Session = Depends(get_session)
):
    old_refresh_token = request.cookies.get("refresh_token")
    if not old_refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    new_access, new_refresh = AuthService.rotate_refresh_token(
        session, old_refresh_token
    )
    cookie_secure = not settings.DEV_MODE
    refresh_cookie_path = f"{settings.API_V1_STR}/auth"

    response.set_cookie(
        key="access_token",
        value=new_access,
        httponly=True,
        secure=cookie_secure,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        secure=cookie_secure,
        samesite="lax",
        path=refresh_cookie_path,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    return {"message": "Token refreshed"}


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Log out the current session",
    description="Revoke the current refresh token if present and clear the authentication cookies from the response.",
)
def logout(
    response: Response, request: Request, session: Session = Depends(get_session)
):
    presented_refresh_token = request.cookies.get("refresh_token")
    if presented_refresh_token:
        AuthService.revoke_refresh_token(session, presented_refresh_token)

    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token", path=f"{settings.API_V1_STR}/auth")
    return {"message": "Logged out"}


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    summary="Get the current authenticated user",
    description="Return the authenticated user identity and role resolved from the access token cookie or bearer token.",
    responses={401: {"model": ErrorResponse, "description": "Authentication is required"}},
)
def read_users_me(current_user: User = Depends(get_current_user)):
    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        full_name=current_user.full_name,
    )
