from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    detail: str


class RootResponse(BaseModel):
    message: str


class UserRead(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str] = None
    role: str
    org_id: Optional[UUID] = None
    status: str
    last_login_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
