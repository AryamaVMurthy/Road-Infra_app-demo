from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Any


class IssueRead(BaseModel):
    id: UUID
    category_id: UUID
    category_name: Optional[str] = None
    worker_id: Optional[UUID] = None
    worker_name: Optional[str] = None
    status: str
    location_wkt: str
    lat: float
    lng: float
    address: Optional[str] = None
    reporter_id: UUID
    worker_id: Optional[UUID] = None
    org_id: Optional[UUID] = None
    priority: Optional[str] = "P3"
    report_count: int = 1
    created_at: datetime
    updated_at: datetime
    rejection_reason: Optional[str] = None
    eta_duration: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
