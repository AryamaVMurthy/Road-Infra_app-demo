from uuid import UUID

from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str


class Login(BaseModel):
    email: EmailStr
    otp: str


class OTPRequest(BaseModel):
    email: EmailStr


class CurrentUserResponse(BaseModel):
    id: UUID
    email: EmailStr
    role: str
    full_name: str | None = None
