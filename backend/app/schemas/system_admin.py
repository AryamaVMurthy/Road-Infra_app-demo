from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel, Field


LngLat = Tuple[float, float]


class AuthorityCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=128)
    admin_email: str
    jurisdiction_points: List[LngLat]
    zone_name: Optional[str] = None


class AuthorityUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=128)
    jurisdiction_points: Optional[List[LngLat]] = None
    zone_name: Optional[str] = None


class AuthorityRead(BaseModel):
    org_id: UUID
    name: str
    zone_id: UUID
    zone_name: str
    admin_count: int
    worker_count: int
    jurisdiction_wkt: Optional[str] = None


class IssueTypeCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    default_priority: str = Field(default="P3", pattern="^P[1-4]$")
    expected_sla_days: int = Field(default=7, ge=1, le=365)


class IssueTypeUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    default_priority: Optional[str] = Field(default=None, pattern="^P[1-4]$")
    expected_sla_days: Optional[int] = Field(default=None, ge=1, le=365)
    is_active: Optional[bool] = None


class ManualIssueCreateRequest(BaseModel):
    category_id: UUID
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    address: Optional[str] = None
    priority: Optional[str] = Field(default=None, pattern="^P[1-4]$")
    org_id: Optional[UUID] = None


class ManualIssueCreateResponse(BaseModel):
    issue_id: UUID
    message: str
    created_at: datetime
