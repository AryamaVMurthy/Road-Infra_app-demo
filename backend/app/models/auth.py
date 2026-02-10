from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship
from app.models.domain import User
from app.core.time import utc_now


class RefreshToken(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    # Slow hash (bcrypt) used for secure token verification.
    token_hash: str = Field(index=True)
    # Deterministic lookup hash (sha256) to avoid querying by raw token value.
    token_lookup: Optional[str] = Field(default=None, index=True)
    expires_at: datetime
    created_at: datetime = Field(default_factory=utc_now)
    revoked_at: Optional[datetime] = None
    replaced_by: Optional[str] = None
    family_id: UUID = Field(default_factory=uuid4, index=True)

    user: User = Relationship(back_populates="refresh_tokens")
