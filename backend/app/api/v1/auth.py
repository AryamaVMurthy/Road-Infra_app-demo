from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.core.config import settings
from app.schemas.auth import Token, Login, OTPRequest
from app.models.domain import User, Otp
from sqlmodel import Session, select, desc
from app.db.session import get_session
from datetime import datetime, timedelta
from app.services.email import EmailService

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


from app.core.security import check_otp_rate_limit


@router.post("/otp-request")
async def request_otp(data: OTPRequest, session: Session = Depends(get_session)):
    check_otp_rate_limit(data.email)
    otp_code = EmailService.generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    otp_entry = Otp(email=data.email, code=otp_code, expires_at=expires_at)
    session.add(otp_entry)
    session.commit()

    await EmailService.send_otp(data.email, otp_code)
    return {"message": "OTP sent to your email"}


@router.post("/login", response_model=Token)
def login(data: Login, session: Session = Depends(get_session)):
    # Verify OTP
    statement = (
        select(Otp)
        .where(Otp.email == data.email, Otp.code == data.otp)
        .order_by(desc(Otp.created_at))
    )
    otp_record = session.exec(statement).first()

    if not otp_record or otp_record.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    # Check if user exists, if not create as CITIZEN
    statement = select(User).where(User.email == data.email)
    user = session.exec(statement).first()

    if not user:
        user = User(email=data.email, role="CITIZEN")
        session.add(user)

    user.last_login_at = datetime.utcnow()
    session.add(user)
    session.commit()
    session.refresh(user)

    access_token = create_access_token(
        data={"sub": user.email, "role": user.role, "id": str(user.id)}
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/google-mock", response_model=Token)
def google_mock_login(email: str, session: Session = Depends(get_session)):
    # Simulates a successful Google OAuth login
    statement = select(User).where(User.email == email)
    user = session.exec(statement).first()

    if not user:
        user = User(email=email, role="CITIZEN")
        session.add(user)
        session.commit()
        session.refresh(user)

    access_token = create_access_token(
        data={"sub": user.email, "role": user.role, "id": str(user.id)}
    )
    return {"access_token": access_token, "token_type": "bearer"}
