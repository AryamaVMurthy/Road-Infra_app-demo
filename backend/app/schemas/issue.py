from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Any


class IssueRead(BaseModel):
    id: UUID
    category_id: Optional[UUID] = None
    category_name: Optional[str] = None
    worker_id: Optional[UUID] = None
    worker_name: Optional[str] = None
    status: str
    location_wkt: str
    lat: float
    lng: float
    address: Optional[str] = None
    reporter_id: UUID
    org_id: Optional[UUID] = None
    priority: Optional[str] = None
    report_count: int = 1
    created_at: datetime
    updated_at: datetime
    rejection_reason: Optional[str] = None
    eta_date: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class IssueReportResponse(BaseModel):
    message: str
    issue_id: UUID
    submission_id: UUID
    category_id: Optional[UUID] = None
    category_name: Optional[str] = None
    duplicate_merged: bool = False
    requires_admin_category_assignment: bool = False


class IssueReportRejectedResponse(BaseModel):
    message: str
    submission_id: UUID


class IssueCategoryAssignmentRequest(BaseModel):
    category_id: UUID
    reason: Optional[str] = None


class IntakeSpamOverrideRequest(BaseModel):
    reason: str


class IntakeArchiveRead(BaseModel):
    id: UUID
    reporter_id: UUID
    issue_id: Optional[UUID] = None
    status: str
    reason_code: Optional[str] = None
    selected_category_name_snapshot: Optional[str] = None
    model_id: Optional[str] = None
    model_quantization: Optional[str] = None
    prompt_version: Optional[str] = None
    file_path: str
    mime_type: str
    reporter_notes: Optional[str] = None
    address: Optional[str] = None
    lat: float
    lng: float
    raw_primary_result: Optional[dict[str, Any]] = None
    raw_evaluator_result: Optional[dict[str, Any]] = None
    latency_ms: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IntakeArchiveDetailRead(IntakeArchiveRead):
    image_url: Optional[str] = None
